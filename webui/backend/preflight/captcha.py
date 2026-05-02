import logging

import httpx
from pydantic import BaseModel

from ._common import CheckResult, PreflightResult, aggregate

log = logging.getLogger("webui.preflight.captcha")


class CaptchaInput(BaseModel):
    api_url: str
    client_key: str


def check(body: dict) -> PreflightResult:
    cfg = CaptchaInput.model_validate(body)
    payload = {
        "clientKey": cfg.client_key,
        "task": {
            "type": "FunCaptchaTaskProxyless",
            "websiteURL": "https://example.com",
            "websitePublicKey": "00000000-0000-0000-0000-000000000000",
        },
    }
    try:
        with httpx.Client(timeout=15.0) as c:
            r = c.post(cfg.api_url.rstrip("/") + "/createTask", json=payload)
    except httpx.HTTPError as e:
        log.error("captcha.connect_error: %s", e)
        return aggregate([CheckResult(name="api", status="fail",
                                      message=str(e))])
    try:
        data = r.json()
    except Exception:
        log.error("captcha.non_json_response: HTTP %d", r.status_code)
        return aggregate([CheckResult(name="api", status="fail",
                                      message=f"non-JSON HTTP {r.status_code}",
                                      details=r.text[:1000])])
    if data.get("errorId") == 0 and data.get("taskId"):
        return aggregate([CheckResult(name="api", status="ok",
                                      message=f"taskId {data['taskId']}")])
    log.warning("captcha.createTask_rejected: %s", data.get("errorDescription"))
    return aggregate([CheckResult(name="api", status="fail",
                                  message=data.get("errorDescription") or "createTask rejected",
                                  details=str(data))])
