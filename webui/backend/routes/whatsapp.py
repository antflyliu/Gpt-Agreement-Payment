"""External OTP endpoint – replaces the deleted WhatsApp relay sidecar.

Android notification forwarder apps (e.g. NotificationForwarder,
NotificationWebhookApp) POST incoming business OTPs here. The runner
picks them up through the same ``_otp_pending`` mechanism that the
legacy wa_relay / gopay modal used.
"""
import logging
import os
import secrets

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from .. import runner

log = logging.getLogger("webui.whatsapp")

router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])

_OTP_TOKEN: str = os.environ.get("WHATSAPP_OTP_TOKEN", "")


def get_or_create_token() -> str:
    """Return the OTP bearer token, generating one on first call."""
    global _OTP_TOKEN
    if not _OTP_TOKEN:
        _OTP_TOKEN = secrets.token_urlsafe(32)
        log.info("Generated new OTP token (store it in your forwarder app)")
    return _OTP_TOKEN


class ExternalOTPRequest(BaseModel):
    otp: str
    source: str = "android-notification-forwarder"
    ts: int | None = None


class ExternalOTPResponse(BaseModel):
    status: str  # "consumed" | "no_pending_request"


@router.post("/external-otp", response_model=ExternalOTPResponse)
def receive_external_otp(
    body: ExternalOTPRequest,
    authorization: str = Header(default=""),
):
    """Accept an OTP pushed from an external notification forwarder."""
    expected = get_or_create_token()
    token = authorization.removeprefix("Bearer ").strip()
    if not token or token != expected:
        raise HTTPException(status_code=401, detail="invalid or missing bearer token")

    otp_value = body.otp.strip()
    if not otp_value:
        raise HTTPException(status_code=422, detail="otp field is empty")

    try:
        runner.submit_otp(otp_value)
        log.info("External OTP consumed: source=%s", body.source)
        return ExternalOTPResponse(status="consumed")
    except RuntimeError:
        log.info("External OTP ignored (no pending request): source=%s", body.source)
        return ExternalOTPResponse(status="no_pending_request")


@router.get("/token")
def show_token():
    """Return the current OTP token (webui settings page uses this)."""
    return {"token": get_or_create_token()}
