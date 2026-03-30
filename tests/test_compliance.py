"""Tests for the TORN rules compliance guard."""

from torn_agent.agent.compliance import (
    ComplianceGuard,
    ComplianceViolation,
    SAFE_API_REQUESTS_PER_MINUTE,
    SAFE_MIN_POLL_INTERVAL,
)


def test_api_rate_under_limit():
    guard = ComplianceGuard()
    # Should not raise for a few calls
    for _ in range(10):
        guard.check_api_rate()


def test_api_rate_over_limit():
    guard = ComplianceGuard()
    try:
        for _ in range(SAFE_API_REQUESTS_PER_MINUTE + 5):
            guard.check_api_rate()
        assert False, "Should have raised ComplianceViolation"
    except ComplianceViolation as e:
        assert "rate_limit" in e.rule


def test_cache_respect_first_call():
    guard = ComplianceGuard()
    assert guard.check_cache_respect("profile") is True


def test_cache_respect_repeat_call():
    guard = ComplianceGuard()
    guard.check_cache_respect("bars")
    # Immediate second call should be skipped
    assert guard.check_cache_respect("bars") is False


def test_cache_respect_different_selections():
    guard = ComplianceGuard()
    guard.check_cache_respect("bars")
    # Different selection should be fine
    assert guard.check_cache_respect("profile") is True


def test_validate_safe_actions():
    guard = ComplianceGuard()
    # These should never raise
    guard.validate_action("log_observation")
    guard.validate_action("recommend_action")
    guard.validate_action("wait")


def test_validate_tracks_actions():
    guard = ComplianceGuard()
    guard.validate_action("train_gym")
    guard.validate_action("commit_crime")
    report = guard.get_compliance_report()
    assert report["total_actions_this_session"] == 2


def test_safe_poll_interval_floor():
    guard = ComplianceGuard()
    # Should never go below SAFE_MIN_POLL_INTERVAL
    assert guard.get_safe_poll_interval(10) == SAFE_MIN_POLL_INTERVAL
    assert guard.get_safe_poll_interval(60) == 60
    assert guard.get_safe_poll_interval(SAFE_MIN_POLL_INTERVAL - 1) == SAFE_MIN_POLL_INTERVAL


def test_compliance_report():
    guard = ComplianceGuard()
    guard.validate_action("train_gym")
    report = guard.get_compliance_report()
    assert "session_duration_hours" in report
    assert "api_calls_last_minute" in report
    assert "status" in report
    assert report["status"] == "ok"


def test_reset_session():
    guard = ComplianceGuard()
    guard.validate_action("train_gym")
    guard.validate_action("commit_crime")
    guard.reset_session()
    report = guard.get_compliance_report()
    assert report["total_actions_this_session"] == 0
