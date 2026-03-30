"""Tests for the training module."""

from torn_agent.modules.training import TrainingModule


def test_recommend_stat_balanced():
    """With balanced strategy, recommends the stat most behind target ratio."""
    module = TrainingModule(
        strategy="balanced",
        current_stats={
            "strength": 100,
            "defense": 100,
            "speed": 50,  # behind
            "dexterity": 100,
        },
    )
    assert module.recommend_stat() == "speed"


def test_recommend_stat_zero_stats():
    """With no stats, defaults to strength."""
    module = TrainingModule(strategy="balanced")
    assert module.recommend_stat() == "strength"


def test_should_train_full_energy():
    """Should always train when energy is full."""
    module = TrainingModule(strategy="balanced")
    result = module.should_train(energy=100, energy_max=100, happy=500)
    assert result["should_train"] is True
    assert "full" in result["reasoning"].lower()


def test_should_train_no_energy():
    """Should not train when energy is 0."""
    module = TrainingModule(strategy="balanced")
    result = module.should_train(energy=0, energy_max=100, happy=500)
    assert result["should_train"] is False


def test_should_train_happy_bonus():
    """Should note happy bonus when happy is maxed."""
    module = TrainingModule(strategy="balanced")
    result = module.should_train(energy=50, energy_max=100, happy=99999)
    assert result["should_train"] is True
    assert result["happy_bonus_active"] is True


def test_should_train_low_energy():
    """Should not train with very low energy."""
    module = TrainingModule(strategy="balanced")
    result = module.should_train(energy=10, energy_max=100, happy=500)
    assert result["should_train"] is False


def test_update_stats():
    module = TrainingModule(strategy="balanced")
    module.update_stats({"strength": 500, "defense": 300})
    assert module.current_stats["strength"] == 500
    assert module.current_stats["defense"] == 300


def test_strength_main_strategy():
    """Strength-main strategy should heavily favor strength."""
    module = TrainingModule(
        strategy="strength_main",
        current_stats={
            "strength": 100,
            "defense": 100,
            "speed": 100,
            "dexterity": 100,
        },
    )
    # With equal stats, strength_main should recommend strength (50% target)
    assert module.recommend_stat() == "strength"
