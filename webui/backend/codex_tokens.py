from __future__ import annotations

import base64
import json
import time
from datetime import datetime, timezone
from typing import Any


class CodexTokenValidationError(ValueError):
    pass


def _utc_now_iso(now: float | None = None) -> str:
    ts = time.time() if now is None else now
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def decode_jwt_payload(token: str) -> dict[str, Any]:
    parts = str(token or "").split(".")
    if len(parts) < 2:
        return {}
    payload = parts[1]
    padding = "=" * (-len(payload) % 4)
    try:
        raw = base64.urlsafe_b64decode((payload + padding).encode())
        decoded = json.loads(raw.decode())
    except Exception:
        return {}
    return decoded if isinstance(decoded, dict) else {}


def build_cockpit_auth_json(
    *,
    id_token: str,
    access_token: str,
    refresh_token: str,
    last_refresh: str,
) -> str:
    return json.dumps(
        {
            "tokens": {
                "id_token": id_token,
                "access_token": access_token,
                "refresh_token": refresh_token,
            },
            "last_refresh": last_refresh,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def mask_email(email: str) -> str:
    local, sep, domain = (email or "").partition("@")
    if not sep:
        return ""
    if len(local) <= 3:
        masked_local = f"{local[:1]}***"
    else:
        masked_local = f"{local[:1]}***{local[-1:]}"
    return f"{masked_local}@{domain}"


def mask_account_id(account_id: str) -> str:
    value = account_id or ""
    if len(value) <= 8:
        return value
    return f"{value[:4]}…{value[-4:]}"


def normalize_codex_token_response(
    token_response: dict[str, Any],
    *,
    expected_email: str,
    now: float | None = None,
) -> dict[str, Any]:
    id_token = str((token_response or {}).get("id_token") or "")
    access_token = str((token_response or {}).get("access_token") or "")
    refresh_token = str((token_response or {}).get("refresh_token") or "")
    missing = [
        name
        for name, value in (
            ("id_token", id_token),
            ("access_token", access_token),
            ("refresh_token", refresh_token),
        )
        if not value
    ]
    if missing:
        raise CodexTokenValidationError(f"missing required token fields: {', '.join(missing)}")

    payload = decode_jwt_payload(id_token)
    token_email = str(payload.get("email") or "")
    account_id = str(payload.get("sub") or payload.get("account_id") or "")
    expected = (expected_email or "").strip()
    if token_email and expected and token_email.casefold() != expected.casefold():
        raise CodexTokenValidationError("token email mismatch")
    if not token_email and not account_id:
        raise CodexTokenValidationError("token identity missing")

    current = time.time() if now is None else now
    expires_in = (token_response or {}).get("expires_in")
    try:
        expires_at = current + float(expires_in) if expires_in is not None else float(payload.get("exp") or 0)
    except (TypeError, ValueError):
        expires_at = float(payload.get("exp") or 0)

    last_refresh = _utc_now_iso(current)
    auth_json = build_cockpit_auth_json(
        id_token=id_token,
        access_token=access_token,
        refresh_token=refresh_token,
        last_refresh=last_refresh,
    )
    return {
        "chatgpt_email": expected or token_email,
        "account_id": account_id,
        "id_token": id_token,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "scope": str((token_response or {}).get("scope") or ""),
        "token_type": str((token_response or {}).get("token_type") or ""),
        "expires_at": expires_at,
        "last_refresh": last_refresh,
        "auth_json": auth_json,
    }
