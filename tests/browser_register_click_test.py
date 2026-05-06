import importlib.util
from pathlib import Path


def _load_browser_register_module():
    path = Path(__file__).resolve().parents[1] / "CTF-reg" / "browser_register.py"
    spec = importlib.util.spec_from_file_location("ctf_reg_browser_register", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _EmailInput:
    def __init__(self):
        self.focused = False
        self.clicked = False
        self.filled = ""
        self.value = ""
        self.ignore_fill = False

    def click(self, timeout=0):
        self.clicked = True
        raise AssertionError("email input should not use mouse click before typing")

    def evaluate(self, script):
        if "value" in script:
            return self.value
        assert "focus" in script
        self.focused = True

    def fill(self, value):
        self.filled = value
        if not self.ignore_fill:
            self.value = value


class _Keyboard:
    def __init__(self):
        self.typed = ""
        self.delays = []

    def type(self, value, delay=0):
        self.typed = value
        self.delays.append(delay)
        if getattr(self, "element", None) is not None:
            self.element.value = value


class _EmailPage:
    def __init__(self, element):
        self.element = element
        self.keyboard = _Keyboard()
        self.keyboard.element = element
        self.queries = []

    def query_selector(self, selector):
        self.queries.append(selector)
        if selector in ('input[type="email"]', 'input[name="email"]'):
            return self.element
        return None


def test_fill_email_input_uses_focus_and_keyboard_type_without_click():
    browser_register = _load_browser_register_module()
    element = _EmailInput()
    page = _EmailPage(element)

    assert browser_register._fill_email_input(page, "fake-user@example.test") is True
    assert element.clicked is False
    assert element.focused is True
    assert page.keyboard.typed == "fake-user@example.test"
    assert page.keyboard.delays and 20 <= page.keyboard.delays[0] <= 60
    assert element.filled == ""
    assert element.value == "fake-user@example.test"


def test_fill_email_input_falls_back_to_fill_when_keyboard_value_mismatch():
    browser_register = _load_browser_register_module()
    element = _EmailInput()
    page = _EmailPage(element)
    page.keyboard.element = None

    assert browser_register._fill_email_input(page, "fake-user@example.test") is True
    assert element.clicked is False
    assert page.keyboard.typed == "fake-user@example.test"
    assert element.filled == "fake-user@example.test"
    assert element.value == "fake-user@example.test"


def test_fill_email_input_falls_back_to_fill_when_keyboard_type_fails():
    browser_register = _load_browser_register_module()
    element = _EmailInput()
    page = _EmailPage(element)

    def fail_type(value, delay=0):
        raise RuntimeError("keyboard unavailable")

    page.keyboard.type = fail_type

    assert browser_register._fill_email_input(page, "fake-user@example.test") is True
    assert element.clicked is False
    assert element.filled == "fake-user@example.test"
    assert element.value == "fake-user@example.test"


def test_fill_email_input_returns_false_when_final_value_still_mismatches():
    browser_register = _load_browser_register_module()
    element = _EmailInput()
    element.ignore_fill = True
    page = _EmailPage(element)
    page.keyboard.element = None

    assert browser_register._fill_email_input(page, "fake-user@example.test") is False
    assert element.clicked is False
    assert element.filled == "fake-user@example.test"
    assert element.value == ""
