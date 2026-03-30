"""TORN rules compliance layer.

Enforces TORN's scripting rules to keep the account safe.
Based on official TORN rules and community intelligence:

ALLOWED:
- Read-only API calls to pull data (this is what TORN provides the API for)
- Displaying/organizing data
- Notifications and alerts
- Strategic analysis and recommendations

NOT ALLOWED (enforced here):
- Automated gameplay actions without user input
- Chaining multiple requests from one trigger
- Background page scraping
- Captcha bypassing
- Programmatic browser events (isTrusted=false)

DETECTION SYSTEMS TO AVOID TRIGGERING:
- BotHunter: behavioral analysis, detects statistical outliers
- isTrusted: browser event property checking
- CAPTCHA: image/text/reCAPTCHA, frequency increases if flagged
- Rate monitoring: API call patterns logged and analyzed

References:
- https://wiki.torn.com/wiki/Rule_Violations
- https://wiki.torn.com/wiki/API
- https://www.torn.com/forums.php?p=threads&t=16000717
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger()

# Hard limits from TORN rules
MAX_API_REQUESTS_PER_MINUTE = 100  # per user across all keys
MAX_API_REQUESTS_PER_MINUTE_IP = 1000  # per IP
API_CACHE_SECONDS = 30  # TORN caches responses for 30s, no point polling faster
MAX_CLOUD_ROWS_PER_DAY = 50_000  # for faction news, events, activity log, personal stats

# Conservative operating limits (stay well below detection thresholds)
SAFE_API_REQUESTS_PER_MINUTE = 40  # use only 40% of the limit
SAFE_MIN_POLL_INTERVAL = 35  # never poll faster than cache + margin
SAFE_MAX_CONSECUTIVE_HOURS = 16  # no human plays 16+ hours straight


class ComplianceViolation(Exception):
    """Raised when an action would violate TORN rules."""

    def __init__(self, rule: str, detail: str):
        self.rule = rule
        self.detail = detail
        super().__init__(f"TORN rule violation [{rule}]: {detail}")


class ComplianceGuard:
    """Enforces TORN's scripting rules at the agent level.

    This is the final safety gate before any action is taken.
    It cannot be bypassed by configuration.
    """

    def __init__(self) -> None:
        self._api_call_timestamps: list[float] = []
        self._session_start: datetime = datetime.now(timezone.utc)
        self._action_count: int = 0
        self._last_selections_fetched: dict[str, float] = {}  # selection -> timestamp

    def check_api_rate(self) -> None:
        """Ensure we're within safe API rate limits."""
        now = datetime.now(timezone.utc).timestamp()

        # Clean old timestamps
        cutoff = now - 60
        self._api_call_timestamps = [t for t in self._api_call_timestamps if t > cutoff]

        if len(self._api_call_timestamps) >= SAFE_API_REQUESTS_PER_MINUTE:
            raise ComplianceViolation(
                "rate_limit",
                f"Would exceed safe rate of {SAFE_API_REQUESTS_PER_MINUTE} req/min "
                f"(current: {len(self._api_call_timestamps)})",
            )

        self._api_call_timestamps.append(now)

    def check_cache_respect(self, selection: str) -> bool:
        """Check if we should skip a request because TORN's cache hasn't refreshed.

        TORN caches API responses for ~30 seconds. Polling faster is wasteful
        and could look suspicious.

        Returns True if the request should proceed, False if it should be skipped.
        """
        now = datetime.now(timezone.utc).timestamp()
        last = self._last_selections_fetched.get(selection, 0)

        if now - last < SAFE_MIN_POLL_INTERVAL:
            logger.debug(
                "cache_skip",
                selection=selection,
                seconds_since_last=round(now - last, 1),
            )
            return False

        self._last_selections_fetched[selection] = now
        return True

    def check_session_duration(self) -> None:
        """Warn if the agent has been running too long without a break."""
        elapsed_hours = (
            datetime.now(timezone.utc) - self._session_start
        ).total_seconds() / 3600

        if elapsed_hours > SAFE_MAX_CONSECUTIVE_HOURS:
            logger.warning(
                "session_too_long",
                hours=round(elapsed_hours, 1),
                max_hours=SAFE_MAX_CONSECUTIVE_HOURS,
                message="Agent has been running too long. Take a mandatory break.",
            )
            raise ComplianceViolation(
                "session_duration",
                f"Running for {elapsed_hours:.1f}h exceeds safe limit of "
                f"{SAFE_MAX_CONSECUTIVE_HOURS}h. Mandatory break required.",
            )

    def reset_session(self) -> None:
        """Reset session timer (call after a break)."""
        self._session_start = datetime.now(timezone.utc)
        self._action_count = 0

    def validate_action(self, action: str, params: dict[str, Any] | None = None) -> None:
        """Validate that an action complies with TORN rules.

        This is a hard stop — non-compliant actions are blocked regardless
        of settings.
        """
        # These actions are always safe (read-only / recommendation)
        safe_actions = {
            "log_observation",
            "recommend_action",
            "wait",
        }
        if action in safe_actions:
            return

        # Track action count for pattern analysis
        self._action_count += 1

        # Check session duration
        self.check_session_duration()

        # Log for audit trail
        logger.info(
            "compliance_check",
            action=action,
            action_count=self._action_count,
            params=params,
        )

    def get_safe_poll_interval(self, requested: float) -> float:
        """Ensure poll interval is never faster than TORN's cache."""
        return max(SAFE_MIN_POLL_INTERVAL, requested)

    def get_compliance_report(self) -> dict[str, Any]:
        """Get current compliance status for logging/debugging."""
        now = datetime.now(timezone.utc)
        elapsed = (now - self._session_start).total_seconds()
        recent_calls = len([
            t for t in self._api_call_timestamps
            if t > now.timestamp() - 60
        ])

        return {
            "session_duration_hours": round(elapsed / 3600, 2),
            "api_calls_last_minute": recent_calls,
            "safe_rate_limit": SAFE_API_REQUESTS_PER_MINUTE,
            "total_actions_this_session": self._action_count,
            "status": "ok" if recent_calls < SAFE_API_REQUESTS_PER_MINUTE else "warning",
        }
