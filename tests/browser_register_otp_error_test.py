import importlib
import sys
from pathlib import Path


def _load_browser_register(monkeypatch):
    reg_dir = Path(__file__).resolve().parents[1] / "CTF-reg"
    monkeypatch.syspath_prepend(str(reg_dir))
    sys.modules.pop("browser_register", None)
    return importlib.import_module("browser_register")


def test_text_has_incorrect_otp_matches_openai_message(monkeypatch):
    browser_register = _load_browser_register(monkeypatch)

    assert browser_register._text_has_incorrect_otp("Incorrect code")


def test_text_has_incorrect_otp_ignores_normal_page(monkeypatch):
    browser_register = _load_browser_register(monkeypatch)

    assert not browser_register._text_has_incorrect_otp("Check your inbox")
