"""Combat module - attack target selection and chain management.

Based on real TORN attack mechanics:
- Attack costs 25E (15E Valentine's). Leave = 100% XP, Mug = 55-60%, Hosp = 40%.
- Critical hits: 12% base + edu/merits. Head/throat/heart = 3.5x damage.
- Mugging: steal 5-10% wallet. Masterful Looting merits boost to 7.5-15%.
- 7-star Clothing Store employees get 75% mugging reduction.
"""

from __future__ import annotations

import structlog

from torn_agent.api.client import TornAPI
from torn_agent.api.models import AttackTarget
from torn_agent.modules.knowledge import (
    ATTACK_COST_ENERGY,
    ATTACK_XP_MULTIPLIERS,
    CRITICAL_HIT,
    MUGGING,
)

logger = structlog.get_logger()

# Players in these states cannot be attacked
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
        outcome = self._recommend_outcome(target)
        return {
            "target": target.model_dump(),
            "attack_score": score,
            "recommendation": "attack" if score >= 70 else "skip" if score >= 40 else "avoid",
            "suggested_outcome": outcome,
            "energy_cost": ATTACK_COST_ENERGY,
            "reasons": self._explain_score(target, score),
        }

    def _score_target(self, target: AttackTarget) -> int:
        """Score a target from 0-100 on attackability."""
        score = 50

        if target.status in UNSAFE_STATES:
            return 0

        # Level difference
        level_diff = target.level - self.my_level
        if level_diff > 10:
            score -= 30
        elif level_diff > 5:
            score -= 15
        elif level_diff < -5:
            score += 10

        # Life percentage - low life is easier to finish
        if target.life_maximum > 0:
            life_pct = target.life_current / target.life_maximum
            if life_pct < 0.5:
                score += 15
            elif life_pct < 0.8:
                score += 5

        # Faction check - targets in factions risk retaliation
        if target.faction_id > 0:
            score -= 5

        return max(0, min(100, score))

    def _recommend_outcome(self, target: AttackTarget) -> str:
        """Recommend attack outcome based on target and our goals."""
        # For leveling: always leave (100% XP)
        # For money: mug (55-60% XP but steal cash)
        # For faction wars/chain: hospitalize (40% XP but removes them)

        # Default to leave for maximum XP
        return "leave"

    def _explain_score(self, target: AttackTarget, score: int) -> list[str]:
        reasons = []
        if target.status in UNSAFE_STATES:
            reasons.append(f"Target is {target.status} - cannot attack")
        if target.level > self.my_level + 10:
            reasons.append(f"Target level {target.level} is much higher than ours ({self.my_level})")
        if target.life_maximum > 0 and target.life_current / target.life_maximum < 0.5:
            reasons.append("Target has low life - easier to finish")
        if target.faction_id > 0:
            reasons.append(f"Target in faction {target.faction_id} - retaliation risk")
        if score >= 70:
            reasons.append("Good target - within attack range")
        reasons.append(
            f"XP by outcome: Leave={ATTACK_XP_MULTIPLIERS['leave']*100:.0f}%, "
            f"Mug={ATTACK_XP_MULTIPLIERS['mug']*100:.0f}%, "
            f"Hosp={ATTACK_XP_MULTIPLIERS['hospitalize']*100:.0f}%"
        )
        return reasons

    async def check_chain_status(self) -> dict:
        """Check if faction is currently chaining."""
        chain_data = await self.api.get_faction_chain()
        chain = chain_data.get("chain", {})
        current = chain.get("current", 0)
        timeout = chain.get("timeout", 0)

        urgency = "none"
        if current > 0:
            if timeout < 60:
                urgency = "critical"  # chain about to break
            elif timeout < 120:
                urgency = "high"
            elif timeout < 300:
                urgency = "medium"
            else:
                urgency = "low"

        return {
            "current": current,
            "max": chain.get("max", 0),
            "timeout": timeout,
            "is_active": current > 0,
            "urgency": urgency,
            "needs_hit": timeout < 120 and current > 0,
        }
