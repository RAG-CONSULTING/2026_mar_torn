"""TORN gameplay knowledge base.

Comprehensive game mechanics and strategy data sourced from:
- Torn Wiki (wiki.torn.com)
- TornStats guides
- Community forum guides (thread #16213798 and others)
- Player-tested strategies (2024-2026 meta)

This module provides the AI agent with expert-level game knowledge
so it can make informed strategic recommendations.
"""

from __future__ import annotations

# ── Gym & Training ───────────────────────────────────────────────────────────

# Specialist gym stat requirements (stat must be 25% higher than comparator)
SPECIALIST_GYMS = {
    "Balboa's Gym": {
        "condition": "(def + dex) 25% higher than (speed + str)",
        "requires": "Cha Cha's unlocked",
        "focus": ["defense", "dexterity"],
    },
    "Frontline Fitness": {
        "condition": "(speed + str) 25% higher than (def + dex)",
        "requires": "Cha Cha's unlocked",
        "focus": ["speed", "strength"],
    },
    "Gym 3000": {
        "condition": "str 25% higher than 2nd highest",
        "requires": "George's unlocked",
        "focus": ["strength"],
    },
    "Mr. Isoyama's": {
        "condition": "def 25% higher than 2nd highest",
        "requires": "George's unlocked",
        "focus": ["defense"],
    },
    "Total Rebound": {
        "condition": "speed 25% higher than 2nd highest",
        "requires": "George's unlocked",
        "focus": ["speed"],
    },
    "Elites": {
        "condition": "dex 25% higher than 2nd highest",
        "requires": "George's unlocked",
        "focus": ["dexterity"],
    },
    "Sports Science Lab": {
        "condition": "Last Round's unlocked, max 50 Xanax + 50 Ecstasy lifetime",
        "requires": "Last Round's unlocked",
        "focus": ["all"],
        "note": "Drug-free gym with superior gains across all stats",
    },
}

# Training ratio strategies (stat name -> target fraction of total stats)
TRAINING_STRATEGIES = {
    "balanced": {
        "description": "Equal distribution. Good for early game.",
        "ratios": {"strength": 0.25, "defense": 0.25, "speed": 0.25, "dexterity": 0.25},
    },
    "hank_str": {
        "description": "Hank's ratio: STR primary, DEF/DEX mid, SPD forgotten",
        "ratios": {"strength": 0.35, "defense": 0.25, "speed": 0.05, "dexterity": 0.35},
    },
    "hank_def": {
        "description": "Hank's ratio: DEF primary, STR/SPD mid, DEX forgotten",
        "ratios": {"defense": 0.35, "strength": 0.25, "speed": 0.35, "dexterity": 0.05},
    },
    "hank_spd": {
        "description": "Hank's ratio: SPD primary, DEF/DEX mid, STR forgotten",
        "ratios": {"speed": 0.35, "defense": 0.25, "strength": 0.05, "dexterity": 0.35},
    },
    "hank_dex": {
        "description": "Hank's ratio: DEX primary, STR/SPD mid, DEF forgotten",
        "ratios": {"dexterity": 0.35, "strength": 0.25, "speed": 0.35, "defense": 0.05},
    },
}

# Gym gain modifiers (multiplicative bonuses)
GAIN_MODIFIERS = {
    "faction_steadfast_primary": 0.20,    # +20% on primary stat
    "faction_steadfast_secondary": 0.15,  # +15% on secondary stat
    "faction_steadfast_tertiary": 0.10,   # +10% on tertiary stat
    "sports_science_bachelor": 0.04,      # +4% total (1% per course)
    "property_pool": 0.02,                # +2% from swimming pool upgrade
    "fitness_center_10star": 0.03,        # +3% from 10-star Fitness Center job
    "strip_club_10star": 0.10,            # +10% dex or def from 10-star Strip Club
    "sports_sneakers": 0.05,              # +5% speed gains from item
}

# Happy bonus thresholds - higher happy = exponentially more gains
# Stop happy jumping at ~700-800k stats (with 10-star Adult Novelties)
# or ~300-400k stats (without)
HAPPY_JUMP_STOP_THRESHOLD_WITH_AN = 800_000
HAPPY_JUMP_STOP_THRESHOLD_WITHOUT = 400_000


# ── Energy Management ────────────────────────────────────────────────────────

ENERGY_SOURCES = {
    "natural_regen": {"amount": 5, "interval_minutes": 15, "max_stored": 150},
    "xanax": {"amount": 250, "cooldown_hours": "6-8", "addiction": 35, "od_chance": 0.03},
    "lsd": {"amount": 50, "cooldown_minutes": "400-450"},
    "energy_drink": {"amount": "10-30", "booster_cooldown_hours": 2},
    "fhc": {"amount": "full_bar", "booster_cooldown_hours": 6},
    "point_refill": {"amount": "full_bar", "cost_points": 25, "daily_limit": 1},
}

# Optimal daily training: ~1,350E/day minimum (3 Xanax + 1 refill)
DAILY_ENERGY_TARGET = 1350

# Max energy at any moment
MAX_ENERGY_CAP = 1000


# ── Crimes ───────────────────────────────────────────────────────────────────

# Natural Nerve Bar (NNB) thresholds - indicates Crime Experience level
NNB_THRESHOLDS = {
    10: "Starting",
    15: "Low CE",
    20: "Moderate CE",
    25: "Good CE",
    30: "High CE",
    35: "Very High CE",
    40: "Expert",
    45: "Master",
    50: "Elite",
    55: "Near-max",
    60: "Maximum (unlocks Political Assassination OC positions 3 & 4)",
}

# Crime progression by NNB level
CRIME_PROGRESSION = [
    {"nnb_range": "10-15", "crimes": "2-nerve Search for Cash, then 3-nerve Selling Illegal Products, then 4-nerve Steal Jacket"},
    {"nnb_range": "15-20", "crimes": "5-nerve Pickpocket (Kid -> Old Woman -> Businessman, 50-100 each)"},
    {"nnb_range": "20+", "crimes": "Scale up based on success rate. If failing >1/3, go back one level."},
]

# Crimes 2.0 rules
CRIMES_2_RULES = {
    "chain_mechanic": "Each success +1 chain. Yellow fail halves chain. Critical fail resets + 20-success debuff.",
    "debuff_clearing": "Use low-nerve crimes (bootlegging, vandalism) to clear debuffs after critical fails.",
    "avoid": "Do NOT do Cracking (5 nerve) - only Brute Forcing (7 nerve). Cracking only produces critical fails.",
}

# Crime success boosters
CRIME_BOOSTERS = {
    "psy3690_bachelor": 0.10,      # +10% from Psychology Bachelor
    "crime_exp_merits": 0.03,      # +3% per merit upgrade (10 levels)
    "crime_enhancer_items": 0.02,  # +2% per equipped crime enhancer (17 items)
}


# ── Travel Trading ───────────────────────────────────────────────────────────

TRAVEL_DESTINATIONS = {
    "Mexico": {
        "flight_minutes": 26,
        "items": ["Flowers", "Plushies", "Alcohol", "Card Skimmer"],
        "tier": "short",
        "note": "Good for active players, multiple items",
    },
    "Cayman Islands": {
        "flight_minutes": 35,
        "items": ["Flowers", "Plushies"],
        "tier": "short",
        "note": "Short flight + offshore bank access",
    },
    "Canada": {
        "flight_minutes": 41,
        "items": ["Flowers", "Plushies", "Xanax"],
        "tier": "short",
        "note": "Short flight, Xanax available",
    },
    "Hawaii": {
        "flight_minutes": 134,
        "items": ["Flowers", "Suitcases"],
        "tier": "medium",
        "note": "Poor - only 1 item type",
    },
    "United Kingdom": {
        "flight_minutes": 159,
        "items": ["Flowers", "2 types of Plushies"],
        "tier": "medium",
        "note": "Medium flight, decent variety",
    },
    "Argentina": {
        "flight_minutes": 167,
        "items": ["Monkey Plushie", "Ceibo Flower", "Tear Gas"],
        "tier": "medium",
        "note": "BEST OVERALL - multiple high-profit items, backup if one OOS",
    },
    "Switzerland": {
        "flight_minutes": 175,
        "items": ["Flash Grenades"],
        "tier": "medium",
        "note": "AVOID for profit - saturated market, <50% $/hr of other destinations",
    },
    "Japan": {
        "flight_minutes": 225,
        "items": ["Flowers", "Xanax", "Alcohol"],
        "tier": "long",
        "note": "Poor - only 1 item, slow restock",
    },
    "China": {
        "flight_minutes": 242,
        "items": ["Flowers", "Plushies", "Ecstasy"],
        "tier": "long",
        "note": "Fortune teller shows level progress (costs $75k)",
    },
    "UAE": {
        "flight_minutes": 242,
        "items": ["Flowers", "Plushies"],
        "tier": "long",
        "note": "Standard long-haul",
    },
    "South Africa": {
        "flight_minutes": 272,
        "items": ["Xanax", "Camel Plushie", "Lion Plushie", "African Violet"],
        "tier": "long",
        "note": "HIGHEST TOTAL PROFIT per full hold. Good for overnight trips.",
    },
}

# Travel capacity
TRAVEL_CAPACITY = {
    "base": 5,
    "airstrip_pilot": 10,
    "faction_excursion": 10,
    "large_suitcase": 4,
    "max_normal": 29,
    "max_tourism_day": 44,  # September 27
    "tourism_day_doubled": 88,
}

# Post-Aug 2024: plushies/flowers trade at Museum for Points, sell Points on market
TRAVEL_SELL_METHOD = "Museum trade for Points -> sell Points on player market"


# ── Attack Mechanics ─────────────────────────────────────────────────────────

ATTACK_COST_ENERGY = 25
ATTACK_COST_VALENTINES = 15  # with Love Juice during Valentine's event

# XP gain by outcome
ATTACK_XP_MULTIPLIERS = {
    "leave": 1.0,           # 100% XP - best for leveling
    "mug": 0.575,           # 55-60% XP + steal cash
    "hospitalize": 0.40,    # 40% XP + longer hospital for target
}

# Critical hit mechanics
CRITICAL_HIT = {
    "base_chance": 0.12,
    "bio2410_anatomy": 0.03,
    "merit_per_level": 0.005,  # up to +5% at 10/10
    "laser_mod": "2-5%",
    "head_throat_heart_multiplier": 3.5,
    "chest_stomach_groin_multiplier": 2.0,
    "other_multiplier": 1.0,
}

# Mugging mechanics
MUGGING = {
    "base_steal_pct": 0.05,   # 5% of target wallet
    "rng_max_pct": 0.10,      # up to 10%
    "masterful_looting_bonus": 0.50,  # +50% base at max merits (7.5-15% range)
    "clothing_store_7star_reduction": 0.75,  # 75% mugging reduction for employees
    "protection_duration_hours": 12,  # mugged players get protection on remaining wallet
}

# Budget weapon recommendations
BUDGET_WEAPONS = {
    "melee": {"name": "Macana", "cost": 100_000, "note": "Nearly as good as Diamond Bladed Knife"},
    "rifle": {"name": "Enfield", "cost": "cheap", "note": "Good starter rifle"},
    "armor_budget": "Leather Armor -> Combat Armor when affordable",
    "armor_legendary": "Riot Helmet + Dune Vest (massive improvement)",
}

WEAPON_BONUSES_PRIORITY = [
    "Stun/Suppress (enemy misses next turn, great with high Dex)",
    "Eviscerate (5min debuff, apply then switch to rifle)",
    "Plunder (best for muggers)",
    "Disarm (removes enemy weapon 12 turns)",
]


# ── Drug Management ──────────────────────────────────────────────────────────

DRUGS = {
    "xanax": {
        "energy": 250,
        "happy": 75,
        "cooldown_hours": "6-8",
        "addiction_points": 35,
        "addiction_with_toleration": 18,
        "od_chance": 0.03,
        "od_effect": "Empty Happy bar + extended cooldown",
        "stat_effect": "Reduces all 4 battle stats temporarily",
    },
    "ecstasy": {
        "effect": "Doubles current Happy",
        "od_chance": 0.05,
        "od_effect": "Empty Happy bar",
        "note": "Use for happy jumping - take AFTER stacking Happy",
    },
    "lsd": {
        "energy": 50,
        "nerve": 0.5,
        "happy": "200-500",
        "cooldown_minutes": "400-450",
        "stat_effect": "+30% Str, +50% Def, -21% Spd/Dex",
    },
}

# Addiction: 20 points removed daily at 3:30 TCT
ADDICTION_DAILY_DECAY = 20
ADDICTION_DECAY_TIME = "03:30 TCT"

# With max Toleration: 8 Xanax/week without rehab
MAX_XANAX_PER_WEEK_TOLERATION = 8

# Sports Science Lab drug limit
SPORTS_SCIENCE_LAB_DRUG_LIMIT = {
    "max_lifetime_xanax": 50,
    "max_lifetime_ecstasy": 50,
}


# ── Education Priorities ─────────────────────────────────────────────────────

EDUCATION_PRIORITY_ORDER = [
    {
        "name": "Education Length Merits",
        "priority": 1,
        "effect": "-2% education time per level (10 levels = -20%)",
        "note": "MAX FIRST. Can be reset after education is complete.",
    },
    {
        "name": "Blood Bags (Biology)",
        "priority": 2,
        "courses": ["Intro to Biochemistry", "Intravenous Therapy"],
        "effect": "Unlocks blood bags for attacking/chaining/missions",
    },
    {
        "name": "Bachelor of Sports Science",
        "priority": 3,
        "effect": "+1% gym gains per course, +4% total at bachelor",
        "note": "Do early - compound benefit over entire career",
    },
    {
        "name": "Principal Job Rank",
        "priority": 4,
        "requirements": "1500 MAN, 5000 INT, 1500 END work stats",
        "effect": "Passive -10% education time (persists after leaving job)",
    },
    {
        "name": "WSU Stock Block",
        "priority": 5,
        "cost": "~$92M",
        "effect": "-10% education time",
    },
    {
        "name": "PSY3690 Psychology Bachelor",
        "priority": 6,
        "effect": "+10% crime success + battle stats + crime skill",
    },
]

# Total education time reduction possible: up to 40%
MAX_EDUCATION_TIME_REDUCTION = 0.40


# ── Merit Priorities ─────────────────────────────────────────────────────────

MERIT_PRIORITY_ORDER = [
    {"name": "Education Length", "levels": 10, "priority": 1, "note": "MAX FIRST, reset after done"},
    {"name": "Bank Interest", "levels": 10, "priority": 2, "note": "+5% per level on investments"},
    {"name": "Life Points", "levels": 10, "priority": 3, "note": "+5% max life per level"},
    {"name": "Critical Hit Rate", "levels": 10, "priority": 4, "note": "+0.5% per level"},
    {"name": "Crime Experience", "levels": 10, "priority": 5, "note": "+3% CE per level"},
    {"name": "Battle Stats (3 of 4)", "levels": 10, "priority": 6, "note": "+3% per level, skip forgotten stat"},
    {"name": "Weapon Mastery (1 type)", "levels": 10, "priority": 7, "note": "+3% dmg+acc per level, ONLY invest in one type"},
    {"name": "Nerve Bar", "levels": 10, "priority": 8, "note": "+1 max nerve per level"},
    {"name": "Hospitalizing", "levels": 10, "priority": 9, "note": "+5% hospital time per level"},
]

# Merit efficiency tip: two stats at 7/10 (56 merits) > one at 10/10 (55 merits)
MERIT_EFFICIENCY_NOTE = "Levels 8-10 cost 8+9+10=27 merits. Better to start a new stat."


# ── Money Making ─────────────────────────────────────────────────────────────

MONEY_METHODS_BY_STAGE = {
    "beginner": [
        "NPC item flipping (Beer at $10 from Bits 'n' Bobs, 100/day limit)",
        "Starter jobs - grocer max rank for energy drink cans (~$2M each)",
        "Work in player-run Sweet Shop for free cans",
        "Crimes: direct cash + sellable items",
    ],
    "mid_level_15plus": [
        "Travel trading (Flower/Plushie runs): $3-6M/day",
        "Mugging gamblers with Masterful Looting merits",
        "Mercenary work: $2.5-6M per hospitalization contract",
        "Faction OC 2.0 payouts",
    ],
    "advanced_high_capital": [
        "City Bank: $2B deposit for 3 months = ~$378M profit ($4M/day)",
        "Stock benefits: SYM 500K shares = drug pack/week (~$4M/day)",
        "Landlording: maxed PIs (~$1.6B), rent 700k+/day each",
        "Reviving (requires Bio education, 200+ days setup)",
        "NPC looting (Duke, Fernando)",
    ],
}

# Daily cost target for optimal play
DAILY_COST_OPTIMAL = {
    "pi_rent": 1_000_000,
    "xanax_3x": 2_700_000,
    "energy_refill": 1_300_000,
    "total": 5_000_000,
}


# ── Property Progression ─────────────────────────────────────────────────────

PROPERTY_PROGRESSION = {
    "private_island_base": 500_000_000,
    "airstrip": 75_000_000,
    "superior_interior": 250_000_000,  # +1000 Happy
    "yacht": 895_000_000,              # +500 Happy
    "medical_facility": 17_000_000,    # +1% life regen
    "total_maxed": 1_770_000_000,
    "upgrades_max": 4,  # pick 4: airstrip, medical, shooting range (+2% dmg), pool (+2% gym)
}

PROPERTY_DISCOUNTS = {
    "law_education": 0.05,  # -5% from Law of Property course
    "elbt_stock": 0.10,     # -10% from ELBT stock benefit
}


# ── Stock Market Priorities ──────────────────────────────────────────────────

STOCK_PRIORITY_ORDER = [
    "City Bank 2B deposit first (guaranteed returns)",
    "GRN + TCT (cheap blocks, decent payout, build capital)",
    "SYM 500K shares (drug pack weekly ~$4M/day)",
    "FHG (good payout scaling)",
    "IOU then MUN ($2B+ needed)",
]

STOCK_PASSIVE_MUST_HAVE = {
    "WSU": {"effect": "-10% education time", "cost": "~$92M"},
    "TSB": {"effect": "Boost bank investment returns", "cost": "varies"},
    "ELBT": {"effect": "-10% property costs", "cost": "varies"},
}


# ── Faction Specials ─────────────────────────────────────────────────────────

FACTION_BRANCHES = {
    "steadfast": {
        "effect": "Up to 20/15/10% gym gains on different stats",
        "priority": "HIGH - directly increases training speed",
    },
    "toleration": {
        "effect": "-50% drug addiction, -30% overdose, -30% side effects",
        "priority": "HIGH - essential for Xanax usage",
        "cost": "254,884 respect total",
    },
    "criminality": {
        "effect": "+25% crime skill/exp, -30% jail time, +40 max nerve",
        "priority": "MEDIUM - good for crime-focused players",
    },
    "fortitude": {
        "effect": "-25% hospital time, +4% life regen, revive cost down to 25E",
        "priority": "MEDIUM - good for combat-focused players",
    },
    "excursion": {
        "effect": "Travel cost reduction, +capacity, +hunting income, +offshore bank interest",
        "priority": "MEDIUM - good for travel traders",
    },
    "voracity": {
        "effect": "Energy can bonuses (Cans 10 = +50% energy from cans)",
        "priority": "MEDIUM - stacks with energy drink books",
    },
}


# ── Key Company Jobs ─────────────────────────────────────────────────────────

NOTABLE_COMPANY_JOBS = {
    "sweet_shop": "Free energy drink cans",
    "adult_novelties_10star": "Used for happy jumping",
    "fitness_center_10star": "+3% gym gains",
    "strip_club_10star": "+10% dex or def",
    "lingerie_store_7star": "Waives ALL property upkeep/staff costs",
    "nightclub_7star": "-50% overdose chance",
    "restaurant_10star": "-25% consumable cooldown",
    "grocery_3star": "-10% consumable cooldown",
    "clothing_store_7star": "75% mugging reduction for employees",
}


# ── Leveling ─────────────────────────────────────────────────────────────────

LEVEL_MILESTONES = {
    15: "Unlocks TRAVEL (critical for income)",
}

LEVELING_STRATEGY = (
    "Attack leveling targets and LEAVE them (100% XP). "
    "Mugging = 55-60% XP. Hospitalizing = only 40% XP. "
    "Use Baldr's Targets (oran.pw/baldrstargets/) or torn-levelling-targets.pages.dev"
)
