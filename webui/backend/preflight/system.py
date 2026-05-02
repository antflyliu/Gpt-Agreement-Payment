import logging
import shutil
import sys

from ..errors import PreflightError
from ._common import CheckResult, PreflightResult, aggregate

log = logging.getLogger("webui.preflight.system")


def check() -> PreflightResult:
    checks: list[CheckResult] = []

    # Python
    if sys.version_info >= (3, 10):
        checks.append(CheckResult(name="python", status="ok",
                                  message=f"Python {sys.version.split()[0]}"))
    else:
        raise PreflightError(
            code="system.python_too_old",
            msg=f"Python {sys.version.split()[0]} < 3.10",
            hint="Upgrade to Python 3.10+.",
        )

    # Binaries
    for binary in ("camoufox", "xvfb-run"):
        path = shutil.which(binary)
        checks.append(CheckResult(
            name=binary,
            status="ok" if path else "fail",
            message=path or f"{binary} not found in PATH",
        ))

    # Playwright import
    try:
        import playwright  # noqa: F401
        checks.append(CheckResult(name="playwright", status="ok",
                                  message="playwright importable"))
    except ImportError as e:
        checks.append(CheckResult(name="playwright", status="fail",
                                  message=str(e)))

    return aggregate(checks)
