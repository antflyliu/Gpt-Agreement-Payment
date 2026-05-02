"""Unified error types for the webui backend.

Preflight modules should raise ``PreflightError`` for **fatal configuration
issues** (missing required fields, incompatible environment) where continuing
the check makes no sense.  Routine check failures (API returned 4xx, Luhn
mismatch, etc.) should still use ``aggregate([CheckResult(status='fail')])``
so the UI can display a partial result grid.

The FastAPI global handler converts ``PreflightError`` to a structured JSON
response with *code*, *message*, and an actionable *hint* for the end-user.
"""


class PreflightError(Exception):
    """Structured preflight check failure.

    Parameters
    ----------
    code:
        Dot-separated error code, e.g. ``"imap.connect_timeout"``.
    msg:
        Technical error description.
    hint:
        Actionable suggestion displayed to the user.
    """

    def __init__(self, code: str, msg: str, hint: str = ""):
        self.code = code
        self.msg = msg
        self.hint = hint
        super().__init__(f"[{code}] {msg}")
