import logging

import httpx
from pydantic import BaseModel

from ._common import CheckResult, PreflightResult, aggregate

log = logging.getLogger("webui.preflight.team_system")


class TeamSystemInput(BaseModel):
    base_url: str
    username: str
    password: str


def check(body: dict) -> PreflightResult:
    cfg = TeamSystemInput.model_validate(body)
    try:
        with httpx.Client(timeout=15.0) as c:
            r = c.post(cfg.base_url.rstrip("/") + "/api/user/login",
                       json={"username": cfg.username, "password": cfg.password})
    except httpx.HTTPError as e:
        return aggregate([CheckResult(name="login", status="fail",
                                      message=str(e))])
    try:
        data = r.json()
    except Exception:
        return aggregate([CheckResult(name="login", status="fail",
                                      message=f"non-JSON HTTP {r.status_code}",
                                      details=r.text[:500])])
    if r.status_code == 200 and data.get("success"):
        return aggregate([CheckResult(name="login", status="ok",
                                      message="auth ok")])
    return aggregate([CheckResult(name="login", status="fail",
                                  message=data.get("message") or f"HTTP {r.status_code}",
                                  details=str(data))])
