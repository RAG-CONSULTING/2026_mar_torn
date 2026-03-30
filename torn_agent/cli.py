"""CLI entry point for the TORN AI agent."""

from __future__ import annotations

import argparse
import asyncio
import sys

import structlog

from torn_agent.config.settings import Settings


def setup_logging(verbose: bool = False) -> None:
    """Configure structured logging."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(colors=True),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            structlog.logging.DEBUG if verbose else structlog.logging.INFO
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="torn-agent",
        description="AI agent powered by Claude Opus 4.6 that plays TORN City",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single cycle then exit (useful for testing)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=None,
        help="Log recommendations without executing actions",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Execute actions (overrides dry_run setting)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help="Override loop interval in seconds",
    )

    args = parser.parse_args()
    setup_logging(verbose=args.verbose)
    logger = structlog.get_logger()

    try:
        settings = Settings()  # type: ignore[call-arg]
    except Exception as e:
        logger.error("config_error", error=str(e))
        print(
            "\nConfiguration error. Make sure you have a .env file with:\n"
            "  TORN_API_KEY=your_torn_api_key\n"
            "  ANTHROPIC_API_KEY=your_anthropic_api_key\n",
            file=sys.stderr,
        )
        sys.exit(1)

    # CLI overrides
    if args.dry_run is True:
        settings.dry_run = True
    elif args.live:
        settings.dry_run = False
    if args.interval:
        settings.agent_loop_interval_seconds = args.interval

    from torn_agent.agent.scheduler import AgentScheduler

    scheduler = AgentScheduler(settings)

    logger.info(
        "torn_agent_starting",
        player_id=settings.torn_player_id,
        model=settings.claude_model,
        dry_run=settings.dry_run,
        mode="single-cycle" if args.once else "continuous",
    )

    if args.once:
        results = asyncio.run(scheduler.run_once())
        for r in results:
            print(f"  [{r['action']}] priority={r['priority']} executed={r['executed']}")
            print(f"    {r['result']}")
    else:
        asyncio.run(scheduler.run())


if __name__ == "__main__":
    main()
