import importlib.util
from pathlib import Path


def _load_card_module():
    card_path = Path(__file__).resolve().parents[1] / "CTF-pay" / "card.py"
    spec = importlib.util.spec_from_file_location("ctf_pay_card", card_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_paypal_ddc_manual_handoff_defaults_to_visible_browser(monkeypatch):
    card = _load_card_module()

    monkeypatch.delenv("CARD_PAYPAL_DDC_MANUAL_HANDOFF", raising=False)

    assert card._paypal_ddc_manual_handoff_enabled(has_display=True)
    assert not card._paypal_ddc_manual_handoff_enabled(has_display=False)


def test_paypal_ddc_auto_drag_defaults_to_enabled(monkeypatch):
    card = _load_card_module()

    monkeypatch.delenv("CARD_PAYPAL_DDC_AUTO_DRAG", raising=False)
    assert card._paypal_ddc_auto_drag_enabled()

    monkeypatch.setenv("CARD_PAYPAL_DDC_AUTO_DRAG", "0")
    assert not card._paypal_ddc_auto_drag_enabled()


def test_paypal_ddc_continuation_ready_detects_hermes_url():
    card = _load_card_module()
    page = _FakePage(url="https://www.paypal.com/webapps/hermes?token=EC-123")

    assert card._paypal_ddc_continuation_ready(page)


def test_paypal_ddc_continuation_ready_detects_visible_login_input():
    card = _load_card_module()
    page = _FakePage(
        url="https://www.paypal.com/agreements/approve?ba_token=BA-123",
        selectors={"input[name=\"login_email\"]": _FakeElement(visible=True)},
    )

    assert card._paypal_ddc_continuation_ready(page)


class _FakeElement:
    def __init__(self, visible):
        self._visible = visible

    def is_visible(self):
        return self._visible


class _FakePage:
    def __init__(self, url, selectors=None):
        self.url = url
        self._selectors = selectors or {}

    def query_selector(self, selector):
        return self._selectors.get(selector)
