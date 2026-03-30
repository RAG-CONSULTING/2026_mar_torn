"""The AI brain: Claude Opus 4.6 agent that plays TORN.

This module wires Claude's tool-use capability to the TORN API,
letting the model observe game state and recommend actions.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import anthropic
import structlog

from torn_agent.api.client import TornAPI
from torn_agent.agent.tools import TORN_TOOLS
from torn_agent.config.settings import Settings

logger = structlog.get_logger()

SYSTEM_PROMPT = """\
You are an expert TORN City player AI agent. Your player ID is {player_id}.

Your goal is to optimally play TORN by making strategic decisions about:
- **Gym Training**: Spend energy training battle stats. Prioritize the stat that gives
  best returns for your current build. Consider happy bonus (2x gains when happy > 99%).
- **Crimes**: Spend nerve on crimes for money and stat gains. Pick crimes with best
  success rate vs reward.
- **Attacks**: Find suitable targets for respect gains and faction chains. Only attack
  targets you can beat. Avoid attacking faction allies or players much stronger than you.
- **Items**: Use medical items when low on life. Use drugs/boosters strategically
  considering cooldowns. Equip best weapons/armor.
- **Travel**: Travel abroad to buy special items cheaply and sell at home for profit.
- **Market**: Buy underpriced items, sell overpriced ones. Monitor points market.
- **Faction**: Maintain chains, participate in wars, coordinate with faction members.

STRATEGY PRIORITIES:
1. Stay alive - heal if life is low, avoid attacks when weak
2. Never waste energy - always train when energy is available
3. Use nerve on crimes when available
4. Build chain when faction is chaining
5. Make money through market arbitrage and travel
6. Keep happy high for training bonuses (use candy/boosters)

CONSTRAINTS:
- You are {mode}. {"Log recommendations but don't execute." if dry_run else "Execute recommended actions."}
- Maximum spend per action: ${max_spend:,}
- Attacks enabled: {attacks_enabled}
- Travel enabled: {travel_enabled}
- Market trading enabled: {market_enabled}

CURRENT TIME: {current_time}

Always start by calling get_my_status to understand your current state before making
any decisions. Use multiple tools to gather information, then call recommend_action
with your strategic decision.
"""


class ActionRecommendation:
    """A recommended action from the AI agent."""

    def __init__(
        self,
        action: str,
        reasoning: str,
        priority: int,
        parameters: dict[str, Any] | None = None,
        wait_seconds: int | None = None,
    ):
        self.action = action
        self.reasoning = reasoning
        self.priority = priority
        self.parameters = parameters or {}
        self.wait_seconds = wait_seconds
        self.timestamp = datetime.now(timezone.utc)

    def __repr__(self) -> str:
        return f"Action({self.action}, priority={self.priority}, reason={self.reasoning[:60]})"


class Observation:
    """A logged strategic observation."""

    def __init__(self, category: str, observation: str, importance: str):
        self.category = category
        self.observation = observation
        self.importance = importance
        self.timestamp = datetime.now(timezone.utc)


class TornAgentBrain:
    """Claude-powered AI agent that plays TORN.

    Each 'think' cycle:
    1. Sends game context + tools to Claude
    2. Claude calls tools to observe game state via TORN API
    3. Claude recommends actions based on observations
    4. Actions are collected and returned for execution
    """

    def __init__(self, settings: Settings, torn_api: TornAPI):
        self.settings = settings
        self.api = torn_api
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.recommendations: list[ActionRecommendation] = []
        self.observations: list[Observation] = []
        self.history: list[dict[str, Any]] = []  # conversation turns for context

    def _build_system_prompt(self) -> str:
        return SYSTEM_PROMPT.format(
            player_id=self.settings.torn_player_id,
            mode="in DRY RUN mode" if self.settings.dry_run else "in LIVE mode",
            dry_run=self.settings.dry_run,
            max_spend=self.settings.max_spend_per_action,
            attacks_enabled=self.settings.enable_attacks,
            travel_enabled=self.settings.enable_travel,
            market_enabled=self.settings.enable_market,
            current_time=datetime.now(timezone.utc).isoformat(),
        )

    async def _execute_tool(self, tool_name: str, tool_input: dict[str, Any]) -> str:
        """Execute a tool call by routing to the appropriate TORN API method."""
        try:
            match tool_name:
                # Observation tools
                case "get_my_status":
                    result = await self.api.get_user(
                        selections="profile,bars,cooldowns,travel,money,battlestats"
                    )
                case "get_my_inventory":
                    items = await self.api.get_my_inventory()
                    result = [item.model_dump() for item in items]
                case "get_my_attacks":
                    result = await self.api.get_my_attacks()
                case "get_my_crimes":
                    result = await self.api.get_my_crimes()
                case "get_my_education":
                    result = await self.api.get_my_education()
                case "get_my_perks":
                    result = await self.api.get_my_perks()
                case "get_my_networth":
                    result = await self.api.get_my_networth()
                case "scout_target":
                    target = await self.api.get_target_profile(tool_input["target_id"])
                    result = target.model_dump()
                case "get_faction_info":
                    faction = await self.api.get_my_faction_basic()
                    result = faction.model_dump()
                case "get_faction_chain":
                    result = await self.api.get_faction_chain()
                case "get_faction_members":
                    fid = tool_input.get("faction_id")
                    members = await self.api.get_faction_members(faction_id=fid)
                    result = [m.model_dump() for m in members]
                case "get_company_info":
                    company = await self.api.get_my_company()
                    result = company.model_dump()
                case "check_market_prices":
                    market = await self.api.get_market(tool_input["item_id"])
                    result = market.model_dump()
                case "check_points_market":
                    result = await self.api.get_pointsmarket()
                case "get_travel_info":
                    result = await self.api.get_my_travel()

                # Decision tools
                case "recommend_action":
                    rec = ActionRecommendation(
                        action=tool_input["action"],
                        reasoning=tool_input["reasoning"],
                        priority=tool_input["priority"],
                        parameters=tool_input.get("parameters"),
                        wait_seconds=tool_input.get("wait_seconds"),
                    )
                    self.recommendations.append(rec)
                    logger.info(
                        "action_recommended",
                        action=rec.action,
                        priority=rec.priority,
                        reasoning=rec.reasoning,
                    )
                    result = {"status": "recorded", "action": rec.action}

                case "log_observation":
                    obs = Observation(
                        category=tool_input["category"],
                        observation=tool_input["observation"],
                        importance=tool_input["importance"],
                    )
                    self.observations.append(obs)
                    logger.info(
                        "observation_logged",
                        category=obs.category,
                        importance=obs.importance,
                        observation=obs.observation[:100],
                    )
                    result = {"status": "logged"}

                case _:
                    result = {"error": f"Unknown tool: {tool_name}"}

            return json.dumps(result, default=str)

        except Exception as e:
            logger.error("tool_execution_error", tool=tool_name, error=str(e))
            return json.dumps({"error": str(e)})

    async def think(self, extra_context: str = "") -> list[ActionRecommendation]:
        """Run one thinking cycle.

        Claude observes the game state via tools, reasons about strategy,
        and returns a list of recommended actions sorted by priority.
        """
        self.recommendations = []

        messages: list[dict[str, Any]] = []

        # Add recent history for continuity (last 3 cycles)
        for entry in self.history[-6:]:
            messages.append(entry)

        # Add current turn
        user_content = "Analyze the current game state and recommend the best actions to take."
        if extra_context:
            user_content += f"\n\nAdditional context: {extra_context}"
        if self.observations:
            recent_obs = self.observations[-10:]
            obs_text = "\n".join(
                f"- [{o.importance}] {o.category}: {o.observation}" for o in recent_obs
            )
            user_content += f"\n\nRecent observations:\n{obs_text}"

        messages.append({"role": "user", "content": user_content})

        # Agentic loop: keep calling Claude until it stops using tools
        response = self.client.messages.create(
            model=self.settings.claude_model,
            max_tokens=4096,
            system=self._build_system_prompt(),
            tools=TORN_TOOLS,
            messages=messages,
        )

        while response.stop_reason == "tool_use":
            # Process all tool calls in this response
            tool_results = []
            assistant_content = response.content

            for block in response.content:
                if block.type == "tool_use":
                    logger.debug("tool_call", tool=block.name, input=block.input)
                    result_str = await self._execute_tool(block.name, block.input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_str,
                        }
                    )

            messages.append({"role": "assistant", "content": assistant_content})
            messages.append({"role": "user", "content": tool_results})

            response = self.client.messages.create(
                model=self.settings.claude_model,
                max_tokens=4096,
                system=self._build_system_prompt(),
                tools=TORN_TOOLS,
                messages=messages,
            )

        # Extract final text response
        final_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                final_text += block.text

        if final_text:
            logger.info("agent_summary", summary=final_text[:500])

        # Save conversation to history
        self.history.append({"role": "user", "content": user_content})
        self.history.append({"role": "assistant", "content": final_text})

        # Trim history to prevent unbounded growth
        if len(self.history) > 20:
            self.history = self.history[-12:]

        # Sort recommendations by priority (highest first)
        self.recommendations.sort(key=lambda r: r.priority, reverse=True)
        return self.recommendations
