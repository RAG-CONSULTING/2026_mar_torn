"""Tool definitions for the Claude agent to interact with TORN.

Each tool maps to a TORN API call or a gameplay decision. Claude uses these
tools to observe the game state and decide on actions.
"""

from __future__ import annotations

TORN_TOOLS: list[dict] = [
    # ── Observation tools ────────────────────────────────────────────────
    {
        "name": "get_my_status",
        "description": (
            "Get your current player status including energy, nerve, happy, life bars, "
            "battle stats, cooldowns, travel state, money on hand, and overall status "
            "(Okay/Hospital/Jail/Traveling/Abroad). Call this first every loop to decide "
            "what actions are available."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_my_inventory",
        "description": (
            "Get your current inventory of items including weapons, armor, drugs, "
            "boosters, medical items, and their quantities."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_my_attacks",
        "description": "Get your recent attack history to analyze win/loss patterns and respect gains.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_my_crimes",
        "description": "Get your crimes data to see available crime options and recent crime results.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_my_education",
        "description": "Check your current education course progress and available courses.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_my_perks",
        "description": "Get your active perks, merits, education perks, and faction perks.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_my_networth",
        "description": "Get a detailed breakdown of your networth across all asset categories.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "scout_target",
        "description": (
            "Scout a potential attack target by their player ID. Returns their level, "
            "status, life, faction, and last action time. Use this before deciding to "
            "attack someone."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "target_id": {
                    "type": "integer",
                    "description": "The player ID of the target to scout.",
                },
            },
            "required": ["target_id"],
        },
    },
    {
        "name": "get_faction_info",
        "description": "Get your faction's basic info including respect, member count, and chain status.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_faction_chain",
        "description": (
            "Get the current faction chain status. Important for timing attacks to "
            "maintain or build chains."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_faction_members",
        "description": "Get list of all faction members with their status and last action.",
        "input_schema": {
            "type": "object",
            "properties": {
                "faction_id": {
                    "type": "integer",
                    "description": "Faction ID to look up. Omit for your own faction.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_company_info",
        "description": "Get your company profile including rating, income, and employee info.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "check_market_prices",
        "description": (
            "Check current market listings for a specific item by ID. Useful for "
            "finding deals or pricing items to sell."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "integer",
                    "description": "The item ID to check market prices for.",
                },
            },
            "required": ["item_id"],
        },
    },
    {
        "name": "check_points_market",
        "description": "Check the current points market for buying/selling points.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_travel_info",
        "description": "Get current travel status and destination info.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },

    # ── Action / Decision tools ──────────────────────────────────────────
    {
        "name": "recommend_action",
        "description": (
            "After analyzing the game state, recommend the best action(s) to take. "
            "This records your strategic recommendation which will be executed if not "
            "in dry-run mode. Actions: train_gym, commit_crime, use_item, attack_target, "
            "travel, buy_market, sell_market, wait, refill_energy, chain_attack."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "train_gym",
                        "commit_crime",
                        "use_item",
                        "attack_target",
                        "travel",
                        "buy_market",
                        "sell_market",
                        "wait",
                        "refill_energy",
                        "chain_attack",
                    ],
                    "description": "The action type to recommend.",
                },
                "reasoning": {
                    "type": "string",
                    "description": "Your strategic reasoning for this recommendation.",
                },
                "priority": {
                    "type": "integer",
                    "description": "Priority 1-10 (10=urgent). Helps order multiple recommendations.",
                    "minimum": 1,
                    "maximum": 10,
                },
                "parameters": {
                    "type": "object",
                    "description": (
                        "Action-specific parameters. E.g. {'stat': 'strength'} for gym, "
                        "{'target_id': 123} for attack, {'item_id': 456, 'quantity': 1} for items."
                    ),
                },
                "wait_seconds": {
                    "type": "integer",
                    "description": "If action is 'wait', how many seconds to wait before next check.",
                },
            },
            "required": ["action", "reasoning", "priority"],
        },
    },
    {
        "name": "log_observation",
        "description": (
            "Log a strategic observation or insight about the current game state. "
            "This helps build a history of observations for long-term strategy."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["combat", "economy", "faction", "training", "travel", "general"],
                    "description": "Category of the observation.",
                },
                "observation": {
                    "type": "string",
                    "description": "The observation or insight.",
                },
                "importance": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                },
            },
            "required": ["category", "observation", "importance"],
        },
    },
]
