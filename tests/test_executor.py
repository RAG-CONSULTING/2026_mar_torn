"""Tests for the action executor."""

from torn_agent.agent.brain import ActionRecommendation
from torn_agent.agent.executor import ActionExecutor
from torn_agent.config.settings import Settings


def _make_settings(**kwargs) -> Settings:
    defaults = {
        "torn_api_key": "test",
        "anthropic_api_key": "test",
        "dry_run": True,
    }
    defaults.update(kwargs)
    return Settings(**defaults)


def test_dry_run_does_not_execute():
    executor = ActionExecutor(settings=_make_settings(dry_run=True))
    recs = [
        ActionRecommendation(action="train_gym", reasoning="test", priority=5),
    ]
    results = executor.execute(recs)
    assert len(results) == 1
    assert results[0].executed is False
    assert "DRY RUN" in results[0].result


def test_attack_blocked_when_disabled():
    executor = ActionExecutor(settings=_make_settings(enable_attacks=False, dry_run=False))
    recs = [
        ActionRecommendation(
            action="attack_target",
            reasoning="test",
            priority=5,
            parameters={"target_id": 123},
        ),
    ]
    results = executor.execute(recs)
    assert results[0].executed is False
    assert "safety" in results[0].result.lower()


def test_travel_blocked_when_disabled():
    executor = ActionExecutor(settings=_make_settings(enable_travel=False, dry_run=False))
    recs = [
        ActionRecommendation(action="travel", reasoning="test", priority=5),
    ]
    results = executor.execute(recs)
    assert results[0].executed is False


def test_market_blocked_when_disabled():
    executor = ActionExecutor(settings=_make_settings(enable_market=False, dry_run=False))
    recs = [
        ActionRecommendation(action="buy_market", reasoning="test", priority=5),
    ]
    results = executor.execute(recs)
    assert results[0].executed is False


def test_max_actions_per_loop():
    executor = ActionExecutor(
        settings=_make_settings(
            dry_run=False,
            max_actions_per_loop=2,
            enable_attacks=True,
        )
    )
    recs = [
        ActionRecommendation(action="train_gym", reasoning="r1", priority=5),
        ActionRecommendation(action="train_gym", reasoning="r2", priority=4),
        ActionRecommendation(action="train_gym", reasoning="r3", priority=3),
    ]
    results = executor.execute(recs)
    executed = [r for r in results if r.executed]
    skipped = [r for r in results if not r.executed]
    assert len(executed) == 2
    assert len(skipped) == 1


def test_spend_limit_blocks():
    executor = ActionExecutor(
        settings=_make_settings(
            dry_run=False,
            enable_market=True,
            max_spend_per_action=50000,
        )
    )
    recs = [
        ActionRecommendation(
            action="buy_market",
            reasoning="expensive",
            priority=5,
            parameters={"cost": 100000},
        ),
    ]
    results = executor.execute(recs)
    assert results[0].executed is False
