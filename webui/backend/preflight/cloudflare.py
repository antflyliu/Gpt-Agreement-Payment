import logging

import httpx
from pydantic import BaseModel

from ._common import CheckResult, PreflightResult, aggregate

log = logging.getLogger("webui.preflight.cloudflare")

CF = "https://api.cloudflare.com/client/v4"


class CloudflareInput(BaseModel):
    cf_token: str
    zone_names: list[str]


def check(body: dict) -> PreflightResult:
    cfg = CloudflareInput.model_validate(body)
    checks: list[CheckResult] = []
    headers = {"Authorization": f"Bearer {cfg.cf_token}"}

    with httpx.Client(timeout=10.0) as c:
        try:
            r = c.get(f"{CF}/user/tokens/verify", headers=headers)
            data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
            if r.status_code == 200 and data.get("success"):
                checks.append(CheckResult(name="token", status="ok",
                                          message="token active"))
            else:
                msg = "; ".join(e.get("message", "") for e in data.get("errors", [])) or f"HTTP {r.status_code}"
                log.warning("cloudflare.token_invalid: %s", msg)
                checks.append(CheckResult(name="token", status="fail",
                                          message=msg, details=r.text[:1000]))
                return aggregate(checks)
        except httpx.HTTPError as e:
            log.error("cloudflare.connect_error: %s", e)
            checks.append(CheckResult(name="token", status="fail",
                                      message=str(e)))
            return aggregate(checks)

        for zone in cfg.zone_names:
            try:
                r = c.get(f"{CF}/zones", params={"name": zone}, headers=headers)
                data = r.json()
                if r.status_code == 200 and data.get("success") and data.get("result"):
                    checks.append(CheckResult(name=f"zone:{zone}", status="ok",
                                              message=f"zone id {data['result'][0]['id']}"))
                else:
                    log.warning("cloudflare.zone_not_found: %s", zone)
                    checks.append(CheckResult(name=f"zone:{zone}", status="fail",
                                              message="zone not found / no access",
                                              details=r.text[:1000]))
            except httpx.HTTPError as e:
                log.error("cloudflare.zone_check_error: zone=%s err=%s", zone, e)
                checks.append(CheckResult(name=f"zone:{zone}", status="fail",
                                          message=str(e)))
    return aggregate(checks)
