"""Timezone-aware timestamps (UTC in storage; the browser renders local time)."""

from datetime import datetime, timezone


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
