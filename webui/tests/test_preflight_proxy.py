from unittest.mock import patch

import respx
from httpx import Response


def _login(client):
    client.post("/api/setup", json={"username": "admin", "password": "hunter2hunter2"})
    client.post("/api/login", json={"username": "admin", "password": "hunter2hunter2"})


@respx.mock
@patch("webui.backend.preflight.proxy._port_listening", return_value=True)
def test_proxy_ok_country_match(_mock_port, client):
    _login(client)
    respx.get("https://api.ipify.org").mock(return_value=Response(200, text="1.2.3.4"))
    respx.get("http://ip-api.com/json/1.2.3.4").mock(
        return_value=Response(200, json={"status": "success", "countryCode": "US", "country": "United States"})
    )
    r = client.post("/api/preflight/proxy", json={
        "mode": "manual",
        "url": "socks5://user:pw@127.0.0.1:1080",
        "expected_country": "US",
    })
    assert r.json()["status"] == "ok"


@respx.mock
@patch("webui.backend.preflight.proxy._port_listening", return_value=True)
def test_proxy_country_mismatch(_mock_port, client):
    _login(client)
    respx.get("https://api.ipify.org").mock(return_value=Response(200, text="1.2.3.4"))
    respx.get("http://ip-api.com/json/1.2.3.4").mock(
        return_value=Response(200, json={"status": "success", "countryCode": "DE", "country": "Germany"})
    )
    r = client.post("/api/preflight/proxy", json={
        "mode": "manual",
        "url": "socks5://user:pw@127.0.0.1:1080",
        "expected_country": "US",
    })
    assert r.json()["status"] == "warn"


def test_proxy_mode_none(client):
    _login(client)
    r = client.post("/api/preflight/proxy", json={"mode": "none"})
    assert r.json()["status"] == "ok"
