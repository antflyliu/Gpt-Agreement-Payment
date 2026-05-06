import json

import pytest
from webui.backend.db import Database


@pytest.fixture
def db(tmp_path):
    return Database(tmp_path / "test.db")


def test_create_and_verify_user(db):
    db.create_user("admin", "secret")
    assert db.verify_user("admin", "secret") is True
    assert db.verify_user("admin", "wrong") is False
    assert db.verify_user("nobody", "secret") is False


def test_user_count_distinguishes_uninitialized(db):
    assert db.user_count() == 0
    db.create_user("admin", "secret")
    assert db.user_count() == 1


def test_session_create_lookup_delete(db):
    db.create_user("admin", "secret")
    sid = db.create_session("admin")
    assert db.lookup_session(sid) == "admin"
    db.delete_session(sid)
    assert db.lookup_session(sid) is None


def test_session_expires(db, monkeypatch):
    import webui.backend.db as db_mod
    db.create_user("admin", "secret")
    times = [1000.0]
    monkeypatch.setattr(db_mod.time, "time", lambda: times[0])
    sid = db.create_session("admin", ttl_s=60)
    times[0] = 1061.0  # past TTL
    assert db.lookup_session(sid) is None


def test_clear_runtime_data_preserves_durable_runtime_config(db):
    db.set_runtime_json("secrets", {"cloudflare": {"api_token": "tok"}})
    db.set_runtime_json("wizard_state", {"current_step": 4, "answers": {}})
    db.set_runtime_json("wa_settings", {"engine": "baileys"})
    db.set_runtime_json("wa_session_snapshot", {"data": "snapshot"})
    db.set_runtime_json("daemon_state", {"old": True})
    db.set_runtime_json("wa_state", {"latest": {"otp": "123456"}})
    db.add_registered_account({"email": "a@example.com", "session_token": "sess"})
    db.add_card_result({"chatgpt_email": "a@example.com", "status": "succeeded"})

    db.clear_runtime_data()

    assert db.iter_registered_accounts() == []
    assert db.iter_card_results() == []
    assert db.get_runtime_json("secrets", {})["cloudflare"]["api_token"] == "tok"
    assert db.get_runtime_json("wizard_state", {})["current_step"] == 4
    assert db.get_runtime_json("wa_settings", {})["engine"] == "baileys"
    assert db.get_runtime_json("wa_session_snapshot", {})["data"] == "snapshot"
    assert db.get_runtime_json("daemon_state", {}) == {}
    assert db.get_runtime_json("wa_state", {}) == {}


def test_codex_auth_tokens_crud(db):
    auth_json = json.dumps(
        {
            "tokens": {
                "id_token": "id_123",
                "access_token": "access_123",
                "refresh_token": "refresh_123",
            },
            "last_refresh": "2026-05-06T00:00:00Z",
        }
    )

    token_id = db.add_codex_auth_token(
        {
            "card_result_id": 7,
            "chatgpt_email": "buyer@example.com",
            "account_id": "acct_123456789",
            "id_token": "id_123",
            "access_token": "access_123",
            "refresh_token": "refresh_123",
            "scope": "openid profile email offline_access api.connectors.read api.connectors.invoke",
            "token_type": "Bearer",
            "expires_at": 1777777777.0,
            "last_refresh": "2026-05-06T00:00:00Z",
            "auth_json": auth_json,
        }
    )

    rows = db.list_codex_auth_tokens()
    assert len(rows) == 1
    assert rows[0]["id"] == token_id
    assert rows[0]["chatgpt_email"] == "buyer@example.com"
    assert rows[0]["account_id"] == "acct_123456789"
    assert rows[0]["has_id_token"] == 1
    assert rows[0]["has_access_token"] == 1
    assert rows[0]["has_refresh_token"] == 1
    assert "id_123" not in rows[0].values()
    assert db.get_codex_auth_json(token_id) == auth_json


def test_clear_runtime_data_removes_codex_tokens(db):
    token_id = db.add_codex_auth_token(
        {
            "card_result_id": None,
            "chatgpt_email": "buyer@example.com",
            "account_id": "acct_123",
            "id_token": "id_123",
            "access_token": "access_123",
            "refresh_token": "refresh_123",
            "scope": "openid",
            "token_type": "Bearer",
            "expires_at": 0,
            "last_refresh": "2026-05-06T00:00:00Z",
            "auth_json": "{}",
        }
    )

    db.clear_runtime_data()

    assert db.get_codex_auth_json(token_id) is None


def test_add_card_result_persists_codex_auth_token(db):
    assert db.add_card_result(
        {
            "ts": "2026-05-06T00:00:00Z",
            "status": "succeeded",
            "chatgpt_email": "buyer@example.com",
            "email": "buyer@example.com",
            "session_id": "sess_123",
            "channel": "gopay",
            "entity": "subscription",
            "config": "{}",
            "error": "",
            "refresh_token": "refresh_123",
            "codex_auth_token": {
                "chatgpt_email": "buyer@example.com",
                "account_id": "acct_123",
                "id_token": "id_123",
                "access_token": "access_123",
                "refresh_token": "refresh_123",
                "scope": "openid profile email offline_access api.connectors.read api.connectors.invoke",
                "token_type": "Bearer",
                "expires_at": 1777777777.0,
                "last_refresh": "2026-05-06T00:00:00Z",
                "auth_json": "{}",
            },
        }
    )

    rows = db.list_codex_auth_tokens()
    assert len(rows) == 1
    assert rows[0]["card_result_id"] == 1
    assert rows[0]["chatgpt_email"] == "buyer@example.com"
