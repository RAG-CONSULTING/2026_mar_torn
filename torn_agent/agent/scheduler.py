"""Scheduler - runs the agent loop on a configurable interval."""

from __future__ import annotations

import asyncio
import signal
from datetime import datetime, timezone

import structlog

from torn_agent.agent.brain import TornAgentBrain
from torn_agent.agent.executor import ActionExecutor
from torn_agent.api.client import TornAPI
from torn_agent.config.settings import Settings

logger = structlog.get_logger()


class AgentScheduler:
    """Runs the AI agent on a recurring loop.

    Each cycle:
    1. Agent observes game state via TORN API
    2. Claude analyzes and recommends actions
    3. Executor processes recommendations
    4. Sleep until next cycle
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self._running = False
        self._cycle_count = 0

    async def run(self) -> None:
        """Start the agent loop. Runs until interrupted."""
        self._running = True
        loop = asyncio.get_event_loop()
        loop.add_signal_handler(signal.SIGINT, self._stop)
        loop.add_signal_handler(signal.SIGTERM, self._stop)

        logger.info(
            "agent_starting",
            player_id=self.settings.torn_player_id,
            dry_run=self.settings.dry_run,
            interval=self.settings.agent_loop_interval_seconds,
        )

        async with TornAPI(
            api_key=self.settings.torn_api_key,
            base_url=self.settings.torn_api_base_url,
        ) as api:
            brain = TornAgentBrain(settings=self.settings, torn_api=api)
            executor = ActionExecutor(settings=self.settings)

            while self._running:
                await self._run_cycle(brain, executor)
                if self._running:
                    wait = self._determine_wait(executor)
                    logger.info("cycle_sleeping", seconds=wait)
                    await asyncio.sleep(wait)

        logger.info("agent_stopped", cycles_completed=self._cycle_count)

    async def run_once(self) -> list[dict]:
        """Run a single agent cycle and return action log. Useful for testing."""
        async with TornAPI(
            api_key=self.settings.torn_api_key,
            base_url=self.settings.torn_api_base_url,
        ) as api:
            brain = TornAgentBrain(settings=self.settings, torn_api=api)
            executor = ActionExecutor(settings=self.settings)
            await self._run_cycle(brain, executor)
            return executor.get_recent_log()

    async def _run_cycle(
        self, brain: TornAgentBrain, executor: ActionExecutor
    ) -> None:
        """Execute one think-act cycle."""
        self._cycle_count += 1
        cycle_start = datetime.now(timezone.utc)

        logger.info("cycle_start", cycle=self._cycle_count, time=cycle_start.isoformat())

        try:
            recommendations = await brain.think()
            logger.info(
                "cycle_recommendations",
                count=len(recommendations),
                actions=[r.action for r in recommendations],
            )

            results = executor.execute(recommendations)
            for result in results:
                logger.info(
                    "cycle_result",
                    action=result.recommendation.action,
                    executed=result.executed,
                    result=result.result,
                )

        except Exception as e:
            logger.error("cycle_error", cycle=self._cycle_count, error=str(e), exc_info=True)

        elapsed = (datetime.now(timezone.utc) - cycle_start).total_seconds()
        logger.info("cycle_complete", cycle=self._cycle_count, elapsed_seconds=round(elapsed, 1))

    def _determine_wait(self, executor: ActionExecutor) -> int:
        """Determine how long to wait before next cycle.

        If the agent recommended a specific wait time, use that.
        Otherwise use the configured interval.
        """
        recent = executor.get_recent_log(5)
        for entry in recent:
            if entry["action"] == "wait" and entry.get("parameters", {}).get("wait_seconds"):
                return entry["parameters"]["wait_seconds"]

        return self.settings.agent_loop_interval_seconds

    def _stop(self) -> None:
        logger.info("shutdown_requested")
        self._running = False
