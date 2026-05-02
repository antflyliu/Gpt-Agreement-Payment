"""Backward-compatible wrapper around the existing ``mail_provider.MailProvider``.

This simply re-exports the original IMAP-based provider under the new
``MailProviderProtocol`` interface so that callers using the new
``CTF-reg/mail/`` package get the same behaviour as before.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure CTF-reg is on sys.path so the legacy module is importable.
_REG_DIR = str(Path(__file__).resolve().parent.parent)
if _REG_DIR not in sys.path:
    sys.path.insert(0, _REG_DIR)

from mail_provider import MailProvider  # noqa: E402  # type: ignore[import-untyped]


class IMAPMailProvider(MailProvider):
    """IMAP mail provider – thin subclass for explicit naming."""
    pass
