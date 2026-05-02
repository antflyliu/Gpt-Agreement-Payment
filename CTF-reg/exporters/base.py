"""Exporter plugin interface.

Every exporter receives an ``AccountResult`` and pushes it to a
downstream channel. Failures in one exporter must not block others.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class AccountResult:
    """Standard payload passed to every exporter after a successful pipeline."""
    email: str
    password: str = ""
    subscription_status: str = ""
    refresh_token: str = ""
    team_account_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExportResult:
    ok: bool
    message: str = ""


@runtime_checkable
class ExporterProtocol(Protocol):
    """Contract every exporter must satisfy."""

    name: str

    def export(self, account: AccountResult) -> ExportResult:
        """Push *account* to the downstream channel."""
        ...
