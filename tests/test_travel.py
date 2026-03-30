"""Tests for the travel module."""

from torn_agent.modules.travel import TravelModule


def test_recommend_destination_okay():
    module = TravelModule(cash_available=1_000_000)
    result = module.recommend_destination("Okay", available_time_minutes=300)
    assert result["recommendation"] == "travel"
    assert "destination" in result


def test_recommend_destination_traveling():
    module = TravelModule()
    result = module.recommend_destination("Traveling")
    assert result["recommendation"] == "wait"


def test_recommend_destination_hospital():
    module = TravelModule()
    result = module.recommend_destination("Hospital")
    assert result["recommendation"] == "skip"


def test_recommend_destination_no_time():
    module = TravelModule()
    result = module.recommend_destination("Okay", available_time_minutes=10)
    assert result["recommendation"] == "skip"


def test_is_traveling_true():
    module = TravelModule()
    assert module.is_traveling({"time_left": 120}) is True


def test_is_traveling_false():
    module = TravelModule()
    assert module.is_traveling({"time_left": 0}) is False
