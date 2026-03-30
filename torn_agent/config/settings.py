"""Application settings loaded from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuration for the TORN AI agent.

    All values can be set via environment variables or a .env file.
    """

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # TORN API
    torn_api_key: str
    torn_api_base_url: str = "https://api.torn.com/v2"
    torn_player_id: int = 4202918

    # Anthropic / Claude
    anthropic_api_key: str
    claude_model: str = "claude-opus-4-6"

    # Agent behaviour
    agent_loop_interval_seconds: int = 60
    max_actions_per_loop: int = 5
    energy_threshold: int = 25
    nerve_threshold: int = 5
    happy_threshold: int = 500

    # Safety
    dry_run: bool = True  # When True, log decisions but don't execute
    enable_attacks: bool = False
    enable_travel: bool = False
    enable_market: bool = False
    max_spend_per_action: int = 100_000  # max cash to spend in a single action
