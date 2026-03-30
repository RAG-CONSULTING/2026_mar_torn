"""Scheduler - runs the agent loop with human-like timing."""

from __future__ import annotations

import asyncio
import signal
from datetime import datetime, timezone

import structlog

from torn_agent.agent.brain import TornAgentBrain
from torn_agent.agent.executor import ActionExecutor
from torn_agent.agent.stealth import HumanBehaviorSimulator, StealthProfile
from torn_agent.api.client import TornAPI
from torn_agent.config.settings import Settings

logger = structlog.get_logger()


class AgentScheduler:
    """Runs the AI agent on a recurring loop with anti-detection timing.

    Each cycle:
    1. Check if we should be active (circadian rhythm)
    2. Agent observes game state via TORN API
    3. Claude analyzes and recommends actions
    4. Executor processes recommendations with human-like delays
    5. Sleep with randomized jitter until next cycle
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self._running = False
        self._cycle_count = 0
        self._stealth = HumanBehaviorSimulator(
            StealthProfile(
                timezone_offset_hours=settings.timezone_offset_hours,
            )
        )

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
            stealth="enabled",
        )

        self._stealth.start_session()

        async with TornAPI(
            api_key=self.settings.torn_api_key,
            base_url=self.settings.torn_api_base_url,
        ) as api:
            brain = TornAgentBrain(settings=self.settings, torn_api=api)
            executor = ActionExecutor(settings=self.settings)

            while self._running:
                # Session break check
                if self._stealth.should_take_break():
                    break_duration = self._stealth.get_break_duration()
                    logger.info(
                        "session_break",
                        duration_minutes=round(break_duration / 60, 1),
                    )
                    await asyncio.sleep(break_duration)
                    self._stealth.start_session()
                    continue

                # Circadian activity check
                if not self._stealth.should_be_active():
                    sleep_time = self._stealth.get_break_duration()
                    logger.info(
                        "inactive_period",
                        sleep_minutes=round(sleep_time / 60, 1),
                        reason="circadian_rhythm",
                    )
                    await asyncio.sleep(sleep_time)
                    continue

                # Pre-action delay (human doesn't act instantly)
                pre_delay = self._stealth.get_action_delay()
                logger.debug("pre_action_delay", seconds=round(pre_delay, 1))
                await asyncio.sleep(pre_delay)

                await self._run_cycle(brain, executor)

                if self._running:
                    wait = self._determine_wait(executor)
                    # Apply stealth jitter to wait time
                    wait = self._stealth.get_poll_interval(wait)
                    logger.info("cycle_sleeping", seconds=round(wait, 1))
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

            # Shuffle action order slightly for unpredictability
            recommendations = self._stealth.shuffle_actions(recommendations)

            logger.info(
                "cycle_recommendations",
                count=len(recommendations),
                actions=[r.action for r in recommendations],
            )

            # Execute with human-like delays between actions
            results = []
            for rec in recommendations:
                # Skip occasionally (human imperfection)
                if rec.priority < 8 and self._stealth.should_skip_action():
                    logger.info("action_skipped_stealth", action=rec.action)
                    continue

                result = executor.execute([rec])
                results.extend(result)

                # Delay between actions (humans don't chain instantly)
                if len(recommendations) > 1:
                    gap = self._stealth.get_action_delay()
                    await asyncio.sleep(gap)

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
