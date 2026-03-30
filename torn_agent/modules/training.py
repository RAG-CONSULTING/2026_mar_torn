"""Training module - gym strategy and stat optimization.

Based on real TORN mechanics:
- Specialist gyms give ~4x gains but require stat ratios
- Hank's Ratio: 1.25 : 1 : 1 : 0 (primary 25% above, one forgotten)
- Happy multiplies gains exponentially
- Happy jumping is optimal until ~700-800k total stats (with Adult Novelties)
"""

from __future__ import annotations

import structlog

from torn_agent.modules.knowledge import (
    DAILY_ENERGY_TARGET,
    GAIN_MODIFIERS,
    HAPPY_JUMP_STOP_THRESHOLD_WITH_AN,
    HAPPY_JUMP_STOP_THRESHOLD_WITHOUT,
    SPECIALIST_GYMS,
    TRAINING_STRATEGIES,
)

logger = structlog.get_logger()

STATS = ["strength", "defense", "speed", "dexterity"]


class TrainingModule:
    """Decides which stat to train and when, using real TORN gym mechanics."""

    def __init__(
        self,
        strategy: str = "balanced",
        current_stats: dict[str, float] | None = None,
    ):
        self.strategy = strategy
        strat = TRAINING_STRATEGIES.get(strategy, TRAINING_STRATEGIES["balanced"])
        self.target_ratios = strat["ratios"]
        self.current_stats = current_stats or {s: 0 for s in STATS}

    def recommend_stat(self) -> str:
        """Pick the stat that is most behind its target ratio."""
        total = sum(self.current_stats.values())
        if total == 0:
            return "strength"

        current_ratios = {s: v / total for s, v in self.current_stats.items()}
        deficits = {
            s: self.target_ratios[s] - current_ratios.get(s, 0) for s in STATS
        }
        return max(deficits, key=deficits.get)  # type: ignore[arg-type]

    def should_train(self, energy: int, energy_max: int, happy: int) -> dict:
        """Decide whether to train now or wait for better conditions."""
        happy_bonus = happy >= 99999
        total_stats = sum(self.current_stats.values())

        recommendation = {
            "should_train": False,
            "stat": self.recommend_stat(),
            "happy_bonus_active": happy_bonus,
            "reasoning": "",
            "happy_jump_recommended": False,
        }

        if energy == 0:
            recommendation["reasoning"] = "No energy available"
            return recommendation

        # Always train if energy is full (don't waste regen)
        if energy >= energy_max:
            recommendation["should_train"] = True
            recommendation["reasoning"] = "Energy is full - train to avoid waste"
            return recommendation

        # Check if happy jumping would be beneficial
        if self._should_happy_jump(energy, happy, total_stats):
            recommendation["should_train"] = False
            recommendation["happy_jump_recommended"] = True
            recommendation["reasoning"] = (
                f"HAPPY JUMP: Stack energy to 1000, eat 49 Big Chocolates, "
                f"pop Ecstasy to double Happy, then train all 1000E. "
                f"Current total stats: {total_stats:,.0f}"
            )
            return recommendation

        # Train if energy is above threshold
        if energy >= 25:
            recommendation["should_train"] = True
            if happy_bonus:
                recommendation["reasoning"] = (
                    f"Training {recommendation['stat']} with happy bonus active (2x gains)"
                )
            else:
                recommendation["reasoning"] = (
                    f"Training {recommendation['stat']} with {energy}E available"
                )
            return recommendation

        recommendation["reasoning"] = f"Only {energy}E available - waiting for more"
        return recommendation

    def check_specialist_gym_eligibility(self) -> list[dict]:
        """Check which specialist gyms the player qualifies for."""
        eligible = []
        total = sum(self.current_stats.values())
        if total == 0:
            return eligible

        str_val = self.current_stats.get("strength", 0)
        def_val = self.current_stats.get("defense", 0)
        spd_val = self.current_stats.get("speed", 0)
        dex_val = self.current_stats.get("dexterity", 0)

        checks = {
            "Balboa's Gym": (def_val + dex_val) >= 1.25 * (spd_val + str_val),
            "Frontline Fitness": (spd_val + str_val) >= 1.25 * (def_val + dex_val),
            "Gym 3000": str_val >= 1.25 * sorted([def_val, spd_val, dex_val])[-1],
            "Mr. Isoyama's": def_val >= 1.25 * sorted([str_val, spd_val, dex_val])[-1],
            "Total Rebound": spd_val >= 1.25 * sorted([str_val, def_val, dex_val])[-1],
            "Elites": dex_val >= 1.25 * sorted([str_val, def_val, spd_val])[-1],
        }

        for gym_name, qualifies in checks.items():
            info = SPECIALIST_GYMS[gym_name]
            eligible.append({
                "gym": gym_name,
                "qualifies": qualifies,
                "focus": info["focus"],
                "condition": info["condition"],
            })

        return eligible

    def estimate_daily_gains(self, happy: int, energy_per_day: int = DAILY_ENERGY_TARGET) -> dict:
        """Estimate stat gains per day given current happy and energy budget."""
        # Simplified gain formula: gains scale with happy
        # Real formula: ((Gym_Dots * 4) * ((0.00019106 * Stat) + (0.00226263 * Happy) + 0.55))
        #               * (1 + bonuses) / 150 * Energy_Used
        happy_factor = 0.00226263 * happy + 0.55
        stat = sum(self.current_stats.values()) / 4  # average stat
        stat_factor = 0.00019106 * stat
        base_per_energy = (stat_factor + happy_factor) * 4 / 150  # assuming ~2.0 gym dots

        return {
            "estimated_gains_per_day": round(base_per_energy * energy_per_day, 0),
            "happy_factor": round(happy_factor, 4),
            "energy_per_day": energy_per_day,
            "note": "Rough estimate. Actual gains depend on gym dots and modifiers.",
        }

    def _should_happy_jump(self, energy: int, happy: int, total_stats: float) -> bool:
        """Check if happy jumping is recommended right now."""
        # Only worth it below the threshold
        if total_stats > HAPPY_JUMP_STOP_THRESHOLD_WITH_AN:
            return False
        # Need enough energy stacked (at least 500+)
        if energy < 500:
            return False
        # Happy should be relatively low (jump is about maximizing happy first)
        if happy > 5000:
            return False
        return True

    def update_stats(self, stats: dict[str, float]) -> None:
        """Update current stat values from API data."""
        for s in STATS:
            if s in stats:
                self.current_stats[s] = stats[s]
