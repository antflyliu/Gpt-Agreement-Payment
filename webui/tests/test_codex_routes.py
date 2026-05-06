import json


def test_codex_tokens_list_masks_sensitive_values(client):
    from webui.backend import db

    token_id = db.get_db().add_codex_auth_token(
        {
            "card_result_id": 1,
            "chatgpt_email": "buyer@example.com",
            "account_id": "acct_123456789",
            "id_token": "id_123",
            "access_token": "access_123",
            "refresh_token": "refresh_123",
            "scope": "openid profile email offline_access api.connectors.read api.connectors.invoke",
            "token_type": "Bearer",
            "expires_at": 1777777777.0,
            "last_refresh": "2026-05-06T00:00:00Z",
            "auth_json": "{}",
        }
    )

    response = client.get("/api/codex-tokens")

    assert response.status_code == 200
    data = response.json()
    assert data["items"][0]["id"] == token_id
    assert data["items"][0]["email_masked"] == "b***r@example.com"
    assert data["items"][0]["account_id_masked"] == "acct…6789"
    assert data["items"][0]["has_id_token"] is True
    assert "id_123" not in response.text
    assert "access_123" not in response.text
    assert "refresh_123" not in response.text


def test_codex_token_export_returns_cockpit_auth_json(client):
    from webui.backend import db

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
    token_id = db.get_db().add_codex_auth_token(
        {
            "card_result_id": 1,
            "chatgpt_email": "buyer@example.com",
            "account_id": "acct_123",
            "id_token": "id_123",
            "access_token": "access_123",
            "refresh_token": "refresh_123",
            "scope": "openid",
            "token_type": "Bearer",
            "expires_at": 0,
            "last_refresh": "2026-05-06T00:00:00Z",
            "auth_json": auth_json,
        }
    )

    response = client.get(f"/api/codex-tokens/{token_id}/export")

    assert response.status_code == 200
    assert response.json()["auth_json"] == auth_json
    assert response.json()["filename"].startswith("codex-auth-buyer-example-com-") is False
    assert response.json()["filename"].startswith("codex-auth-") is True
    assert response.json()["filename"].endswith(".json")


def test_codex_token_export_404_for_missing_id(client):
    response = client.get("/api/codex-tokens/999/export")

    assert response.status_code == 404


def test_codex_tokens_list_never_returns_auth_json(client):
    from webui.backend import db

    db.get_db().add_codex_auth_token(
        {
            "card_result_id": 1,
            "chatgpt_email": "buyer@example.com",
            "account_id": "acct_123",
            "id_token": "id_secret",
            "access_token": "access_secret",
            "refresh_token": "refresh_secret",
            "scope": "openid",
            "token_type": "Bearer",
            "expires_at": 0,
            "last_refresh": "2026-05-06T00:00:00Z",
            "auth_json": '{"secret": true}',
        }
    )

    response = client.get("/api/codex-tokens")

    assert response.status_code == 200
    assert "auth_json" not in response.text
    assert "id_secret" not in response.text
    assert "access_secret" not in response.text
    assert "refresh_secret" not in response.text
