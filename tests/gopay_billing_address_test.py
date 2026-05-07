import importlib.util
from pathlib import Path

import pytest


def _load_card_module():
    card_path = Path(__file__).resolve().parents[1] / "CTF-pay" / "card.py"
    spec = importlib.util.spec_from_file_location(
        "ctf_pay_card_gopay_address", card_path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _FakeResponse:
    status_code = 200
    text = "{}"

    def __init__(self, payload=None):
        self._payload = payload or {}

    def json(self):
        return self._payload


class _RecordingSession:
    def __init__(self, response_payload=None):
        self.headers = {}
        self.posts = []
        self._response_payload = response_payload or {"id": "pm_test"}

    def post(self, url, data=None, headers=None, **kwargs):
        self.posts.append(
            {"url": url, "data": dict(data or {}), "headers": headers, "kwargs": kwargs}
        )
        return _FakeResponse(self._response_payload)


def _base_card():
    return {
        "number": "4242424242424242",
        "name": "Test Buyer",
        "email": "buyer@example.com",
        "address": {
            "line1": "3110 Sunset Boulevard",
            "city": "Los Angeles",
            "state": "CA",
            "postal_code": "90026",
            "country": "US",
        },
    }


def test_prepare_gopay_billing_address_uses_plan_country_and_stores_once(monkeypatch):
    card = _load_card_module()
    payment_card = _base_card()
    calls = []
    dynamic_addr = {
        "line1": "18 Orchard Rd",
        "city": "Singapore",
        "state": "Central",
        "postal_code": "238839",
        "country": "SG",
    }

    def fake_fetch(country):
        calls.append(country)
        return dynamic_addr

    monkeypatch.setattr(card, "_fetch_meiguodizhi_address", fake_fetch)

    resolved = card._prepare_gopay_billing_address(
        payment_card,
        {"fresh_checkout": {"plan": {"billing_country": "sg"}}},
    )

    assert calls == ["SG"]
    assert resolved == dynamic_addr
    assert payment_card["address"] == dynamic_addr


def test_prepare_gopay_billing_address_falls_back_to_static_address_fields(monkeypatch):
    card = _load_card_module()
    payment_card = _base_card()
    calls = []

    def fake_fetch(country):
        calls.append(country)
        return None

    monkeypatch.setattr(card, "_fetch_meiguodizhi_address", fake_fetch)

    resolved = card._prepare_gopay_billing_address(
        payment_card,
        {"fresh_checkout": {"plan": {"billing_country": "uk"}}},
    )

    assert calls == ["UK"]
    assert resolved["line1"] == "3110 Sunset Boulevard"
    assert resolved["city"] == "Los Angeles"
    assert resolved["postal_code"] == "90026"
    assert resolved["country"] == "UK"
    assert payment_card["address"] == resolved


def test_run_prepares_gopay_address_before_address_update(monkeypatch):
    card = _load_card_module()
    dynamic_addr = {
        "line1": "18 Orchard Rd",
        "city": "Singapore",
        "state": "Central",
        "postal_code": "238839",
        "country": "SG",
    }
    calls = []
    seen_addresses = []

    class StopRun(Exception):
        pass

    def fake_fetch(country):
        calls.append(country)
        return dynamic_addr

    def fake_update_payment_page_address(
        _session, _pk, _session_id, payment_card, _ctx, stripe_ver=None
    ):
        seen_addresses.append(dict(payment_card["address"]))
        raise StopRun

    monkeypatch.setattr(
        card,
        "load_config",
        lambda _path: {
            "cards": [_base_card()],
            "captcha": {"api_key": ""},
            "gopay": {
                "country_code": "62",
                "phone_number": "81234567890",
                "pin": "123456",
            },
            "fresh_checkout": {"enabled": True, "plan": {"billing_country": "sg"}},
        },
    )
    monkeypatch.setattr(card.requests, "Session", lambda: _RecordingSession())
    monkeypatch.setattr(
        card, "register_fingerprint", lambda _session: ("guid", "muid", "sid")
    )
    monkeypatch.setattr(
        card,
        "generate_fresh_checkout",
        lambda *_args, **_kwargs: {
            "url": "https://checkout.stripe.com/c/pay/cs_test",
            "processor_entity": "openai_ie",
        },
    )
    monkeypatch.setattr(
        card,
        "parse_checkout_url",
        lambda _value: ("cs_test", "https://checkout.stripe.com/c/pay/cs_test"),
    )
    monkeypatch.setattr(
        card, "fetch_publishable_key", lambda *_args, **_kwargs: "pk_test"
    )
    monkeypatch.setattr(
        card,
        "init_checkout",
        lambda *_args, **_kwargs: (
            {
                "mode": "setup",
                "account_settings": {
                    "display_name": "OpenAI",
                    "account_id": "acct_test",
                },
            },
            card.STRIPE_VERSION_BASE,
            {
                "locale": "en-US",
                "elements_session_id": "ess_test",
                "stripe_js_id": "js_test",
                "config_id": "cfg_test",
            },
        ),
    )
    monkeypatch.setattr(
        card,
        "_extract_checkout_totals",
        lambda _resp: {"due": None, "subtotal": None, "total": None, "currency": "usd"},
    )
    monkeypatch.setattr(card, "fetch_elements_session", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(card, "lookup_consumer", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        card, "update_payment_page_address", fake_update_payment_page_address
    )
    monkeypatch.setattr(card, "_fetch_meiguodizhi_address", fake_fetch)

    with pytest.raises(StopRun):
        card.run("fresh", config_path="unused.json", use_gopay=True, force_fresh=True)

    assert calls == ["SG"]
    assert seen_addresses == [dynamic_addr]


def test_update_and_gopay_payment_method_share_card_address(monkeypatch):
    card = _load_card_module()
    dynamic_addr = {
        "line1": "18 Orchard Rd",
        "city": "Singapore",
        "state": "Central",
        "postal_code": "238839",
        "country": "SG",
    }
    payment_card = _base_card()
    payment_card["address"] = dynamic_addr

    def fail_fetch(_country):
        raise AssertionError(
            "create_gopay_payment_method must not fetch a second address"
        )

    monkeypatch.setattr(card, "_fetch_meiguodizhi_address", fail_fetch)
    monkeypatch.setattr(card.time, "sleep", lambda _seconds: None)

    update_session = _RecordingSession()
    ctx = {
        "elements_session_id": "ess_test",
        "stripe_js_id": "js_test",
        "locale": "en-US",
    }
    card.update_payment_page_address(
        update_session,
        "pk_test",
        "cs_test",
        payment_card,
        ctx,
        stripe_ver=card.STRIPE_VERSION_FULL,
    )

    pm_session = _RecordingSession({"id": "pm_gopay"})
    pm_id = card.create_gopay_payment_method(
        pm_session,
        "pk_test",
        payment_card,
        "cs_test",
        stripe_ver=card.STRIPE_VERSION_BASE,
        ctx=ctx,
    )

    assert pm_id == "pm_gopay"
    last_update = update_session.posts[-1]["data"]
    pm_data = pm_session.posts[0]["data"]
    assert last_update["tax_region[country]"] == dynamic_addr["country"]
    assert last_update["tax_region[line1]"] == dynamic_addr["line1"]
    assert last_update["tax_region[city]"] == dynamic_addr["city"]
    assert last_update["tax_region[state]"] == dynamic_addr["state"]
    assert last_update["tax_region[postal_code]"] == dynamic_addr["postal_code"]
    assert pm_data["billing_details[address][country]"] == dynamic_addr["country"]
    assert pm_data["billing_details[address][line1]"] == dynamic_addr["line1"]
    assert pm_data["billing_details[address][city]"] == dynamic_addr["city"]
    assert pm_data["billing_details[address][state]"] == dynamic_addr["state"]
    assert (
        pm_data["billing_details[address][postal_code]"] == dynamic_addr["postal_code"]
    )


def test_gopay_linking_429_recreates_checkout_with_frozen_address(monkeypatch):
    card = _load_card_module()
    dynamic_addr = {
        "line1": "18 Orchard Rd",
        "city": "Singapore",
        "state": "Central",
        "postal_code": "238839",
        "country": "SG",
    }
    fetch_calls = []
    fresh_urls = []
    updated_addresses = []
    pm_addresses = []
    drive_urls = []
    records = []

    def fake_fetch(country):
        fetch_calls.append(country)
        return dynamic_addr

    def fake_generate_fresh_checkout(*_args, **_kwargs):
        idx = len(fresh_urls) + 1
        url = f"https://checkout.stripe.com/c/pay/cs_retry_{idx}"
        fresh_urls.append(url)
        return {"url": url, "processor_entity": "openai_ie"}

    def fake_parse_checkout_url(value):
        return value.rsplit("/", 1)[-1], value

    def fake_init_checkout(_session, session_id, *_args, **_kwargs):
        return (
            {
                "mode": "setup",
                "account_settings": {
                    "display_name": "OpenAI",
                    "account_id": "acct_test",
                },
            },
            card.STRIPE_VERSION_BASE,
            {
                "locale": "en-US",
                "elements_session_id": f"ess_{session_id}",
                "stripe_js_id": f"js_{session_id}",
                "config_id": f"cfg_{session_id}",
            },
        )

    def fake_update_payment_page_address(
        _session, _pk, _session_id, payment_card, _ctx, stripe_ver=None
    ):
        updated_addresses.append(dict(payment_card["address"]))

    def fake_create_gopay_payment_method(
        _session, _pk, payment_card, session_id, stripe_ver=None, ctx=None
    ):
        pm_addresses.append((session_id, dict(payment_card["address"])))
        return f"pm_{session_id}"

    def fake_confirm_payment(*args, **_kwargs):
        session_id = args[2]
        return {
            "setup_intent": {
                "next_action": {
                    "type": "redirect_to_url",
                    "redirect_to_url": {
                        "url": f"https://pm-redirects.stripe.com/authorize/{session_id}",
                    },
                },
            },
        }

    def fake_drive_gopay_from_redirect(redirect_url, *_args, **_kwargs):
        drive_urls.append(redirect_url)
        if len(drive_urls) == 1:
            raise RuntimeError(
                "midtrans linking 429 exhausted retries after 30 retries body="
            )

    monkeypatch.setattr(
        card,
        "load_config",
        lambda _path: {
            "cards": [_base_card()],
            "captcha": {"api_key": ""},
            "pre_solve_passive_captcha": False,
            "gopay": {
                "country_code": "62",
                "phone_number": "81234567890",
                "pin": "123456",
                "checkout_429_retry_limit": 1,
                "checkout_429_retry_sleep_s": 0,
            },
            "fresh_checkout": {"enabled": True, "plan": {"billing_country": "sg"}},
        },
    )
    monkeypatch.setenv("SKIP_PAY_RT_EXCHANGE", "1")
    monkeypatch.setattr(card.requests, "Session", lambda: _RecordingSession())
    monkeypatch.setattr(
        card, "register_fingerprint", lambda _session: ("guid", "muid", "sid")
    )
    monkeypatch.setattr(card, "generate_fresh_checkout", fake_generate_fresh_checkout)
    monkeypatch.setattr(card, "parse_checkout_url", fake_parse_checkout_url)
    monkeypatch.setattr(
        card, "fetch_publishable_key", lambda *_args, **_kwargs: "pk_test"
    )
    monkeypatch.setattr(card, "init_checkout", fake_init_checkout)
    monkeypatch.setattr(
        card,
        "_extract_checkout_totals",
        lambda _resp: {"due": None, "subtotal": None, "total": None, "currency": "idr"},
    )
    monkeypatch.setattr(card, "fetch_elements_session", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(card, "lookup_consumer", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        card, "update_payment_page_address", fake_update_payment_page_address
    )
    monkeypatch.setattr(card, "_fetch_meiguodizhi_address", fake_fetch)
    monkeypatch.setattr(
        card, "extract_hcaptcha_config", lambda _resp: {"site_key": "site", "rqdata": ""}
    )
    monkeypatch.setattr(
        card,
        "extract_passive_captcha_config",
        lambda *_args, **_kwargs: {"site_key": "passive", "rqdata": ""},
    )
    monkeypatch.setattr(card, "send_telemetry_batch", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        card, "create_gopay_payment_method", fake_create_gopay_payment_method
    )
    monkeypatch.setattr(card, "confirm_payment", fake_confirm_payment)
    monkeypatch.setattr(card, "_drive_gopay_from_redirect", fake_drive_gopay_from_redirect)
    monkeypatch.setattr(
        card,
        "poll_result",
        lambda *_args, **_kwargs: {"state": "succeeded", "return_url": ""},
    )
    monkeypatch.setattr(card, "_record_result", lambda **kwargs: records.append(kwargs))

    result = card.run("fresh", config_path="unused.json", use_gopay=True, force_fresh=True)

    assert result["state"] == "succeeded"
    assert fresh_urls == [
        "https://checkout.stripe.com/c/pay/cs_retry_1",
        "https://checkout.stripe.com/c/pay/cs_retry_2",
    ]
    assert fetch_calls == ["SG"]
    assert updated_addresses == [dynamic_addr, dynamic_addr]
    assert pm_addresses == [
        ("cs_retry_1", dynamic_addr),
        ("cs_retry_2", dynamic_addr),
    ]
    assert drive_urls == [
        "https://pm-redirects.stripe.com/authorize/cs_retry_1",
        "https://pm-redirects.stripe.com/authorize/cs_retry_2",
    ]
    assert len(records) == 1
