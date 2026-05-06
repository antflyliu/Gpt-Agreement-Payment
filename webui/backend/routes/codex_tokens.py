from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from .. import db
from ..codex_tokens import mask_account_id, mask_email

router = APIRouter(prefix="/api/codex-tokens", tags=["codex-tokens"])


def _filename_for(email: str, token_id: int) -> str:
    digest = hashlib.sha256(f"{email}:{token_id}".encode()).hexdigest()[:10]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"codex-auth-{digest}-{stamp}.json"


@router.get("")
def list_tokens() -> dict[str, object]:
    items = []
    for row in db.get_db().list_codex_auth_tokens():
        email = str(row.get("chatgpt_email") or "")
        account_id = str(row.get("account_id") or "")
        item = dict(row)
        item["has_id_token"] = bool(item.get("has_id_token"))
        item["has_access_token"] = bool(item.get("has_access_token"))
        item["has_refresh_token"] = bool(item.get("has_refresh_token"))
        item["email_masked"] = mask_email(email)
        item["account_id_masked"] = mask_account_id(account_id)
        item.pop("chatgpt_email", None)
        item.pop("account_id", None)
        items.append(item)
    return {"items": items}


@router.get("/{token_id}/export")
def export_token(token_id: int) -> dict[str, str]:
    export = db.get_db().get_codex_auth_export(token_id)
    if export is None:
        raise HTTPException(status_code=404, detail="Codex token not found")
    email = str(export.get("chatgpt_email") or "")
    auth_json = str(export.get("auth_json") or "")
    return {"auth_json": auth_json, "filename": _filename_for(email, token_id)}
