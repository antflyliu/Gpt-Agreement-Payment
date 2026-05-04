import importlib
import sys
from pathlib import Path


def test_otp_issue_window_uses_first_trigger_time(monkeypatch):
    reg_dir = Path(__file__).resolve().parents[1] / "CTF-reg"
    monkeypatch.syspath_prepend(str(reg_dir))
    sys.modules.pop("browser_register", None)
    browser_register = importlib.import_module("browser_register")

    times = iter([1000.0, 1040.0])
    monkeypatch.setattr(browser_register.time, "time", lambda: next(times))

    window = browser_register._OtpIssueWindow()
    window.mark_possible_send()

    assert window.issued_after() == 1000.0


def test_otp_issue_window_updates_for_later_trigger(monkeypatch):
    reg_dir = Path(__file__).resolve().parents[1] / "CTF-reg"
    monkeypatch.syspath_prepend(str(reg_dir))
    sys.modules.pop("browser_register", None)
    browser_register = importlib.import_module("browser_register")

    times = iter([1000.0, 1030.0, 1040.0])
    monkeypatch.setattr(browser_register.time, "time", lambda: next(times))

    window = browser_register._OtpIssueWindow()
    window.mark_possible_send()
    window.mark_possible_send()

    assert window.issued_after() == 1030.0
