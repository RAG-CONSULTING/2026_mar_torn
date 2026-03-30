"""Action executor - translates AI recommendations into game actions.

The TORN API is read-only, so actual gameplay actions are logged as
instructions for the player or dispatched via browser automation
(if configured).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog

from torn_agent.agent.brain import ActionRecommendation
from torn_agent.config.settings import Settings

logger = structlog.get_logger()


class ActionLog:
    """Record of an executed or skipped action."""

    def __init__(
        self,
        recommendation: ActionRecommendation,
        executed: bool,
        result: str,
    ):
        self.recommendation = recommendation
        self.executed = executed
        self.result = result
        self.timestamp = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.recommendation.action,
            "priority": self.recommendation.priority,
            "reasoning": self.recommendation.reasoning,
            "parameters": self.recommendation.parameters,
            "executed": self.executed,
            "result": self.result,
            "timestamp": self.timestamp.isoformat(),
        }


class ActionExecutor:
    """Executes or logs recommended actions.

    In dry-run mode: logs what *would* happen.
    In live mode: outputs instructions or triggers browser automation.

    NOTE: The TORN API is read-only. Actual gameplay actions (attacking,
    training, using items) require browser interaction. This executor
    serves as the bridge between AI decisions and action dispatch.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.action_log: list[ActionLog] = []

    def execute(self, recommendations: list[ActionRecommendation]) -> list[ActionLog]:
        """Process a batch of recommendations."""
        results = []
        actions_taken = 0

        for rec in recommendations:
            if actions_taken >= self.settings.max_actions_per_loop:
                log = ActionLog(rec, False, "Skipped - max actions per loop reached")
                self.action_log.append(log)
                results.append(log)
                continue

            log = self._process_action(rec)
            self.action_log.append(log)
            results.append(log)
            if log.executed:
                actions_taken += 1

        return results

    def _process_action(self, rec: ActionRecommendation) -> ActionLog:
        """Process a single action recommendation."""
        # Safety checks
        if not self._safety_check(rec):
            return ActionLog(rec, False, "Blocked by safety check")

        if self.settings.dry_run:
            logger.info(
                "dry_run_action",
                action=rec.action,
                priority=rec.priority,
                reasoning=rec.reasoning,
                parameters=rec.parameters,
            )
            return ActionLog(
                rec,
                False,
                f"[DRY RUN] Would execute: {rec.action} - {rec.reasoning}",
            )

        # Live mode - dispatch action
        return self._dispatch(rec)

    def _safety_check(self, rec: ActionRecommendation) -> bool:
        """Validate an action against safety constraints."""
        if rec.action == "attack_target" and not self.settings.enable_attacks:
            logger.warning("attack_blocked", reasoning="Attacks disabled in settings")
            return False

        if rec.action == "travel" and not self.settings.enable_travel:
            logger.warning("travel_blocked", reasoning="Travel disabled in settings")
            return False

        if rec.action in ("buy_market", "sell_market") and not self.settings.enable_market:
            logger.warning("market_blocked", reasoning="Market trading disabled in settings")
            return False

        # Spending limit check
        if rec.parameters and rec.parameters.get("cost", 0) > self.settings.max_spend_per_action:
            logger.warning(
                "spend_limit_exceeded",
                cost=rec.parameters["cost"],
                limit=self.settings.max_spend_per_action,
            )
            return False

        return True

    def _dispatch(self, rec: ActionRecommendation) -> ActionLog:
        """Dispatch an action for execution.

        Currently outputs structured instructions. Can be extended to
        trigger browser automation (Playwright/Selenium) for actual
        gameplay execution.
        """
        instruction = self._build_instruction(rec)
        logger.info("action_dispatched", action=rec.action, instruction=instruction)
        return ActionLog(rec, True, instruction)

    def _build_instruction(self, rec: ActionRecommendation) -> str:
        """Build a human-readable or machine-parseable instruction."""
        params = rec.parameters or {}

        match rec.action:
            case "train_gym":
                stat = params.get("stat", "strength")
                return f"TRAIN: Go to gym and train {stat}"
            case "commit_crime":
                crime = params.get("crime_type", "auto")
                return f"CRIME: Commit crime - {crime}"
            case "use_item":
                item = params.get("item_name", params.get("item_id", "unknown"))
                return f"USE ITEM: Use {item}"
            case "attack_target":
                target = params.get("target_id", "unknown")
                return f"ATTACK: Attack player #{target}"
            case "travel":
                dest = params.get("destination", "unknown")
                return f"TRAVEL: Fly to {dest}"
            case "buy_market":
                item = params.get("item_name", params.get("item_id", "unknown"))
                qty = params.get("quantity", 1)
                return f"BUY: Purchase {qty}x {item} from market"
            case "sell_market":
                item = params.get("item_name", params.get("item_id", "unknown"))
                return f"SELL: List {item} on market"
            case "refill_energy":
                return "REFILL: Use energy refill (Xanax/energy drink)"
            case "chain_attack":
                target = params.get("target_id", "unknown")
                return f"CHAIN: Attack player #{target} to maintain chain"
            case "wait":
                secs = rec.wait_seconds or 60
                return f"WAIT: Sleep for {secs}s before next check"
            case _:
                return f"UNKNOWN ACTION: {rec.action} with params {params}"

    def get_recent_log(self, count: int = 20) -> list[dict]:
        """Get recent action log entries."""
        return [log.to_dict() for log in self.action_log[-count:]]
