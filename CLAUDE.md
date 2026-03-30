# TORN AI Agent - Claude Code Instructions

## Project Overview
This is a TORN City (torn.com) AI agent powered by Claude Opus 4.6. It uses the
TORN API v2 to observe game state and Claude's tool-use to make strategic gameplay
decisions.

**Player ID**: 4202918

## Architecture

```
torn_agent/
├── api/           # TORN API v2 client (async, rate-limited)
│   ├── client.py  # TornAPI class with typed methods
│   └── models.py  # Pydantic models for API responses
├── agent/         # Claude-powered AI brain
│   ├── brain.py   # TornAgentBrain - agentic loop with tool use
│   ├── tools.py   # Tool definitions for Claude
│   ├── executor.py # Translates recommendations to actions
│   └── scheduler.py # Recurring agent loop
├── modules/       # Gameplay strategy modules
│   ├── combat.py  # Attack target selection & chains
│   ├── training.py # Gym stat optimization
│   ├── travel.py  # Foreign stock trading
│   ├── market.py  # Item market arbitrage
│   └── faction.py # Faction coordination
├── config/
│   └── settings.py # Pydantic settings from .env
└── cli.py         # Entry point
```

## Key Commands

```bash
# Install
pip install -e ".[dev]"

# Run single cycle (dry run)
torn-agent --once --dry-run -v

# Run continuously
torn-agent --dry-run

# Run live (executes actions)
torn-agent --live

# Tests
pytest tests/ -v

# Lint
ruff check torn_agent/
mypy torn_agent/
```

## How It Works

1. **Scheduler** triggers a cycle every N seconds
2. **Brain** sends game context + tools to Claude Opus 4.6
3. Claude calls observation tools (get_my_status, etc.) → TORN API
4. Claude analyzes state and calls `recommend_action` with decisions
5. **Executor** processes recommendations (dry-run logs or live dispatch)

## TORN API Notes

- API v2 is **read-only** — actual gameplay actions (attacking, training, etc.)
  require browser interaction
- Rate limit: 100 requests/min per user, 1000/min per IP
- Auth: `Authorization: ApiKey <key>` header
- Base URL: `https://api.torn.com/v2`
- Categories: user, faction, company, market, torn, property

## Safety Defaults

- `DRY_RUN=true` — logs decisions without executing
- Attacks, travel, and market trading disabled by default
- Max spend limit per action: $100,000
- All actions logged with reasoning

## Development Notes

- Python 3.11+, async throughout
- Pydantic v2 for all data models
- structlog for structured logging
- httpx for async HTTP
- The agent uses Claude's native tool-use (no LangChain/LlamaIndex)
