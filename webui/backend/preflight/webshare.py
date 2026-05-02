import logging

import httpx
from pydantic import BaseModel

from ._common import CheckResult, PreflightResult, aggregate

log = logging.getLogger("webui.preflight.webshare")

WS_API = "https://proxy.webshare.io/api/v2"


class WebshareInput(BaseModel):
    api_key: str


def check(body: dict) -> PreflightResult:
    cfg = WebshareInput.model_validate(body)
    headers = {"Authorization": f"Token {cfg.api_key}"}
    try:
        with httpx.Client(timeout=15.0) as c:
            r = c.get(f"{WS_API}/proxy/list/", headers=headers)
    except httpx.HTTPError as e:
        log.error("webshare.connect_error: %s", e)
        return aggregate([CheckResult(name="api", status="fail",
                                      message=str(e))])
    if r.status_code == 200:
        data = r.json()
        return aggregate([CheckResult(name="api", status="ok",
                                      message=f"{data.get('count', '?')} proxies available")])
    log.warning("webshare.api_error: HTTP %d", r.status_code)
    return aggregate([CheckResult(name="api", status="fail",
                                  message=f"HTTP {r.status_code}",
                                  details=r.text[:1000])])
