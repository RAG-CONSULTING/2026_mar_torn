# TORN AI Agent

An AI agent powered by **Claude Opus 4.6** that plays [TORN City](https://www.torn.com) — the
text-based online RPG.

The agent uses the TORN API v2 to observe game state and Claude's tool-use capability to make
strategic gameplay decisions about training, combat, crimes, travel, market trading, and faction
coordination.

## Features

- **Claude Opus 4.6 Brain** — uses native tool-use to observe and decide (no LangChain needed)
- **Full TORN API v2 client** — async, rate-limited, typed with Pydantic v2
- **Strategy modules** — combat, gym training, travel arbitrage, market trading, faction chains
- **Safety first** — dry-run mode, spending limits, feature toggles, full action logging
- **Configurable** — all settings via environment variables

## Quick Start

```bash
# Clone and install
git clone https://github.com/rag-consulting/2026_mar_torn.git
cd 2026_mar_torn
pip install -e ".[dev]"

# Configure
cp .env.example .env
# Edit .env with your TORN API key and Anthropic API key

# Run a single cycle in dry-run mode
torn-agent --once --dry-run -v

# Run continuously
torn-agent --dry-run --interval 120
```

## Configuration

| Variable | Default | Description |
|---|---|---|
| `TORN_API_KEY` | (required) | Your TORN API key |
| `ANTHROPIC_API_KEY` | (required) | Your Anthropic API key |
| `TORN_PLAYER_ID` | `4202918` | Your TORN player ID |
| `DRY_RUN` | `true` | Log decisions without executing |
| `ENABLE_ATTACKS` | `false` | Allow attack recommendations |
| `ENABLE_TRAVEL` | `false` | Allow travel recommendations |
| `ENABLE_MARKET` | `false` | Allow market trading |
| `MAX_SPEND_PER_ACTION` | `100000` | Max cash per action |
| `AGENT_LOOP_INTERVAL_SECONDS` | `60` | Seconds between cycles |

## How It Works

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│  Scheduler   │────▶│  Claude Opus 4.6 │────▶│  Executor   │
│  (loop)      │     │  (brain.py)      │     │  (actions)  │
└─────────────┘     └────────┬─────────┘     └─────────────┘
                             │ tool calls
                    ┌────────▼─────────┐
                    │   TORN API v2    │
                    │   (read-only)    │
                    └──────────────────┘
```

Each cycle:
1. **Observe** — Claude calls tools to fetch player status, bars, inventory, faction chain, etc.
2. **Analyze** — Claude reasons about the optimal strategy given current state
3. **Recommend** — Claude calls `recommend_action` with prioritized decisions
4. **Execute** — Actions are logged (dry-run) or dispatched (live mode)

## Strategy

The agent prioritizes:
1. **Stay alive** — heal when low on life, avoid risky situations
2. **Never waste energy** — always train gym when energy is available
3. **Use nerve** — commit crimes for money and stat gains
4. **Maintain chains** — hit targets when faction is chaining
5. **Make money** — market arbitrage and travel trading
6. **Optimize training** — use happy bonus, train weakest stat for build

## Project Structure

```
torn_agent/
├── api/           # TORN API v2 async client
├── agent/         # Claude AI brain, tools, executor, scheduler
├── modules/       # Gameplay strategy (combat, training, travel, market, faction)
├── config/        # Settings from .env
└── cli.py         # Entry point
```

## Development

```bash
# Lint
ruff check torn_agent/

# Type check
mypy torn_agent/

# Test
pytest tests/ -v
```

## License

MIT
