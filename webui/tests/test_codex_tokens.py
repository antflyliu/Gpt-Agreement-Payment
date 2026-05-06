import base64
import json
import time

import pytest

from webui.backend.codex_tokens import (
    CodexTokenValidationError,
    build_cockpit_auth_json,
    decode_jwt_payload,
    mask_account_id,
    mask_email,
    normalize_codex_token_response,
)


def _jwt(payload: dict) -> str:
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none"}).encode()).decode().rstrip("=")
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"{header}.{body}.sig"


def test_decode_jwt_payload_extracts_email_and_subject():
    token = _jwt({"email": "Buyer@Example.com", "sub": "acct_123"})

    payload = decode_jwt_payload(token)

    assert payload["email"] == "Buyer@Example.com"
    assert payload["sub"] == "acct_123"


def test_normalize_codex_token_response_builds_auth_json():
    now = time.time()
    token = _jwt({"email": "buyer@example.com", "sub": "acct_123", "exp": int(now) + 3600})

    normalized = normalize_codex_token_response(
        {
            "id_token": token,
            "access_token": "access_abc",
            "refresh_token": "refresh_abc",
            "scope": "openid profile email offline_access api.connectors.read api.connectors.invoke",
            "token_type": "Bearer",
            "expires_in": 3600,
        },
        expected_email="buyer@example.com",
        now=now,
    )

    assert normalized["chatgpt_email"] == "buyer@example.com"
    assert normalized["account_id"] == "acct_123"
    assert normalized["id_token"] == token
    assert normalized["access_token"] == "access_abc"
    assert normalized["refresh_token"] == "refresh_abc"
    assert normalized["expires_at"] == pytest.approx(now + 3600)
    assert normalized["auth_json"] == build_cockpit_auth_json(
        id_token=token,
        access_token="access_abc",
        refresh_token="refresh_abc",
        last_refresh=normalized["last_refresh"],
    )


def test_normalize_rejects_missing_required_tokens():
    with pytest.raises(CodexTokenValidationError, match="missing required token fields"):
        normalize_codex_token_response(
            {"id_token": "id", "access_token": "access"},
            expected_email="buyer@example.com",
            now=1000,
        )


def test_normalize_rejects_email_mismatch():
    token = _jwt({"email": "other@example.com", "sub": "acct_123"})

    with pytest.raises(CodexTokenValidationError, match="token email mismatch"):
        normalize_codex_token_response(
            {
                "id_token": token,
                "access_token": "access_abc",
                "refresh_token": "refresh_abc",
            },
            expected_email="buyer@example.com",
            now=1000,
        )


def test_normalize_allows_missing_email_when_subject_exists():
    token = _jwt({"sub": "acct_123"})

    normalized = normalize_codex_token_response(
        {
            "id_token": token,
            "access_token": "access_abc",
            "refresh_token": "refresh_abc",
        },
        expected_email="buyer@example.com",
        now=1000,
    )

    assert normalized["chatgpt_email"] == "buyer@example.com"
    assert normalized["account_id"] == "acct_123"


def test_masking_helpers_do_not_leak_full_values():
    assert mask_email("buyer@example.com") == "b***r@example.com"
    assert mask_email("ab@example.com") == "a***@example.com"
    assert mask_account_id("acct_123456789") == "acct…6789"
