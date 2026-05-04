"""WhatsApp Web sidecar control, status, and external OTP ingestion."""
from __future__ import annotations

import logging
import os
import re
import secrets

from fastapi import APIRouter, Header, HTTPException, Response
from pydantic import BaseModel, Field

from ..auth import CurrentUser
from .. import runner, wa_relay

log = logging.getLogger("webui.whatsapp")

router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])

_OTP_PATTERN = re.compile(r"^\d{4,8}$")


class StartRequest(BaseModel):
    mode: str = Field(pattern="^(qr|pairing)$", default="qr")
    phone: str = ""
    engine: str = ""


class SettingsRequest(BaseModel):
    engine: str = ""


class ExternalOTPRequest(BaseModel):
    otp: str
    source: str = "android-notification-forwarder"
    ts: int | None = None


class ExternalOTPResponse(BaseModel):
    status: str  # "consumed" | "no_pending_request"


def get_or_create_token() -> str:
    """Return the bearer token used by external OTP forwarders."""
    env_token = os.environ.get("WHATSAPP_OTP_TOKEN", "").strip()
    if env_token:
        return env_token
    return wa_relay.relay_token()


def _check_relay_token(token: str = "", x_wa_relay_token: str = "") -> None:
    got = token or x_wa_relay_token or ""
    expected = wa_relay.relay_token()
    if not got or not secrets.compare_digest(got, expected):
        raise HTTPException(status_code=403, detail="invalid relay token")


@router.get("/status")
def get_status(user: str = CurrentUser):
    return wa_relay.status()


@router.post("/start")
def start(req: StartRequest, user: str = CurrentUser):
    try:
        return wa_relay.start(mode=req.mode, pairing_phone=req.phone, engine=req.engine)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/settings")
def update_settings(req: SettingsRequest, user: str = CurrentUser):
    try:
        return wa_relay.set_preferred_engine(req.engine)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/stop")
def stop(user: str = CurrentUser):
    return wa_relay.stop()


@router.post("/logout")
def logout(user: str = CurrentUser):
    return wa_relay.logout()


@router.post("/sidecar/state")
def sidecar_state(
    payload: dict,
    token: str = "",
    x_wa_relay_token: str = Header(default=""),
):
    _check_relay_token(token=token, x_wa_relay_token=x_wa_relay_token)
    return {"ok": True, "state": wa_relay.apply_sidecar_state(payload)}


@router.get("/latest-otp")
def latest_otp(
    response: Response,
    since: float = 0.0,
    token: str = "",
    x_wa_relay_token: str = Header(default=""),
):
    _check_relay_token(token=token, x_wa_relay_token=x_wa_relay_token)
    item = wa_relay.latest_otp(since=since)
    if not item:
        response.status_code = 204
        return None
    return item


@router.post("/external-otp", response_model=ExternalOTPResponse)
def receive_external_otp(
    body: ExternalOTPRequest,
    authorization: str = Header(default=""),
):
    """Accept an OTP pushed from an external notification forwarder."""
    expected = get_or_create_token()
    token = authorization.removeprefix("Bearer ").strip()
    if not token or not secrets.compare_digest(token, expected):
        raise HTTPException(status_code=401, detail="invalid or missing bearer token")

    otp_value = body.otp.strip()
    if not otp_value:
        raise HTTPException(status_code=422, detail="otp field is empty")
    if not _OTP_PATTERN.match(otp_value):
        raise HTTPException(status_code=422, detail="otp must be 4-8 digits")

    try:
        runner.submit_otp(otp_value)
        log.info("External OTP consumed: source=%s", body.source)
        return ExternalOTPResponse(status="consumed")
    except RuntimeError:
        log.info("External OTP ignored (no pending request): source=%s", body.source)
        return ExternalOTPResponse(status="no_pending_request")


@router.get("/token")
def show_token(_: str = CurrentUser):
    """Return the current OTP token for forwarder configuration."""
    return {"token": get_or_create_token()}
