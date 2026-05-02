"""Unified error types for the webui backend.

Every preflight module should raise ``PreflightError`` instead of bare
``RuntimeError`` / returning ad-hoc dicts.  The FastAPI global handler
converts it to a structured JSON response with *code*, *message*, and
an actionable *hint* for the end-user.
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
