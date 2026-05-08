"""Demo-mode identity provider.

Hackathon demos use a single local user so the core agent workflow can be
shown without spending MVP time on sign-in screens and Firebase wiring.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.errors import ValidationAppError


DEMO_USER_ID = "demo-user"


@dataclass(frozen=True)
class AuthenticatedUser:
    """Current user identity used by application services."""

    uid: str
    display_name: str
    auth_mode: str


class DemoIdentityProvider:
    """Return a stable single-user identity for hackathon demo mode."""

    def __init__(self, *, uid: str = DEMO_USER_ID, display_name: str = "Demo User") -> None:
        if not uid.strip():
            raise ValidationAppError("demo user uid must not be empty")
        if not display_name.strip():
            raise ValidationAppError("demo user display name must not be empty")
        self._user = AuthenticatedUser(
            uid=uid.strip(),
            display_name=display_name.strip(),
            auth_mode="demo",
        )

    async def current_user(self) -> AuthenticatedUser:
        """Return the current demo user."""

        return self._user
