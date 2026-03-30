"""Market module - item trading and arbitrage opportunities."""

from __future__ import annotations

import structlog

from torn_agent.api.client import TornAPI
from torn_agent.api.models import ItemMarketData

logger = structlog.get_logger()

# Common items worth monitoring for price dips
WATCHLIST_ITEMS = {
    # Drugs (high-value consumables)
    206: "Xanax",
    197: "Cannabis",
    196: "Ecstasy",
    # Temporary items
    366: "Feathery Hotel Coupon",
    367: "Erotic DVD",
    # Boosters
    614: "Energy Drink",
    # Medical
    68: "Morphine",
    66: "First Aid Kit",
    # Weapons (popular)
    233: "Kodachi",
}


class MarketModule:
    """Monitors market prices and identifies trading opportunities."""

    def __init__(self, api: TornAPI, max_spend: int = 100_000):
        self.api = api
        self.max_spend = max_spend
        self.price_history: dict[int, list[int]] = {}  # item_id -> [prices]

    async def scan_watchlist(self) -> list[dict]:
        """Scan all watchlist items and find deals."""
        opportunities = []
        for item_id, name in WATCHLIST_ITEMS.items():
            try:
                market_data = await self.api.get_market(item_id)
                analysis = self._analyze_listings(item_id, name, market_data)
                if analysis:
                    opportunities.append(analysis)
            except Exception as e:
                logger.warning("market_scan_error", item=name, error=str(e))
        return opportunities

    def _analyze_listings(
        self, item_id: int, name: str, data: ItemMarketData
    ) -> dict | None:
        """Analyze market listings to find underpriced items."""
        if not data.listings:
            return None

        prices = sorted(l.cost for l in data.listings if l.cost > 0)
        if len(prices) < 2:
            return None

        lowest = prices[0]
        median = prices[len(prices) // 2]

        # Track price history
        if item_id not in self.price_history:
            self.price_history[item_id] = []
        self.price_history[item_id].append(lowest)
        if len(self.price_history[item_id]) > 100:
            self.price_history[item_id] = self.price_history[item_id][-50:]

        # Flag if lowest price is significantly below median (potential deal)
        if median > 0 and lowest < median * 0.8 and lowest <= self.max_spend:
            return {
                "item_id": item_id,
                "name": name,
                "lowest_price": lowest,
                "median_price": median,
                "discount_pct": round((1 - lowest / median) * 100, 1),
                "recommendation": "buy",
                "reasoning": f"{name} at ${lowest:,} is {round((1 - lowest / median) * 100)}% below median ${median:,}",
            }
        return None

    async def check_points_market(self) -> dict:
        """Check if points are worth buying/selling."""
        data = await self.api.get_pointsmarket()
        points = data.get("pointsmarket", {})
        if not points:
            return {"recommendation": "skip", "reasoning": "No points market data"}

        prices = sorted(
            (v.get("cost", 0) for v in points.values() if isinstance(v, dict)),
        )
        if not prices:
            return {"recommendation": "skip", "reasoning": "No valid prices"}

        lowest = prices[0]
        return {
            "lowest_point_price": lowest,
            "recommendation": "info",
            "reasoning": f"Lowest point price: ${lowest:,}",
        }
