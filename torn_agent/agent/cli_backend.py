"""Claude CLI brain backend — uses your Claude Max subscription via `claude` CLI.

Instead of calling the Anthropic API (which requires API credits), this backend
shells out to the `claude` CLI tool. Since you're authenticated via Claude Code
with your Max subscription, this costs nothing extra.

Strategy: gather all TORN API data first, then pass the full game state to Claude
in a single prompt for analysis. This is more efficient than multi-turn tool loops
and works perfectly with the CLI's print mode.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

import structlog

from torn_agent.api.client import TornAPI, TornAPIError
from torn_agent.config.settings import Settings

logger = structlog.get_logger()

# Selections to fetch each cycle — covers all key game state
_PLAYER_SELECTIONS = "profile,bars,battlestats,cooldowns,travel,money,perks"
_EXTRA_SELECTIONS = ["attacks", "crimes", "inventory", "education", "networth"]


async def gather_game_state(api: TornAPI) -> dict[str, Any]:
    """Fetch all relevant game state from TORN API in parallel.

    Returns a single dict with all data needed for Claude to make decisions.
    """
    state: dict[str, Any] = {}

    # Core player data (always fetch)
    try:
        state["player"] = await api.get_user(selections=_PLAYER_SELECTIONS)
    except TornAPIError as e:
        state["player_error"] = str(e)

    # Parallel fetch of additional data
    tasks = {
        "attacks": api.get_my_attacks(),
        "crimes": api.get_my_crimes(),
        "education": api.get_my_education(),
    }

    # Faction data
    tasks["faction_basic"] = api.get_faction(selections="basic")
    tasks["faction_chain"] = api.get_faction_chain()

    results = await asyncio.gather(
        *tasks.values(),
        return_exceptions=True,
    )

    for key, result in zip(tasks.keys(), results):
        if isinstance(result, Exception):
            state[f"{key}_error"] = str(result)
            logger.debug("state_fetch_error", key=key, error=str(result))
        else:
            state[key] = result

    state["timestamp"] = datetime.now(timezone.utc).isoformat()
    return state


def build_analysis_prompt(
    system_prompt: str,
    game_state: dict[str, Any],
    extra_context: str = "",
    recent_observations: list[str] | None = None,
) -> str:
    """Build a single prompt containing all game state for Claude to analyze.

    Instead of multi-turn tool calls, we pre-fetch everything and let Claude
    analyze it all at once. This is more efficient for the CLI backend.
    """
    parts = [
        system_prompt,
        "\n═══ CURRENT GAME STATE ═══\n",
        "The following data was just fetched from the TORN API:\n",
        "```json",
        json.dumps(game_state, indent=2, default=str),
        "```\n",
    ]

    if extra_context:
        parts.append(f"\nAdditional context: {extra_context}\n")

    if recent_observations:
        parts.append("\nRecent observations from previous cycles:")
        for obs in recent_observations:
            parts.append(f"  - {obs}")
        parts.append("")

    parts.append(
        "\nBased on the game state above, analyze the situation and provide your "
        "strategic recommendations. For EACH recommendation, output a JSON block:\n"
        "```json\n"
        '{"action": "<action_type>", "reasoning": "<why>", "priority": <1-10>, '
        '"parameters": {<action-specific params>}}\n'
        "```\n"
        "\nValid actions: train_gym, commit_crime, use_item, attack_target, "
        "travel, buy_market, sell_market, wait, refill_energy, chain_attack\n"
        "\nProvide 1-3 recommendations ordered by priority. Include specific "
        "details (which stat to train, which crime, target ID, etc)."
    )

    return "\n".join(parts)


async def invoke_claude_cli(
    prompt: str,
    model: str = "sonnet",
) -> str:
    """Invoke the `claude` CLI in print mode and return the response text.

    Uses the user's Claude Max subscription — zero API cost.
    """
    cmd = [
        "claude",
        "-p",  # print mode
        "--output-format", "json",
        "--max-turns", "1",
    ]

    logger.debug("cli_invoke", model=model, prompt_len=len(prompt))

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await process.communicate(input=prompt.encode())

    if process.returncode != 0:
        error_msg = stderr.decode().strip()
        logger.error("cli_error", returncode=process.returncode, stderr=error_msg[:500])
        raise RuntimeError(f"claude CLI failed (exit {process.returncode}): {error_msg[:200]}")

    response = json.loads(stdout.decode())
    result_text = response.get("result", "")
    cost = response.get("total_cost_usd", 0)

    logger.info(
        "cli_response",
        cost_usd=cost,
        result_len=len(result_text),
        session_id=response.get("session_id", "")[:12],
    )

    return result_text


def parse_recommendations(response_text: str) -> list[dict[str, Any]]:
    """Extract action recommendations from Claude's response.

    Looks for JSON blocks in the response text.
    """
    recommendations = []
    import re

    # Find JSON blocks in markdown code fences or standalone
    json_pattern = re.compile(r'```json\s*\n?(.*?)\n?\s*```', re.DOTALL)
    matches = json_pattern.findall(response_text)

    # Also try to find bare JSON objects
    if not matches:
        bare_pattern = re.compile(r'\{[^{}]*"action"[^{}]*\}')
        matches = bare_pattern.findall(response_text)

    for match in matches:
        try:
            data = json.loads(match.strip())
            if "action" in data:
                recommendations.append(data)
        except json.JSONDecodeError:
            # Try line-by-line for multiple JSON objects
            for line in match.strip().split("\n"):
                line = line.strip()
                if line.startswith("{") and "action" in line:
                    try:
                        data = json.loads(line)
                        if "action" in data:
                            recommendations.append(data)
                    except json.JSONDecodeError:
                        continue

    # Sort by priority descending
    recommendations.sort(key=lambda r: r.get("priority", 0), reverse=True)
    return recommendations
