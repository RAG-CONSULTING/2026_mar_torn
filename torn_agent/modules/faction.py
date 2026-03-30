"""Faction module - chain management and faction coordination."""

from __future__ import annotations

import structlog

from torn_agent.api.client import TornAPI

logger = structlog.get_logger()


class FactionModule:
    """Handles faction-related strategy: chains, wars, and coordination."""

    def __init__(self, api: TornAPI):
        self.api = api

    async def get_chain_status(self) -> dict:
        """Get current chain status with recommendations."""
        chain_data = await self.api.get_faction_chain()
        chain = chain_data.get("chain", {})

        current = chain.get("current", 0)
        timeout = chain.get("timeout", 0)
        max_chain = chain.get("max", 0)

        status = {
            "current_chain": current,
            "max_chain": max_chain,
            "timeout_seconds": timeout,
            "is_active": current > 0,
            "urgent": timeout < 90 and current > 0,
            "recommendation": "none",
            "reasoning": "",
        }

        if current == 0:
            status["recommendation"] = "start_chain"
            status["reasoning"] = "No active chain - consider starting one"
        elif timeout < 60:
            status["recommendation"] = "chain_hit_urgent"
            status["reasoning"] = f"Chain at {current} about to expire in {timeout}s - HIT NOW"
        elif timeout < 180:
            status["recommendation"] = "chain_hit_soon"
            status["reasoning"] = f"Chain at {current} needs refresh within {timeout}s"
        else:
            status["recommendation"] = "chain_healthy"
            status["reasoning"] = f"Chain at {current} healthy with {timeout}s remaining"

        return status

    async def find_active_members(self) -> list[dict]:
        """Find faction members who are currently active (online recently)."""
        members = await self.api.get_faction_members()
        active = []
        for member in members:
            if member.status.state == "Okay":
                active.append({
                    "id": member.id,
                    "name": member.name,
                    "level": member.level,
                    "status": member.status.state,
                    "last_action": member.last_action,
                    "position": member.position,
                })
        return active

    async def get_war_status(self) -> dict:
        """Check if faction is currently at war."""
        wars_data = await self.api.get_faction_wars()
        wars = wars_data.get("wars", {})
        active_wars = {k: v for k, v in wars.items() if isinstance(v, dict)}
        return {
            "at_war": len(active_wars) > 0,
            "war_count": len(active_wars),
            "wars": active_wars,
        }
