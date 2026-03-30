"""TORN API v2 async client with rate limiting."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx
import structlog

from torn_agent.api.models import (
    APIResponse,
    AttackTarget,
    CompanyProfile,
    FactionBasic,
    FactionMember,
    InventoryItem,
    ItemMarketData,
    MarketListing,
    TornItem,
    UserProfile,
)

logger = structlog.get_logger()

# TORN API allows 100 requests per minute per user
_RATE_LIMIT = 100
_RATE_WINDOW = 60  # seconds


class RateLimiter:
    """Token-bucket rate limiter for TORN API calls."""

    def __init__(self, max_calls: int = _RATE_LIMIT, period: float = _RATE_WINDOW):
        self._max_calls = max_calls
        self._period = period
        self._timestamps: list[float] = []

    async def acquire(self) -> None:
        now = time.monotonic()
        self._timestamps = [t for t in self._timestamps if now - t < self._period]
        if len(self._timestamps) >= self._max_calls:
            sleep_until = self._timestamps[0] + self._period
            await asyncio.sleep(sleep_until - now)
        self._timestamps.append(time.monotonic())


class TornAPI:
    """Async client for the TORN API v2.

    Provides typed methods for each major API category:
    user, faction, company, market, torn, property.
    """

    def __init__(self, api_key: str, base_url: str = "https://api.torn.com/v2"):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._base_url_v1 = "https://api.torn.com"
        self._rate_limiter = RateLimiter()
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={"Authorization": f"ApiKey {api_key}"},
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> TornAPI:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    # ── Raw request ──────────────────────────────────────────────────────

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make a rate-limited GET request to the TORN API."""
        await self._rate_limiter.acquire()
        url = f"{self._base_url}/{path.lstrip('/')}"
        logger.debug("torn_api_request", url=url, params=params)
        resp = await self._client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            logger.error("torn_api_error", error=data["error"], url=url)
            raise TornAPIError(data["error"])
        return data

    async def _get_v1(self, section: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make a rate-limited GET to the v1 API (some selections are v1-only)."""
        await self._rate_limiter.acquire()
        params = dict(params or {})
        params["key"] = self._api_key
        url = f"{self._base_url_v1}/{section}/"
        logger.debug("torn_api_v1_request", url=url, params=params)
        resp = await self._client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            logger.error("torn_api_error", error=data["error"], url=url)
            raise TornAPIError(data["error"])
        return data

    async def raw_get(self, path: str, params: dict[str, Any] | None = None) -> APIResponse:
        """Generic GET returning an APIResponse wrapper."""
        data = await self._get(path, params)
        return APIResponse(data=data)

    # ── User endpoints ───────────────────────────────────────────────────

    async def get_user(self, selections: str = "", user_id: int | None = None) -> dict[str, Any]:
        """Fetch user data. If user_id is None, fetches the authenticated user."""
        path = f"user/{user_id}" if user_id else "user"
        params = {"selections": selections} if selections else None
        return await self._get(path, params)

    async def get_my_profile(self) -> UserProfile:
        """Get full profile of the authenticated user."""
        data = await self.get_user(selections="profile,battlestats,bars,cooldowns,travel,money")
        return UserProfile.model_validate(data)

    async def get_my_bars(self) -> dict[str, Any]:
        """Get current energy, nerve, happy, life bars."""
        return await self.get_user(selections="bars")

    async def get_my_inventory(self) -> list[InventoryItem]:
        """Get the authenticated user's inventory."""
        data = await self.get_user(selections="inventory")
        items = data.get("inventory", [])
        return [InventoryItem.model_validate(item) for item in items]

    async def get_my_cooldowns(self) -> dict[str, Any]:
        """Get drug/booster/medical cooldowns."""
        return await self.get_user(selections="cooldowns")

    async def get_my_attacks(self) -> dict[str, Any]:
        """Get recent attack log."""
        return await self.get_user(selections="attacks")

    async def get_my_travel(self) -> dict[str, Any]:
        """Get travel status."""
        return await self.get_user(selections="travel")

    async def get_my_education(self) -> dict[str, Any]:
        """Get education courses status."""
        return await self.get_user(selections="education")

    async def get_my_crimes(self) -> dict[str, Any]:
        """Get crimes data."""
        return await self.get_user(selections="crimes")

    async def get_my_networth(self) -> dict[str, Any]:
        """Get networth breakdown."""
        return await self.get_user(selections="networth")

    async def get_my_perks(self) -> dict[str, Any]:
        """Get active perks, merits, and bonuses."""
        return await self.get_user(selections="perks")

    async def get_my_gym(self) -> dict[str, Any]:
        """Get gym/workout stats."""
        return await self.get_user(selections="gym")

    async def get_target_profile(self, user_id: int) -> AttackTarget:
        """Get basic profile of another player for attack evaluation."""
        data = await self.get_user(selections="profile", user_id=user_id)
        return AttackTarget(
            player_id=user_id,
            name=data.get("name", ""),
            level=data.get("level", 0),
            status=data.get("status", {}).get("state", ""),
            last_action=data.get("last_action", {}).get("relative", ""),
            faction_id=data.get("faction", {}).get("faction_id", 0),
            life_current=data.get("life", {}).get("current", 0),
            life_maximum=data.get("life", {}).get("maximum", 0),
        )

    # ── Faction endpoints ────────────────────────────────────────────────

    async def get_faction(
        self, selections: str = "", faction_id: int | None = None
    ) -> dict[str, Any]:
        """Fetch faction data."""
        path = f"faction/{faction_id}" if faction_id else "faction"
        params = {"selections": selections} if selections else None
        return await self._get(path, params)

    async def get_my_faction_basic(self) -> FactionBasic:
        data = await self.get_faction(selections="basic")
        return FactionBasic.model_validate(data)

    async def get_faction_members(self, faction_id: int | None = None) -> list[FactionMember]:
        data = await self.get_faction(selections="members", faction_id=faction_id)
        members = data.get("members", {})
        result = []
        for mid, mdata in members.items():
            mdata["id"] = int(mid)
            result.append(FactionMember.model_validate(mdata))
        return result

    async def get_faction_chain(self) -> dict[str, Any]:
        return await self.get_faction(selections="chain")

    async def get_faction_wars(self) -> dict[str, Any]:
        return await self.get_faction(selections="wars")

    # ── Company endpoints ────────────────────────────────────────────────

    async def get_company(
        self, selections: str = "", company_id: int | None = None
    ) -> dict[str, Any]:
        path = f"company/{company_id}" if company_id else "company"
        params = {"selections": selections} if selections else None
        return await self._get(path, params)

    async def get_my_company(self) -> CompanyProfile:
        data = await self.get_company(selections="profile")
        return CompanyProfile.model_validate(data)

    # ── Market endpoints ─────────────────────────────────────────────────

    async def get_market(self, item_id: int) -> ItemMarketData:
        """Get market listings for a specific item."""
        data = await self._get(f"market/{item_id}", {"selections": "itemmarket"})
        listings_raw = data.get("itemmarket", [])
        listings = [MarketListing.model_validate(l) for l in listings_raw]
        return ItemMarketData(item_id=item_id, listings=listings)

    async def get_pointsmarket(self) -> dict[str, Any]:
        return await self._get("market", {"selections": "pointsmarket"})

    # ── Torn (game data) endpoints ───────────────────────────────────────

    async def get_torn(self, selections: str = "") -> dict[str, Any]:
        params = {"selections": selections} if selections else None
        return await self._get("torn", params)

    async def get_torn_items(self) -> dict[str, TornItem]:
        data = await self.get_torn(selections="items")
        items = data.get("items", {})
        return {k: TornItem.model_validate(v) for k, v in items.items()}

    async def get_torn_gym(self) -> dict[str, Any]:
        return await self.get_torn(selections="gyms")

    async def get_torn_companies(self) -> dict[str, Any]:
        return await self.get_torn(selections="companies")

    async def get_torn_properties(self) -> dict[str, Any]:
        return await self.get_torn(selections="properties")

    # ── Property endpoints ───────────────────────────────────────────────

    async def get_property(self, property_id: int | None = None) -> dict[str, Any]:
        path = f"property/{property_id}" if property_id else "property"
        return await self._get(path)


class TornAPIError(Exception):
    """Raised when the TORN API returns an error object."""

    def __init__(self, error: dict[str, Any]):
        self.code = error.get("code", 0)
        self.message = error.get("error", "Unknown error")
        super().__init__(f"TORN API Error {self.code}: {self.message}")
