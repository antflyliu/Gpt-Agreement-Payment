"""Generic webhook exporter – POST JSON to a user-configured URL."""
from __future__ import annotations

import dataclasses
import logging

import requests

from .base import AccountResult, ExportResult

log = logging.getLogger(__name__)


class WebhookExporter:
    name = "webhook"

    def __init__(self, url: str, headers: dict[str, str] | None = None, timeout: int = 15):
        self._url = url
        self._headers = {"Content-Type": "application/json", **(headers or {})}
        self._timeout = timeout

    def export(self, account: AccountResult) -> ExportResult:
        payload = dataclasses.asdict(account)
        try:
            resp = requests.post(
                self._url, json=payload,
                headers=self._headers, timeout=self._timeout,
            )
            resp.raise_for_status()
            log.info("Webhook export ok -> %s (%d)", self._url, resp.status_code)
            return ExportResult(ok=True, message=f"HTTP {resp.status_code}")
        except Exception as e:
            log.error("Webhook export failed -> %s: %s", self._url, e)
            return ExportResult(ok=False, message=str(e))
