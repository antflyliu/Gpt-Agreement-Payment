import json

from webui.backend.db import get_db


def _login(client):
    client.post("/api/setup", json={"username": "admin", "password": "hunter2hunter2"})
    client.post("/api/login", json={"username": "admin", "password": "hunter2hunter2"})


def test_wizard_state_requires_auth(client):
    r = client.get("/api/wizard/state")
    assert r.status_code == 401


def test_wizard_state_initially_empty(client):
    _login(client)
    r = client.get("/api/wizard/state")
    assert r.status_code == 200
    assert r.json() == {"current_step": 1, "answers": {}}


def test_wizard_state_persists(client):
    _login(client)
    payload = {"current_step": 3, "answers": {"cloudflare": {"cf_token": "x"}}}
    r = client.post("/api/wizard/state", json=payload)
    assert r.status_code == 200

    r = client.get("/api/wizard/state")
    assert r.json() == payload


def test_wizard_state_removes_gopay_credentials(client):
    _login(client)
    payload = {
        "current_step": 14,
        "answers": {
            "payment": {"method": "gopay"},
            "gopay": {
                "country_code": "86",
                "phone_number": "FAKE_OLD_GOPAY_PHONE",
                "pin": "FAKE_OLD_GOPAY_PIN",
                "otp_timeout": 300,
            },
        },
    }
    r = client.post("/api/wizard/state", json=payload)
    assert r.status_code == 200

    r = client.get("/api/wizard/state")
    body = r.json()
    assert body["answers"]["gopay"] == {
        "country_code": "86",
        "phone_number": "YOUR_PHONE_NUMBER",
        "pin": "YOUR_6_DIGIT_GOPAY_PIN",
        "otp_timeout": 300,
    }


def test_wizard_state_read_scrubs_legacy_gopay_credentials_at_rest(client):
    _login(client)
    legacy = {
        "current_step": 14,
        "answers": {
            "payment": {"method": "gopay"},
            "gopay": {
                "country_code": "86",
                "phone_number": "FAKE_OLD_GOPAY_PHONE",
                "pin": "FAKE_OLD_GOPAY_PIN",
                "otp_timeout": 300,
            },
        },
    }
    get_db().set_runtime_json("wizard_state", legacy)

    r = client.get("/api/wizard/state")
    assert r.status_code == 200
    body = r.json()
    assert body["answers"]["gopay"] == {
        "country_code": "86",
        "phone_number": "YOUR_PHONE_NUMBER",
        "pin": "YOUR_6_DIGIT_GOPAY_PIN",
        "otp_timeout": 300,
    }

    stored_config = get_db().get_runtime_json("wizard_state", {})
    assert stored_config["answers"]["gopay"]["phone_number"] == "YOUR_PHONE_NUMBER"
    assert stored_config["answers"]["gopay"]["pin"] == "YOUR_6_DIGIT_GOPAY_PIN"
    stored = json.dumps(stored_config, ensure_ascii=False)
    assert "FAKE_OLD_GOPAY_PHONE" not in stored
    assert "FAKE_OLD_GOPAY_PIN" not in stored


def test_wizard_state_partial_update(client):
    _login(client)
    client.post("/api/wizard/state", json={"current_step": 3, "answers": {"a": 1}})
    client.post("/api/wizard/state", json={"current_step": 4, "answers": {"b": 2}})
    r = client.get("/api/wizard/state")
    body = r.json()
    assert body["current_step"] == 4
    assert body["answers"] == {"b": 2}  # full replace, not merge
