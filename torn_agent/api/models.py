"""Pydantic models for TORN API v2 responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── User models ──────────────────────────────────────────────────────────────


class BattleStats(BaseModel):
    strength: float = 0
    defense: float = 0
    speed: float = 0
    dexterity: float = 0
    total: float = 0


class PlayerBars(BaseModel):
    current: int = 0
    maximum: int = 0
    ticktime: int = 0  # seconds until next tick
    fulltime: int = 0  # seconds until full
    interval: int = 0  # seconds between ticks
    increment: int = 0


class CooldownInfo(BaseModel):
    drug: int = 0
    booster: int = 0
    medical: int = 0


class TravelInfo(BaseModel):
    destination: str = ""
    timestamp: int = 0
    departed: int = 0
    time_left: int = 0


class StatusInfo(BaseModel):
    description: str = ""
    details: str = ""
    state: str = ""  # "Okay", "Hospital", "Jail", "Traveling", "Abroad"
    color: str = ""
    until: int = 0


class UserProfile(BaseModel):
    player_id: int = Field(0, alias="player_id")
    name: str = ""
    level: int = 0
    gender: str = ""
    status: StatusInfo = Field(default_factory=StatusInfo)
    life: PlayerBars = Field(default_factory=PlayerBars)
    energy: PlayerBars = Field(default_factory=PlayerBars)
    nerve: PlayerBars = Field(default_factory=PlayerBars)
    happy: PlayerBars = Field(default_factory=PlayerBars)
    battle_stats: BattleStats = Field(default_factory=BattleStats)
    cooldowns: CooldownInfo = Field(default_factory=CooldownInfo)
    travel: TravelInfo = Field(default_factory=TravelInfo)
    money_onhand: int = 0
    points: int = 0
    networth: int = 0
    rank: str = ""
    age: int = 0  # days since signup
    last_action: str = ""
    faction_id: int = 0
    company_id: int = 0

    model_config = {"populate_by_name": True, "extra": "allow"}


# ── Inventory / Items ────────────────────────────────────────────────────────


class InventoryItem(BaseModel):
    id: int = 0
    name: str = ""
    type: str = ""
    quantity: int = 0
    equipped: bool = False
    market_price: int = 0

    model_config = {"extra": "allow"}


# ── Attack / Combat ──────────────────────────────────────────────────────────


class AttackResult(BaseModel):
    code: int = 0
    attacker_id: int = 0
    defender_id: int = 0
    result: str = ""  # "Attacked", "Hospitalized", "Mugged", "Lost"
    respect: float = 0
    timestamp_started: int = 0
    timestamp_ended: int = 0

    model_config = {"extra": "allow"}


class AttackTarget(BaseModel):
    """A potential attack target with scouted information."""
    player_id: int
    name: str = ""
    level: int = 0
    status: str = ""
    last_action: str = ""
    estimated_stats_total: float = 0
    faction_id: int = 0
    life_current: int = 0
    life_maximum: int = 0

    model_config = {"extra": "allow"}


# ── Faction ──────────────────────────────────────────────────────────────────


class FactionBasic(BaseModel):
    id: int = 0
    name: str = ""
    tag: str = ""
    leader: int = 0
    co_leader: int = 0
    respect: int = 0
    members: int = 0
    best_chain: int = 0

    model_config = {"extra": "allow"}


class FactionMember(BaseModel):
    id: int = 0
    name: str = ""
    level: int = 0
    days_in_faction: int = 0
    status: StatusInfo = Field(default_factory=StatusInfo)
    last_action: str = ""
    position: str = ""

    model_config = {"extra": "allow"}


# ── Market ───────────────────────────────────────────────────────────────────


class MarketListing(BaseModel):
    id: int = 0
    cost: int = 0
    quantity: int = 0

    model_config = {"extra": "allow"}


class ItemMarketData(BaseModel):
    item_id: int = 0
    name: str = ""
    listings: list[MarketListing] = Field(default_factory=list)

    model_config = {"extra": "allow"}


# ── Company ──────────────────────────────────────────────────────────────────


class CompanyProfile(BaseModel):
    id: int = 0
    name: str = ""
    company_type: int = 0
    rating: int = 0
    director: int = 0
    employees_hired: int = 0
    employees_capacity: int = 0
    daily_income: int = 0
    weekly_income: int = 0
    popularity: int = 0
    efficiency: int = 0

    model_config = {"extra": "allow"}


# ── Torn (game data) ────────────────────────────────────────────────────────


class TornItem(BaseModel):
    id: int = 0
    name: str = ""
    description: str = ""
    type: str = ""
    buy_price: int = 0
    sell_price: int = 0
    market_value: int = 0
    circulation: int = 0

    model_config = {"extra": "allow"}


# ── Crimes ───────────────────────────────────────────────────────────────────


class CrimeOption(BaseModel):
    nerve_cost: int = 0
    name: str = ""
    action: str = ""

    model_config = {"extra": "allow"}


# ── Generic wrapper ──────────────────────────────────────────────────────────


class APIResponse(BaseModel):
    """Generic wrapper for any TORN API response."""
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    error: dict[str, Any] | None = None

    model_config = {"extra": "allow"}
