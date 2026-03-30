"""Travel module - foreign stock trading and travel planning.

Based on real TORN travel mechanics (post-Aug 2024 meta):
- Buy plushies/flowers abroad → trade at Museum for Points → sell Points
- Best destinations: Argentina (overall), South Africa (profit/hold), Mexico (speed)
- Avoid Switzerland (saturated, <50% $/hr)
- Capacity: 5 base + 10 airstrip + 10 faction + 4 suitcase = 29 max
"""

from __future__ import annotations

import structlog

from torn_agent.modules.knowledge import TRAVEL_DESTINATIONS, TRAVEL_CAPACITY

logger = structlog.get_logger()


class TravelModule:
    """Plans travel for foreign stock purchases and item arbitrage."""

    def __init__(self, cash_available: int = 0, capacity: int = 5):
        self.cash_available = cash_available
        self.capacity = capacity

    def recommend_destination(
        self,
        current_status: str,
        available_time_minutes: int = 300,
        prefer_overnight: bool = False,
    ) -> dict:
        """Recommend a travel destination based on time, profit, and playstyle."""
        if current_status in ("Traveling", "Abroad"):
            return {
                "recommendation": "wait",
                "reasoning": f"Currently {current_status} - wait for arrival/return",
            }

        if current_status != "Okay":
            return {
                "recommendation": "skip",
                "reasoning": f"Cannot travel while {current_status}",
            }

        # Filter by round-trip time
        viable = {}
        for name, info in TRAVEL_DESTINATIONS.items():
            round_trip = info["flight_minutes"] * 2
            if round_trip <= available_time_minutes:
                viable[name] = info

        if not viable:
            return {
                "recommendation": "skip",
                "reasoning": "Not enough time for any round trip",
            }

        # Exclude Switzerland (bad $/hr)
        viable.pop("Switzerland", None)

        if prefer_overnight:
            # For overnight: prefer long-haul high-profit destinations
            long_haul = {
                k: v for k, v in viable.items()
                if v["tier"] == "long"
            }
            if long_haul:
                # South Africa is highest profit per hold
                if "South Africa" in long_haul:
                    dest = "South Africa"
                else:
                    dest = next(iter(long_haul))
                info = long_haul[dest]
                return {
                    "recommendation": "travel",
                    "destination": dest,
                    "flight_time_minutes": info["flight_minutes"],
                    "items": info["items"],
                    "tier": info["tier"],
                    "reasoning": f"Overnight trip to {dest} ({info['flight_minutes']}min) - {info['note']}",
                }

        # For active play: prefer Argentina (best overall) or short flights
        priority_order = [
            "Argentina",      # Best overall
            "South Africa",   # Highest profit per hold
            "Mexico",         # Short flight
            "Canada",         # Short flight + Xanax
            "Cayman Islands", # Short flight
        ]

        for dest in priority_order:
            if dest in viable:
                info = viable[dest]
                return {
                    "recommendation": "travel",
                    "destination": dest,
                    "flight_time_minutes": info["flight_minutes"],
                    "items": info["items"],
                    "tier": info["tier"],
                    "capacity": self.capacity,
                    "reasoning": f"Travel to {dest} ({info['flight_minutes']}min) - {info['note']}",
                }

        # Fallback: shortest viable
        best = min(viable.items(), key=lambda x: x[1]["flight_minutes"])
        return {
            "recommendation": "travel",
            "destination": best[0],
            "flight_time_minutes": best[1]["flight_minutes"],
            "items": best[1]["items"],
            "reasoning": f"Quick trip to {best[0]} ({best[1]['flight_minutes']}min)",
        }

    def estimate_profit(self, destination: str, point_price: int = 45_000) -> dict:
        """Estimate travel profit based on destination and current point prices."""
        info = TRAVEL_DESTINATIONS.get(destination)
        if not info:
            return {"error": f"Unknown destination: {destination}"}

        # Each plushie/flower trades for ~1 point at Museum
        # Points sell on market for ~$40-50k each
        items_per_trip = self.capacity
        points_per_trip = items_per_trip  # roughly 1 point per item
        gross_profit = points_per_trip * point_price
        round_trip_minutes = info["flight_minutes"] * 2

        return {
            "destination": destination,
            "items_carried": items_per_trip,
            "estimated_points": points_per_trip,
            "gross_profit": gross_profit,
            "round_trip_minutes": round_trip_minutes,
            "profit_per_hour": int(gross_profit / (round_trip_minutes / 60)) if round_trip_minutes > 0 else 0,
        }

    def is_traveling(self, travel_data: dict) -> bool:
        """Check if player is currently traveling."""
        return travel_data.get("time_left", 0) > 0
