"""Tests for CTF-pay/env_placeholder.py and GoPay config placeholders."""
from __future__ import annotations

import json
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DUMMY_PIN_A = "111111"
DUMMY_PIN_B = "222222"
DUMMY_PHONE_WEBUI = "+99 000-0000-0012"
DUMMY_PHONE_FALLBACK = "+99 000-0000-0034"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


env_ph = _load_module("env_placeholder_mod", ROOT / "CTF-pay" / "env_placeholder.py")
gopay = _load_module("gopay_mod", ROOT / "CTF-pay" / "gopay.py")


class _FakeChatGPTSession:
    headers = {}
    proxies = {}


def test_literal_passthrough(monkeypatch):
    monkeypatch.delenv("GOPAY_PIN", raising=False)
    assert env_ph.resolve_placeholder("literal-value", ("GOPAY_PIN",)) == "literal-value"
    assert env_ph.resolve_placeholder("  literal-value  ", ("GOPAY_PIN",)) == "  literal-value  "


def test_placeholder_from_env(monkeypatch):
    monkeypatch.setenv("WEBUI_GOPAY_PIN", DUMMY_PIN_A)
    assert env_ph.resolve_placeholder(
        "YOUR_6_DIGIT_GOPAY_PIN",
        ("WEBUI_GOPAY_PIN", "GOPAY_PIN"),
        label="gopay.pin",
    ) == DUMMY_PIN_A


def test_env_key_order(monkeypatch):
    monkeypatch.setenv("WEBUI_GOPAY_PIN", DUMMY_PIN_A)
    monkeypatch.setenv("GOPAY_PIN", DUMMY_PIN_B)
    assert env_ph.resolve_placeholder(
        "YOUR_6_DIGIT_GOPAY_PIN",
        ("WEBUI_GOPAY_PIN", "GOPAY_PIN"),
    ) == DUMMY_PIN_A
    monkeypatch.delenv("WEBUI_GOPAY_PIN", raising=False)
    assert env_ph.resolve_placeholder(
        "YOUR_6_DIGIT_GOPAY_PIN",
        ("WEBUI_GOPAY_PIN", "GOPAY_PIN"),
    ) == DUMMY_PIN_B


def test_placeholder_missing_env():
    with pytest.raises(env_ph.PlaceholderResolutionError, match="placeholder"):
        env_ph.resolve_placeholder(
            "YOUR_PHONE_NUMBER",
            ("MISSING_KEY_XYZ",),
            label="phone",
        )


def test_empty_raises():
    with pytest.raises(env_ph.PlaceholderResolutionError, match="empty"):
        env_ph.resolve_placeholder("", ("A",), label="x")


def test_is_placeholder():
    assert env_ph.is_placeholder("YOUR_X")
    assert env_ph.is_placeholder("  your_y  ")
    assert not env_ph.is_placeholder("literal-value")
    assert not env_ph.is_placeholder("")


def test_gopay_pin_placeholder_uses_env_and_validates(monkeypatch):
    monkeypatch.setenv("WEBUI_GOPAY_PIN", "123456")
    assert gopay._resolve_gopay_pin("YOUR_6_DIGIT_GOPAY_PIN") == "123456"

    monkeypatch.setenv("WEBUI_GOPAY_PIN", "12345x")
    with pytest.raises(gopay.GoPayError, match="exactly 6 digits"):
        gopay._resolve_gopay_pin("YOUR_6_DIGIT_GOPAY_PIN")


def test_gopay_phone_placeholder_uses_env_and_constructor_strips_digits(monkeypatch):
    monkeypatch.setenv("WEBUI_GOPAY_PHONE", DUMMY_PHONE_WEBUI)
    monkeypatch.setenv("WEBUI_GOPAY_PIN", "123456")

    charger = gopay.GoPayCharger(
        _FakeChatGPTSession(),
        {
            "country_code": "99",
            "phone_number": "YOUR_PHONE_NUMBER",
            "pin": "YOUR_6_DIGIT_GOPAY_PIN",
        },
        otp_provider=lambda: "000000",
    )

    assert charger.phone == "9900000000012"
    assert charger.pin == "123456"


def test_gopay_phone_env_order_and_fallback(monkeypatch):
    monkeypatch.setenv("WEBUI_GOPAY_PHONE", DUMMY_PHONE_WEBUI)
    monkeypatch.setenv("GOPAY_PHONE_NUMBER", DUMMY_PHONE_FALLBACK)
    assert gopay._resolve_gopay_phone("YOUR_PHONE_NUMBER") == DUMMY_PHONE_WEBUI

    monkeypatch.delenv("WEBUI_GOPAY_PHONE", raising=False)
    assert gopay._resolve_gopay_phone("YOUR_PHONE_NUMBER") == DUMMY_PHONE_FALLBACK


def test_gopay_placeholder_env_names_are_supported(monkeypatch):
    monkeypatch.delenv("WEBUI_GOPAY_PHONE", raising=False)
    monkeypatch.delenv("GOPAY_PHONE_NUMBER", raising=False)
    monkeypatch.delenv("WEBUI_GOPAY_PIN", raising=False)
    monkeypatch.delenv("GOPAY_PIN", raising=False)
    monkeypatch.setenv("YOUR_PHONE_NUMBER", DUMMY_PHONE_WEBUI)
    monkeypatch.setenv("YOUR_6_DIGIT_GOPAY_PIN", "123456")

    assert gopay._resolve_gopay_phone("YOUR_PHONE_NUMBER") == DUMMY_PHONE_WEBUI
    assert gopay._resolve_gopay_pin("YOUR_6_DIGIT_GOPAY_PIN") == "123456"


    monkeypatch.setenv("WEBUI_GOPAY_PHONE", "+99 12")
    with pytest.raises(gopay.GoPayError, match="at least 8 digits"):
        gopay._resolve_gopay_phone("YOUR_PHONE_NUMBER")


def test_gopay_runtime_json_and_os_imports(tmp_path, monkeypatch):
    cfg_path = tmp_path / "gopay.json"
    cfg_path.write_text(json.dumps({"gopay": {"pin": "123456"}}), encoding="utf-8")
    assert gopay._load_cfg(str(cfg_path))["gopay"]["pin"] == "123456"

    monkeypatch.setenv("WEBUI_GOPAY_OTP_URL", "http://127.0.0.1:9/otp")
    provider = gopay.build_configured_otp_provider(
        {"otp": {"source": "auto", "timeout": 0.01, "interval": 0.01}},
        fallback_provider=lambda: "000000",
        log=lambda _msg: None,
    )
    assert callable(provider)
