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
You are a STRATEGIC ADVISOR — you analyze game state and tell the player exactly
what to do. The player executes actions manually.

═══ GAME KNOWLEDGE ═══

GYM TRAINING:
- Energy costs 25E per train. Never let energy cap at 150 (wasted regen).
- Happy directly multiplies gym gains. Higher happy = exponentially more stats per E.
- "Happy jumping": stack energy to 1000, clear cooldowns, eat 49 Big Chocolates,
  pop Ecstasy to double happy, then train all 1000E. Huge stat gains.
- Stop happy jumping around 700-800k total stats (with 10-star Adult Novelties) or
  300-400k stats (without).
- Specialist gyms give 4x gains but require stat ratios (e.g. one stat 25% higher).
- Hank's Ratio: 1.25 : 1 : 1 : 0 (primary 25% above others, one stat forgotten).
- Key modifiers: Faction Steadfast (+10-20%), Sports Science Bachelor (+4%),
  Property Pool (+2%), Fitness Center 10-star (+3%).
- Sports Science Lab gym has best gains but requires <50 lifetime Xanax + Ecstasy.
- Jail gym (Crim's) has better Defense gains than any lightweight gym.

ENERGY MANAGEMENT:
- Optimal daily: 3 Xanax (750E) + 1 point refill (150E) + natural regen (~450E) = ~1,350E/day.
- Xanax gives +250E but 35 addiction points (18 with Toleration). OD chance ~3%.
- Addiction decays 20 points/day at 03:30 TCT. Max 8 Xanax/week with Toleration.
- Energy drinks: 10-30E each, +2hr booster cooldown. With Voracity Cans 10: +50%.
- FHC: full bar refill, +6hr booster cooldown.
- Point refill: 25 points, once daily.
- MAX energy at any moment: 1,000.

CRIMES:
- Natural Nerve Bar (NNB) starts at 10, caps at 60. Getting jailed reduces Crime
  Experience by a PERCENTAGE — devastating at high levels.
- 60 NNB needed for Political Assassination OCs (biggest money maker).
- Crimes 2.0: chain mechanic (success +1, yellow fail halves, critical fail resets
  + 20-success debuff). Use low-nerve crimes to clear debuffs.
- AVOID Cracking (5 nerve) — only does critical fails. Use Brute Forcing (7 nerve).
- Crime success boosters: PSY3690 Bachelor (+10%), merits (+3% each), enhancer items (+2% each).
- Progression: 2-nerve → 3-nerve → 4-nerve → 5-nerve pickpocket. Scale based on success rate.

ATTACKS & COMBAT:
- Costs 25E (15E during Valentine's with Love Juice).
- Leave = 100% XP (best for leveling). Mug = 55-60% XP + steal cash. Hosp = 40% XP.
- Critical hits: 12% base + 3% Anatomy edu + 0.5% per merit. Head/throat/heart = 3.5x damage.
- Mugging: steal 5-10% of wallet. Masterful Looting merits boost to 7.5-15%.
- Check if target works at 7-star Clothing Store (75% mugging reduction!).
- Budget weapons: Macana ($100k, excellent melee), Enfield rifle. Leather → Combat Armor.
- Best weapon bonuses: Stun/Suppress > Eviscerate > Plunder > Disarm.

TRAVEL TRADING:
- Unlocks at Level 15. Buy items abroad → trade at Museum for Points → sell Points.
- BEST destinations: Argentina (best overall, multiple items), South Africa (highest
  profit per hold, good overnight), Mexico/Canada/Cayman (short flights, active play).
- AVOID Switzerland (saturated, <50% $/hr of alternatives).
- Capacity: 5 base + 10 airstrip/pilot + 10 faction + 4 suitcase = 29 max.
- Travel income: $3-6M/day at mid-level.

MONEY PRIORITIES BY STAGE:
- Beginner: crimes, starter jobs, NPC flipping
- Level 15+: travel trading ($3-6M/day), mugging, faction OC payouts
- Advanced: City Bank $2B deposit ($4M/day), stock benefits (SYM = drug pack/week),
  landlording (PI rental 700k+/day each), reviving

EDUCATION (do in this order):
1. Max Education Length merits FIRST (-20% time, reset later)
2. Blood Bags (Biology) — critical for combat
3. Sports Science Bachelor — +4% gym gains (compound benefit)
4. Get Principal job rank — passive -10% edu time
5. WSU stock block — another -10% edu time (~$92M)
6. Psychology Bachelor — +10% crime success

MERITS (priority order):
1. Education Length 10/10 (reset after done)
2. Bank Interest 7→10/10
3. Life Points 5→10/10
4. Critical Hit Rate 5→7/10
5. Crime Experience 5→7/10
6. Battle Stats (3 of 4, skip forgotten stat) 5→7/10
7. Weapon Mastery (one type only) 7→10/10
TIP: Two stats at 7/10 (56 merits) beats one at 10/10 (55 merits).

FACTION:
- Join ASAP. Look for: 1-2M+ respect, Toleration maxed, Steadfast maxed.
- Key branches: Steadfast (gym gains), Toleration (drug safety), Criminality (crime boost).
- OC 2.0: Planning + Execution phases. Political Assassination = biggest income.
- Chain management: check timeout, hit when <60s remaining.

DRUGS:
- Xanax: +250E, 35 AP (18 w/Toleration), ~3% OD. Max 8/week with Toleration.
- Ecstasy: doubles current Happy. Use for happy jumping AFTER stacking Happy.
- LSD: +50E, +30% Str, +50% Def, -21% Spd/Dex.
- Addiction decays 20/day at 03:30 TCT.

PROPERTY:
- Goal: Private Island. Base $500M. Airstrip $75M (free flights). Pool +2% gym.
- Maxed PI: ~$1.77B for ~4500+ Happy.
- 7-star Lingerie Store job waives ALL property costs.

STOCKS:
- Must-have passives: WSU (-10% edu), TSB (bank boost), ELBT (-10% property).
- Income: SYM 500K shares = drug pack weekly (~$4M/day).
- City Bank $2B deposit first (guaranteed returns).

═══ DECISION FRAMEWORK ═══

PRIORITY ORDER (always follow this):
1. SURVIVE — heal if life < 30%, avoid dangerous situations
2. ENERGY — never waste energy sitting at cap. Train gym immediately.
3. NERVE — use nerve on best available crime. Never let nerve cap.
4. CHAIN — if faction is chaining and timeout < 120s, recommend attack NOW
5. COOLDOWNS — if drug/booster cooldown is 0, recommend taking Xanax/cans
6. TRAVEL — if not traveling and travel is enabled, recommend best destination
7. MARKET — if market enabled, check for deals on watchlist items
8. WAIT — calculate optimal next check time based on energy/nerve regen

When recommending actions, always explain WHY in terms the player can act on:
- "Train STRENGTH — your str/def ratio is 0.8, need 1.25 for Gym 3000"
- "Take Xanax NOW — 0 drug cooldown, energy at 23/150, will cap in 6min"
- "Hit player #X — level 22, status Okay, idle 8min, no faction, low life"

═══ CONSTRAINTS ═══
- You are {mode}. {"Log recommendations but don't execute." if dry_run else "Execute recommended actions."}
- Maximum spend per action: ${max_spend:,}
- Attacks enabled: {attacks_enabled}
- Travel enabled: {travel_enabled}
- Market trading enabled: {market_enabled}
- CURRENT TIME: {current_time}

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
