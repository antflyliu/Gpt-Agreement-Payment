"""Abstract mail provider interface.

All mail providers must implement this protocol so the registration flow
can swap IMAP / HTTP temp mail / Webhook / Gmail transparently.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class MailProviderProtocol(Protocol):
    """Minimal contract every mail provider must satisfy."""

    def create_mailbox(self) -> str:
        """Return a usable email address (existing or freshly generated)."""
        ...

    def wait_for_otp(
        self,
        email_addr: str,
        timeout: int = 120,
        issued_after: float | None = None,
    ) -> str:
        """Block until an OTP code arrives for *email_addr*, then return it.

        Raises ``TimeoutError`` if no OTP is received within *timeout* seconds.
        """
        ...
