"""Anti-detection and human-like behavior simulation.

TORN monitors for bot-like patterns. This module ensures the agent
behaves indistinguishably from a human player by introducing:

- Randomized timing with natural variance
- Circadian rhythm (sleep/wake activity patterns)
- Variable action ordering and occasional "mistakes"
- Session-based play with realistic breaks
- Request pattern obfuscation
"""

from __future__ import annotations

import random
import time
from datetime import datetime, timezone
from enum import Enum

import structlog

logger = structlog.get_logger()

# ── Timing constants ─────────────────────────────────────────────────────────

# Human reaction times follow a log-normal distribution
# Median ~250ms for simple tasks, 500ms-2s for decisions
_REACTION_MIN_MS = 800
_REACTION_MAX_MS = 4500

# Between-action delays (seconds) - humans don't chain actions instantly
_ACTION_GAP_MIN = 3.0
_ACTION_GAP_MAX = 15.0

# Longer "thinking" pauses happen occasionally
_THINK_PAUSE_MIN = 10.0
_THINK_PAUSE_MAX = 45.0
_THINK_PAUSE_PROBABILITY = 0.15  # 15% chance of a longer pause

# Session duration limits
_SESSION_MIN_MINUTES = 8
_SESSION_MAX_MINUTES = 90
_BREAK_MIN_MINUTES = 5
_BREAK_MAX_MINUTES = 120

# API polling jitter (multiplier applied to base interval)
_POLL_JITTER_MIN = 0.6
_POLL_JITTER_MAX = 1.8


class TimeOfDay(Enum):
    """Approximate activity periods based on player timezone."""
    SLEEPING = "sleeping"       # 1am - 7am: very low activity
    WAKING = "waking"           # 7am - 9am: checking in
    MORNING = "morning"         # 9am - 12pm: moderate
    AFTERNOON = "afternoon"     # 12pm - 5pm: moderate-high
    EVENING = "evening"         # 5pm - 10pm: peak activity
    LATE_NIGHT = "late_night"   # 10pm - 1am: tapering off


class StealthProfile:
    """Defines the behavioral fingerprint of a simulated human player.

    Each profile has slightly different habits to avoid all agent instances
    looking identical.
    """

    def __init__(self, timezone_offset_hours: int = -5, seed: int | None = None):
        self._rng = random.Random(seed)
        self.tz_offset = timezone_offset_hours

        # Randomize personal habits (generated once per profile)
        self.preferred_play_hours: tuple[int, int] = (
            self._rng.randint(7, 10),   # wake hour
            self._rng.randint(22, 26) % 24,  # sleep hour
        )
        self.avg_session_minutes = self._rng.randint(15, 60)
        self.check_frequency_bias = self._rng.uniform(0.7, 1.3)  # some players check more
        self.impatience = self._rng.uniform(0.5, 1.5)  # affects action speed
        self.distraction_rate = self._rng.uniform(0.05, 0.20)  # chance of random delay

        logger.info(
            "stealth_profile_created",
            play_hours=self.preferred_play_hours,
            session_avg=self.avg_session_minutes,
            check_bias=round(self.check_frequency_bias, 2),
        )


class HumanBehaviorSimulator:
    """Generates human-like timing and behavior patterns."""

    def __init__(self, profile: StealthProfile | None = None):
        self.profile = profile or StealthProfile()
        self._session_start: float | None = None
        self._session_duration: float = 0
        self._action_count: int = 0
        self._last_action_time: float = 0

    # ── Timing ───────────────────────────────────────────────────────────

    def get_action_delay(self) -> float:
        """Get a human-like delay before the next action (seconds).

        Uses a log-normal distribution which naturally models human
        reaction/decision times - most actions are quick, with an
        occasional long pause.
        """
        # Base delay
        base = random.uniform(_ACTION_GAP_MIN, _ACTION_GAP_MAX)
        base *= self.profile.impatience

        # Occasional "thinking" pause (reading screen, deciding)
        if random.random() < _THINK_PAUSE_PROBABILITY:
            base += random.uniform(_THINK_PAUSE_MIN, _THINK_PAUSE_MAX)
            logger.debug("stealth_think_pause", extra_delay=base)

        # Occasional distraction (phone, alt-tab, etc.)
        if random.random() < self.profile.distraction_rate:
            distraction = random.uniform(15, 180)  # 15s to 3min
            base += distraction
            logger.debug("stealth_distraction", extra_delay=distraction)

        return max(1.0, base)

    def get_poll_interval(self, base_interval: int) -> float:
        """Add jitter to API polling interval.

        Never poll at exact intervals - real humans check at random times.
        """
        jitter = random.uniform(_POLL_JITTER_MIN, _POLL_JITTER_MAX)
        interval = base_interval * jitter * self.profile.check_frequency_bias

        # Time-of-day adjustment: poll less frequently during off-hours
        tod = self._get_time_of_day()
        if tod == TimeOfDay.SLEEPING:
            interval *= random.uniform(3.0, 8.0)  # much less frequent
        elif tod == TimeOfDay.LATE_NIGHT:
            interval *= random.uniform(1.5, 3.0)
        elif tod == TimeOfDay.WAKING:
            interval *= random.uniform(0.8, 1.2)

        return max(30, interval)  # never faster than 30s

    def get_reaction_time_ms(self) -> int:
        """Simulate human reaction time in milliseconds."""
        # Log-normal distribution centered around 1-2 seconds
        mu = 7.0  # ln(~1100ms)
        sigma = 0.5
        reaction = min(
            random.lognormvariate(mu, sigma),
            _REACTION_MAX_MS,
        )
        return max(_REACTION_MIN_MS, int(reaction))

    # ── Session management ───────────────────────────────────────────────

    def start_session(self) -> None:
        """Mark the start of a play session."""
        self._session_start = time.monotonic()
        self._session_duration = random.uniform(
            _SESSION_MIN_MINUTES * 60,
            _SESSION_MAX_MINUTES * 60,
        )
        self._action_count = 0
        logger.info(
            "session_started",
            planned_duration_min=round(self._session_duration / 60, 1),
        )

    def should_take_break(self) -> bool:
        """Check if we should take a break (end session temporarily).

        Real players don't play 24/7. They take breaks to eat, work,
        sleep, etc.
        """
        if self._session_start is None:
            return False

        elapsed = time.monotonic() - self._session_start

        # Hard limit: always break after session duration
        if elapsed >= self._session_duration:
            logger.info("session_break", reason="session_duration_reached")
            return True

        # Soft limit: increasing probability of break as session goes on
        session_pct = elapsed / self._session_duration
        if session_pct > 0.7 and random.random() < (session_pct - 0.7) * 2:
            logger.info("session_break", reason="natural_fatigue")
            return True

        return False

    def get_break_duration(self) -> float:
        """Get how long to take a break (seconds)."""
        tod = self._get_time_of_day()

        if tod == TimeOfDay.SLEEPING:
            # Long sleep break
            hours = random.uniform(4, 8)
            return hours * 3600

        if tod == TimeOfDay.LATE_NIGHT:
            # Might be going to bed
            if random.random() < 0.4:
                return random.uniform(5, 9) * 3600  # sleep
            return random.uniform(
                _BREAK_MIN_MINUTES * 60,
                _BREAK_MAX_MINUTES * 60,
            )

        # Normal break
        return random.uniform(
            _BREAK_MIN_MINUTES * 60,
            _BREAK_MAX_MINUTES * 60,
        )

    def should_be_active(self) -> bool:
        """Check if the player would typically be active right now."""
        tod = self._get_time_of_day()
        activity_probability = {
            TimeOfDay.SLEEPING: 0.02,     # almost never
            TimeOfDay.WAKING: 0.5,        # maybe checking phone
            TimeOfDay.MORNING: 0.6,
            TimeOfDay.AFTERNOON: 0.7,
            TimeOfDay.EVENING: 0.9,       # peak gaming time
            TimeOfDay.LATE_NIGHT: 0.3,
        }
        prob = activity_probability.get(tod, 0.5)
        return random.random() < prob

    # ── Action ordering ──────────────────────────────────────────────────

    def shuffle_actions(self, actions: list) -> list:
        """Slightly shuffle action order to avoid predictable sequences.

        Humans don't always do things in the same order. Sometimes they
        check faction before training, sometimes the reverse.
        """
        if len(actions) <= 1:
            return actions

        # Only shuffle adjacent pairs occasionally (preserves rough priority)
        result = list(actions)
        for i in range(len(result) - 1):
            if random.random() < 0.2:  # 20% chance to swap adjacent
                result[i], result[i + 1] = result[i + 1], result[i]
        return result

    def should_skip_action(self) -> bool:
        """Occasionally skip a non-critical action (like a human would).

        Real players don't always optimize perfectly. Sometimes they
        forget to train or skip checking the market.
        """
        return random.random() < 0.05  # 5% skip rate

    # ── Request pattern obfuscation ──────────────────────────────────────

    def get_request_batch_size(self) -> int:
        """Vary how many API calls we make per cycle.

        Sometimes check everything, sometimes just bars. Like a real
        player who sometimes does a quick check vs a thorough review.
        """
        if random.random() < 0.3:
            return random.randint(1, 2)  # quick check
        elif random.random() < 0.7:
            return random.randint(3, 5)  # normal check
        else:
            return random.randint(5, 8)  # thorough review

    def should_add_decoy_request(self) -> bool:
        """Occasionally make a request that isn't strictly needed.

        Like a player idly browsing the market or checking a random
        player's profile out of curiosity.
        """
        return random.random() < 0.10

    # ── Internal ─────────────────────────────────────────────────────────

    def _get_time_of_day(self) -> TimeOfDay:
        """Get the current time-of-day category in the player's timezone."""
        utc_now = datetime.now(timezone.utc)
        local_hour = (utc_now.hour + self.profile.tz_offset) % 24

        if 1 <= local_hour < 7:
            return TimeOfDay.SLEEPING
        elif 7 <= local_hour < 9:
            return TimeOfDay.WAKING
        elif 9 <= local_hour < 12:
            return TimeOfDay.MORNING
        elif 12 <= local_hour < 17:
            return TimeOfDay.AFTERNOON
        elif 17 <= local_hour < 22:
            return TimeOfDay.EVENING
        else:
            return TimeOfDay.LATE_NIGHT


def humanize_interval(base_seconds: float) -> float:
    """Quick helper: add ±30% jitter to any interval."""
    jitter = random.uniform(0.7, 1.3)
    return max(5.0, base_seconds * jitter)
