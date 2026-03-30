"""Combat module - handles attack target selection and chain management."""

from __future__ import annotations

import structlog

from torn_agent.api.client import TornAPI
from torn_agent.api.models import AttackTarget

logger = structlog.get_logger()

# Players who are idle for >5 minutes are generally safer targets
IDLE_THRESHOLD_MINUTES = 5

# Don't attack players in these states
UNSAFE_STATES = {"Hospital", "Jail", "Traveling", "Abroad", "Federal"}


class CombatModule:
    """Evaluates potential attack targets and manages chain logic."""

    def __init__(self, api: TornAPI, my_level: int = 0, my_battle_stats: float = 0):
        self.api = api
        self.my_level = my_level
        self.my_battle_stats = my_battle_stats

    async def evaluate_target(self, target_id: int) -> dict:
        """Scout and evaluate a target, returning a risk assessment."""
        target = await self.api.get_target_profile(target_id)
        score = self._score_target(target)
        return {
            "target": target.model_dump(),
            "attack_score": score,
            "recommendation": "attack" if score >= 70 else "skip" if score >= 40 else "avoid",
            "reasons": self._explain_score(target, score),
        }

    def _score_target(self, target: AttackTarget) -> int:
        """Score a target from 0-100 on attackability."""
        score = 50  # baseline

        # Status check - must be "Okay" to attack
        if target.status in UNSAFE_STATES:
            return 0

        # Level difference (prefer targets at or below our level)
        level_diff = target.level - self.my_level
        if level_diff > 10:
            score -= 30
        elif level_diff > 5:
            score -= 15
        elif level_diff < -5:
            score += 10

        # Life percentage - low life is easier
        if target.life_maximum > 0:
            life_pct = target.life_current / target.life_maximum
            if life_pct < 0.5:
                score += 15
            elif life_pct < 0.8:
                score += 5

        # Faction check - avoid targets in large factions (retaliation risk)
        if target.faction_id > 0:
            score -= 5  # slight penalty for being in a faction

        return max(0, min(100, score))

    def _explain_score(self, target: AttackTarget, score: int) -> list[str]:
        reasons = []
        if target.status in UNSAFE_STATES:
            reasons.append(f"Target is {target.status} - cannot attack")
        if target.level > self.my_level + 10:
            reasons.append(f"Target level {target.level} is much higher than ours")
        if target.life_maximum > 0 and target.life_current / target.life_maximum < 0.5:
            reasons.append("Target has low life - easier to finish")
        if score >= 70:
            reasons.append("Good target - within attack range")
        return reasons

    async def check_chain_status(self) -> dict:
        """Check if faction is currently chaining."""
        chain_data = await self.api.get_faction_chain()
        chain = chain_data.get("chain", {})
        return {
            "current": chain.get("current", 0),
            "max": chain.get("max", 0),
            "timeout": chain.get("timeout", 0),
            "is_active": chain.get("current", 0) > 0,
            "needs_hit": chain.get("timeout", 0) < 60 and chain.get("current", 0) > 0,
        }
