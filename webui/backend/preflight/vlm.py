import logging

import httpx
from pydantic import BaseModel

from ._common import CheckResult, PreflightResult, aggregate

log = logging.getLogger("webui.preflight.vlm")


class VLMInput(BaseModel):
    base_url: str
    api_key: str
    model: str


def check(body: dict) -> PreflightResult:
    cfg = VLMInput.model_validate(body)
    headers = {"Authorization": f"Bearer {cfg.api_key}", "Content-Type": "application/json"}
    payload = {
        "model": cfg.model,
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 5,
    }
    try:
        with httpx.Client(timeout=30.0) as c:
            r = c.post(cfg.base_url.rstrip("/") + "/chat/completions",
                       headers=headers, json=payload)
    except httpx.HTTPError as e:
        log.error("vlm.connect_error: %s", e)
        return aggregate([CheckResult(name="api", status="fail",
                                      message=str(e))])
    if r.status_code == 200:
        return aggregate([CheckResult(name="api", status="ok",
                                      message=f"{cfg.model} responded")])
    log.warning("vlm.api_error: HTTP %d", r.status_code)
    return aggregate([CheckResult(name="api", status="fail",
                                  message=f"HTTP {r.status_code}",
                                  details=r.text[:1000])])
