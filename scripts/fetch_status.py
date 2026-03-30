#!/usr/bin/env python3
"""Quick script to fetch and display current TORN player status.

Usage:
    python scripts/fetch_status.py
    python scripts/fetch_status.py --full
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

# Add parent dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from torn_agent.api.client import TornAPI, TornAPIError


async def fetch_status(api_key: str, full: bool = False) -> None:
    async with TornAPI(api_key=api_key) as api:
        print("=" * 60)
        print("  TORN Player Status")
        print("=" * 60)

        # Basic profile + bars
        try:
            data = await api.get_user(
                selections="profile,bars,battlestats,cooldowns,money,travel"
            )
            print(f"\n  Name: {data.get('name', 'N/A')}")
            print(f"  Level: {data.get('level', 'N/A')}")
            print(f"  Rank: {data.get('rank', 'N/A')}")
            print(f"  Age: {data.get('age', 'N/A')} days")

            status = data.get("status", {})
            print(f"  Status: {status.get('state', 'N/A')} - {status.get('description', '')}")

            # Bars
            for bar_name in ["life", "energy", "nerve", "happy"]:
                bar = data.get(bar_name, {})
                cur = bar.get("current", 0)
                mx = bar.get("maximum", 0)
                ft = bar.get("fulltime", 0)
                pct = f"{cur/mx*100:.0f}%" if mx > 0 else "N/A"
                ft_str = f" (full in {ft//60}m)" if ft > 0 else ""
                print(f"  {bar_name.capitalize():>8}: {cur}/{mx} ({pct}){ft_str}")

            # Battle stats
            print(f"\n  -- Battle Stats --")
            for stat in ["strength", "defense", "speed", "dexterity"]:
                val = data.get(stat, data.get("strength_info", {}).get(stat, "N/A"))
                if isinstance(val, (int, float)):
                    print(f"  {stat.capitalize():>12}: {val:,.0f}")
                else:
                    print(f"  {stat.capitalize():>12}: {val}")

            # Money
            print(f"\n  Cash on hand: ${data.get('money_onhand', data.get('cayman_bank', 'N/A')):,}")
            print(f"  Points: {data.get('points', 'N/A')}")

            # Cooldowns
            cds = data.get("cooldowns", {})
            print(f"\n  -- Cooldowns --")
            for cd_name in ["drug", "booster", "medical"]:
                cd_val = cds.get(cd_name, 0)
                if cd_val > 0:
                    print(f"  {cd_name.capitalize()}: {cd_val//60}m {cd_val%60}s")
                else:
                    print(f"  {cd_name.capitalize()}: Ready")

        except TornAPIError as e:
            print(f"\n  API Error: {e}")
            return

        if full:
            # Recent attacks
            print(f"\n  -- Recent Attacks --")
            try:
                attacks_data = await api.get_my_attacks()
                attacks = attacks_data.get("attacks", {})
                for atk_id, atk in list(attacks.items())[-10:]:
                    result = atk.get("result", "?")
                    defender = atk.get("defender_id", "?")
                    attacker = atk.get("attacker_id", "?")
                    respect = atk.get("respect", 0)
                    print(f"  #{atk_id}: {attacker} -> {defender} = {result} (respect: {respect:.2f})")
            except TornAPIError as e:
                print(f"  Could not fetch attacks: {e}")

            # Faction
            print(f"\n  -- Faction --")
            try:
                faction_data = await api.get_faction(selections="basic,chain")
                print(f"  Faction: {faction_data.get('name', 'N/A')} [{faction_data.get('tag', '')}]")
                print(f"  Respect: {faction_data.get('respect', 'N/A')}")
                chain = faction_data.get("chain", {})
                print(f"  Chain: {chain.get('current', 0)} (timeout: {chain.get('timeout', 0)}s)")
            except TornAPIError as e:
                print(f"  Could not fetch faction: {e}")

            # Dump raw JSON
            print(f"\n  -- Raw Profile JSON --")
            print(json.dumps(data, indent=2, default=str))

        print("\n" + "=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch TORN player status")
    parser.add_argument("--full", action="store_true", help="Show full details")
    parser.add_argument("--key", type=str, default=None, help="TORN API key (or set TORN_API_KEY env)")
    args = parser.parse_args()

    api_key = args.key or os.environ.get("TORN_API_KEY", "")
    if not api_key:
        print("Error: Provide --key or set TORN_API_KEY environment variable")
        sys.exit(1)

    asyncio.run(fetch_status(api_key, full=args.full))


if __name__ == "__main__":
    main()
