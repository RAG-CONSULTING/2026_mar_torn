"""Tests for the stealth / anti-detection module."""

from torn_agent.agent.stealth import (
    HumanBehaviorSimulator,
    StealthProfile,
    humanize_interval,
)


def test_action_delay_is_positive():
    sim = HumanBehaviorSimulator()
    for _ in range(100):
        delay = sim.get_action_delay()
        assert delay >= 1.0, f"Delay too short: {delay}"


def test_action_delay_varies():
    sim = HumanBehaviorSimulator()
    delays = [sim.get_action_delay() for _ in range(50)]
    unique = len(set(round(d, 2) for d in delays))
    assert unique > 10, "Delays should have high variance"


def test_poll_interval_has_jitter():
    sim = HumanBehaviorSimulator()
    base = 60
    intervals = [sim.get_poll_interval(base) for _ in range(50)]
    # Should not all be the same
    unique = len(set(round(i) for i in intervals))
    assert unique > 5, "Poll intervals should vary"
    # Should never be less than 30s (minimum floor)
    assert all(i >= 30 for i in intervals)


def test_reaction_time_in_range():
    sim = HumanBehaviorSimulator()
    for _ in range(100):
        rt = sim.get_reaction_time_ms()
        assert 800 <= rt <= 4500, f"Reaction time out of range: {rt}"


def test_session_break_works():
    sim = HumanBehaviorSimulator()
    sim.start_session()
    # Right after starting, should not need break
    # (probabilistic, but extremely unlikely)
    breaks = sum(1 for _ in range(20) if sim.should_take_break())
    assert breaks < 5, "Should not break immediately after session start"


def test_break_duration_positive():
    sim = HumanBehaviorSimulator()
    for _ in range(20):
        dur = sim.get_break_duration()
        assert dur > 0, "Break duration must be positive"


def test_shuffle_actions_preserves_elements():
    sim = HumanBehaviorSimulator()
    actions = ["a", "b", "c", "d", "e"]
    shuffled = sim.shuffle_actions(actions)
    assert sorted(shuffled) == sorted(actions)
    assert len(shuffled) == len(actions)


def test_shuffle_actions_single_item():
    sim = HumanBehaviorSimulator()
    assert sim.shuffle_actions(["only"]) == ["only"]


def test_shuffle_actions_empty():
    sim = HumanBehaviorSimulator()
    assert sim.shuffle_actions([]) == []


def test_request_batch_size_varies():
    sim = HumanBehaviorSimulator()
    sizes = [sim.get_request_batch_size() for _ in range(50)]
    assert min(sizes) >= 1
    assert max(sizes) <= 8
    assert len(set(sizes)) > 1, "Batch sizes should vary"


def test_humanize_interval_jitter():
    results = [humanize_interval(60) for _ in range(50)]
    assert all(r >= 5.0 for r in results)
    unique = len(set(round(r) for r in results))
    assert unique > 5, "humanize_interval should add jitter"


def test_stealth_profile_deterministic_with_seed():
    p1 = StealthProfile(seed=42)
    p2 = StealthProfile(seed=42)
    assert p1.preferred_play_hours == p2.preferred_play_hours
    assert p1.avg_session_minutes == p2.avg_session_minutes


def test_stealth_profile_varies_without_seed():
    profiles = [StealthProfile() for _ in range(10)]
    sessions = [p.avg_session_minutes for p in profiles]
    # Very unlikely all 10 are identical
    assert len(set(sessions)) > 1


def test_skip_action_rate():
    sim = HumanBehaviorSimulator()
    skips = sum(1 for _ in range(1000) if sim.should_skip_action())
    # Should be roughly 5% (50 ± margin)
    assert 10 < skips < 120, f"Skip rate seems off: {skips}/1000"


def test_decoy_request_rate():
    sim = HumanBehaviorSimulator()
    decoys = sum(1 for _ in range(1000) if sim.should_add_decoy_request())
    # Should be roughly 10% (100 ± margin)
    assert 40 < decoys < 180, f"Decoy rate seems off: {decoys}/1000"
