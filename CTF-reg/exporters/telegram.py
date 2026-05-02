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

    @staticmethod
    def _esc(text: str) -> str:
        """Escape special chars for Telegram HTML parse_mode."""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def export(self, account: AccountResult) -> ExportResult:
        lines = [
            "<b>New Account</b>",
            f"Email: <code>{self._esc(account.email)}</code>",
            f"Status: {self._esc(account.subscription_status)}",
        ]
        if account.team_account_id:
            lines.append(f"Team: <code>{self._esc(account.team_account_id)}</code>")
        if account.refresh_token:
            lines.append(f"RT: <code>{self._esc(account.refresh_token[:20])}...</code>")
        text = "\n".join(lines)

        url = f"{_TG_API}/bot{self._token}/sendMessage"
        try:
            resp = requests.post(
                url,
                json={
                    "chat_id": self._chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                },
                timeout=15,
            )
            resp.raise_for_status()
            log.info("Telegram export ok -> chat_id=%s", self._chat_id)
            return ExportResult(ok=True, message="sent")
        except Exception as e:
            log.error("Telegram export failed: %s", e)
            return ExportResult(ok=False, message=str(e))
