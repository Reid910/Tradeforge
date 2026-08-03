from datetime import datetime, timezone

from app.core.config import settings


def tick_boundary(dt: datetime) -> datetime:
    """Floor a timestamp down to the shared global tick grid. Every producer
    in the game (mines, factory chains) settles against this same grid
    instead of its own private clock, so production stays in lockstep
    rather than drifting out of phase based on when each was created.
    """
    epoch_seconds = dt.timestamp()
    floored = (epoch_seconds // settings.tick_seconds) * settings.tick_seconds
    return datetime.fromtimestamp(floored, tz=timezone.utc)
