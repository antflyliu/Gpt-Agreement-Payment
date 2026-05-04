"""Camoufox launch helpers shared by CTF-reg and CTF-pay."""

from __future__ import annotations

import os
from typing import Any


LogSink = Any

_DISABLED = {"0", "false", "no", "off", "disable", "disabled"}
_ENABLED = {"1", "true", "yes", "on", "enable", "enabled", "auto"}


def _warn(log: LogSink | None, message: str) -> None:
    if log is None:
        return
    warning = getattr(log, "warning", None)
    if callable(warning):
        warning(message)
        return
    if callable(log):
        log(message)


def _mmdb_is_usable(log: LogSink | None) -> bool:
    try:
        from camoufox.locale import MMDB_FILE
    except Exception as exc:
        _warn(log, f"[camoufox] GeoIP unavailable; launching with geoip=False: {exc}")
        return False

    if not MMDB_FILE.exists():
        return True

    try:
        import maxminddb

        reader = maxminddb.open_database(str(MMDB_FILE))
        try:
            reader.metadata()
        finally:
            close = getattr(reader, "close", None)
            if callable(close):
                close()
        return True
    except Exception as exc:
        _warn(
            log,
            "[camoufox] GeoIP database is invalid; launching with geoip=False "
            f"({MMDB_FILE}: {exc})",
        )
        return False


def resolve_camoufox_geoip(log: LogSink | None = None) -> bool | str:
    """Return a safe value for Camoufox's geoip launch option.

    The project normally wants Camoufox geolocation spoofing. Some installs leave
    a corrupt GeoLite2-City.mmdb in site-packages; Camoufox only downloads the DB
    when it is missing, so a corrupt existing file aborts browser startup. In
    auto mode we keep geoip enabled only when the MMDB can be opened.
    """
    override = (os.getenv("CTF_CAMOUFOX_GEOIP") or "").strip()
    if override:
        lowered = override.lower()
        if lowered in _DISABLED:
            return False
        if lowered not in _ENABLED:
            return override if _mmdb_is_usable(log) else False

    return True if _mmdb_is_usable(log) else False
