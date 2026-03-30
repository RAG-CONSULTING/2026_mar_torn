"""Training module - gym strategy and stat optimization."""

from __future__ import annotations

import structlog

logger = structlog.get_logger()

# Battle stat names
STATS = ["strength", "defense", "speed", "dexterity"]

# Common gym training strategies
STRATEGIES = {
    "balanced": {"strength": 0.25, "defense": 0.25, "speed": 0.25, "dexterity": 0.25},
    "str_def_focus": {"strength": 0.35, "defense": 0.35, "speed": 0.15, "dexterity": 0.15},
    "speed_dex_focus": {"strength": 0.15, "defense": 0.15, "speed": 0.35, "dexterity": 0.35},
    "strength_main": {"strength": 0.50, "defense": 0.25, "speed": 0.15, "dexterity": 0.10},
}


class TrainingModule:
    """Decides which stat to train and when."""

    def __init__(
        self,
        strategy: str = "balanced",
        current_stats: dict[str, float] | None = None,
    ):
        self.strategy = strategy
        self.target_ratios = STRATEGIES.get(strategy, STRATEGIES["balanced"])
        self.current_stats = current_stats or {s: 0 for s in STATS}

    def recommend_stat(self) -> str:
        """Pick the stat that is most behind its target ratio."""
        total = sum(self.current_stats.values())
        if total == 0:
            return "strength"  # default starting stat

        current_ratios = {s: v / total for s, v in self.current_stats.items()}
        deficits = {
            s: self.target_ratios[s] - current_ratios.get(s, 0) for s in STATS
        }
        return max(deficits, key=deficits.get)  # type: ignore[arg-type]

    def should_train(self, energy: int, energy_max: int, happy: int) -> dict:
        """Decide whether to train now or wait for better conditions."""
        happy_bonus = happy >= 99999
        energy_pct = energy / energy_max if energy_max > 0 else 0

        recommendation = {
            "should_train": False,
            "stat": self.recommend_stat(),
            "happy_bonus_active": happy_bonus,
            "reasoning": "",
        }

        if energy == 0:
            recommendation["reasoning"] = "No energy available"
            return recommendation

        # Always train if energy is full (don't waste regen)
        if energy >= energy_max:
            recommendation["should_train"] = True
            recommendation["reasoning"] = "Energy is full - train to avoid waste"
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

    def update_stats(self, stats: dict[str, float]) -> None:
        """Update current stat values from API data."""
        for s in STATS:
            if s in stats:
                self.current_stats[s] = stats[s]
