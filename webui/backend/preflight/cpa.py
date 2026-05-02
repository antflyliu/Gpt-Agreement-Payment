import logging

import httpx
from pydantic import BaseModel

from ._common import CheckResult, PreflightResult, aggregate

log = logging.getLogger("webui.preflight.cpa")


class CPAInput(BaseModel):
    base_url: str
    admin_key: str


def check(body: dict) -> PreflightResult:
    cfg = CPAInput.model_validate(body)
    try:
        with httpx.Client(timeout=15.0) as c:
            r = c.get(cfg.base_url.rstrip("/") + "/v0/health",
                      headers={"X-Admin-Key": cfg.admin_key})
    except httpx.HTTPError as e:
        return aggregate([CheckResult(name="health", status="fail",
                                      message=str(e))])
    if r.status_code == 200:
        return aggregate([CheckResult(name="health", status="ok",
                                      message="health ok")])
    return aggregate([CheckResult(name="health", status="fail",
                                  message=f"HTTP {r.status_code}",
                                  details=r.text[:1000])])
