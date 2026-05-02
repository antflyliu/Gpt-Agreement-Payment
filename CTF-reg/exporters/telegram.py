"""Telegram bot exporter – send account info via sendMessage."""
from __future__ import annotations

import logging

import requests

from .base import AccountResult, ExportResult

log = logging.getLogger(__name__)

_TG_API = "https://api.telegram.org"


class TelegramExporter:
    name = "telegram"

    def __init__(self, bot_token: str, chat_id: str | int):
        self._token = bot_token
        self._chat_id = str(chat_id)

    def export(self, account: AccountResult) -> ExportResult:
        lines = [
            f"*New Account*",
            f"Email: `{account.email}`",
            f"Status: {account.subscription_status}",
        ]
        if account.team_account_id:
            lines.append(f"Team: `{account.team_account_id}`")
        if account.refresh_token:
            lines.append(f"RT: `{account.refresh_token[:20]}...`")
        text = "\n".join(lines)

        url = f"{_TG_API}/bot{self._token}/sendMessage"
        try:
            resp = requests.post(
                url,
                json={
                    "chat_id": self._chat_id,
                    "text": text,
                    "parse_mode": "Markdown",
                },
                timeout=15,
            )
            resp.raise_for_status()
            log.info("Telegram export ok -> chat_id=%s", self._chat_id)
            return ExportResult(ok=True, message="sent")
        except Exception as e:
            log.error("Telegram export failed: %s", e)
            return ExportResult(ok=False, message=str(e))
