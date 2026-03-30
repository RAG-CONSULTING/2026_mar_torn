"""Travel module - foreign stock trading and travel planning."""

from __future__ import annotations

import structlog

logger = structlog.get_logger()

# Travel destinations and their notable items for arbitrage
DESTINATIONS = {
    "Mexico": {
        "flight_time_minutes": 26,
        "notable_items": ["Xanax", "Feathery Hotel Coupon"],
    },
    "Cayman Islands": {
        "flight_time_minutes": 35,
        "notable_items": ["Feathery Hotel Coupon"],
    },
    "Canada": {
        "flight_time_minutes": 41,
        "notable_items": ["Xanax"],
    },
    "Hawaii": {
        "flight_time_minutes": 134,
        "notable_items": ["Feathery Hotel Coupon"],
    },
    "United Kingdom": {
        "flight_time_minutes": 159,
        "notable_items": ["Donator Pack"],
    },
    "Argentina": {
        "flight_time_minutes": 167,
        "notable_items": ["Feathery Hotel Coupon"],
    },
    "Switzerland": {
        "flight_time_minutes": 175,
        "notable_items": ["Feathery Hotel Coupon"],
    },
    "Japan": {
        "flight_time_minutes": 225,
        "notable_items": ["Xanax"],
    },
    "China": {
        "flight_time_minutes": 242,
        "notable_items": ["Feathery Hotel Coupon"],
    },
    "UAE": {
        "flight_time_minutes": 242,
        "notable_items": ["Xanax", "Feathery Hotel Coupon"],
    },
    "South Africa": {
        "flight_time_minutes": 272,
        "notable_items": ["Feathery Hotel Coupon"],
    },
}


class TravelModule:
    """Plans travel for foreign stock purchases and item arbitrage."""

    def __init__(self, cash_available: int = 0):
        self.cash_available = cash_available

    def recommend_destination(
        self,
        current_status: str,
        available_time_minutes: int = 300,
    ) -> dict:
        """Recommend a travel destination based on time and profit potential."""
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

        viable = {
            name: info
            for name, info in DESTINATIONS.items()
            if info["flight_time_minutes"] * 2 <= available_time_minutes
        }

        if not viable:
            return {
                "recommendation": "skip",
                "reasoning": "Not enough time for any round trip",
            }

        # Prefer short trips for efficiency, but longer trips may have better items
        best = min(viable.items(), key=lambda x: x[1]["flight_time_minutes"])
        return {
            "recommendation": "travel",
            "destination": best[0],
            "flight_time_minutes": best[1]["flight_time_minutes"],
            "notable_items": best[1]["notable_items"],
            "reasoning": f"Quick trip to {best[0]} ({best[1]['flight_time_minutes']}min) for {', '.join(best[1]['notable_items'])}",
        }

    def is_traveling(self, travel_data: dict) -> bool:
        """Check if player is currently traveling."""
        return travel_data.get("time_left", 0) > 0
