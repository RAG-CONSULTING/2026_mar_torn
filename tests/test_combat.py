"""Tests for the combat module."""

from torn_agent.api.models import AttackTarget
from torn_agent.modules.combat import CombatModule


def _make_target(**kwargs) -> AttackTarget:
    defaults = {
        "player_id": 999,
        "name": "TestPlayer",
        "level": 30,
        "status": "Okay",
        "last_action": "2 minutes ago",
        "faction_id": 0,
        "life_current": 500,
        "life_maximum": 500,
    }
    defaults.update(kwargs)
    return AttackTarget(**defaults)


def test_score_target_okay_status():
    module = CombatModule(api=None, my_level=30)  # type: ignore[arg-type]
    target = _make_target(level=25, status="Okay")
    score = module._score_target(target)
    assert score > 0


def test_score_target_hospital_status():
    module = CombatModule(api=None, my_level=30)  # type: ignore[arg-type]
    target = _make_target(status="Hospital")
    score = module._score_target(target)
    assert score == 0


def test_score_target_jail_status():
    module = CombatModule(api=None, my_level=30)  # type: ignore[arg-type]
    target = _make_target(status="Jail")
    score = module._score_target(target)
    assert score == 0


def test_score_target_much_higher_level():
    module = CombatModule(api=None, my_level=20)  # type: ignore[arg-type]
    target = _make_target(level=50)
    score = module._score_target(target)
    assert score < 30  # should be low


def test_score_target_low_life():
    module = CombatModule(api=None, my_level=30)  # type: ignore[arg-type]
    target = _make_target(life_current=100, life_maximum=500)
    score = module._score_target(target)
    # Low life gives a bonus
    assert score >= 50


def test_score_target_in_faction():
    module = CombatModule(api=None, my_level=30)  # type: ignore[arg-type]
    target_no_fac = _make_target(faction_id=0)
    target_fac = _make_target(faction_id=12345)
    score_no_fac = module._score_target(target_no_fac)
    score_fac = module._score_target(target_fac)
    assert score_no_fac > score_fac  # faction member gets penalty
