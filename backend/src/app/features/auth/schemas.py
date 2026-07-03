"""Shared schemas across the auth feature slices."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SessionResponse(BaseModel):
    """Body returned when tokens are delivered via Set-Cookie.

    The tokens themselves live in httpOnly cookies; the body only reports when
    they expire so the frontend can schedule a proactive refresh.
    """

    model_config = ConfigDict(frozen=True)

    access_expires_at: datetime
    refresh_expires_at: datetime
