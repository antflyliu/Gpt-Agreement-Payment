"""Disposable HTTP temp-mail provider using the 1secmail API.

Zero-config, no domain needed – ideal for one-off registration flows.
API docs: https://www.1secmail.com/api/
"""
from __future__ import annotations

import logging
import random
import re
import string
import time
from datetime import datetime, timezone

import requests

log = logging.getLogger(__name__)

_API = "https://www.1secmail.com/api/v1/"
_DOMAINS: list[str] = []


def _get_domains() -> list[str]:
    global _DOMAINS
    if not _DOMAINS:
        try:
            resp = requests.get(f"{_API}?action=getDomainList", timeout=10)
            resp.raise_for_status()
            _DOMAINS = resp.json()
        except Exception:
            _DOMAINS = ["1secmail.com", "1secmail.org", "1secmail.net"]
    return _DOMAINS


class HTTPTempMailProvider:
    """Disposable email via 1secmail REST API."""

    def __init__(self) -> None:
        self._login: str | None = None
        self._domain: str | None = None

    def create_mailbox(self) -> str:
        domains = _get_domains()
        self._domain = random.choice(domains)
        self._login = "".join(random.choices(string.ascii_lowercase, k=8)) + \
                      "".join(random.choices(string.digits, k=3))
        addr = f"{self._login}@{self._domain}"
        log.info("Created temp mailbox: %s", addr)
        return addr

    def wait_for_otp(
        self,
        email_addr: str,
        timeout: int = 120,
        issued_after: float | None = None,
    ) -> str:
        login, _, domain = email_addr.partition("@")
        if not domain:
            raise ValueError(f"Invalid email address: {email_addr}")

        start = time.time()
        log.info("Polling 1secmail for OTP -> %s (max %ds)", email_addr, timeout)
        while time.time() - start < timeout:
            try:
                resp = requests.get(
                    _API,
                    params={"action": "getMessages", "login": login, "domain": domain},
                    timeout=15,
                )
                resp.raise_for_status()
                messages = resp.json()
            except Exception as e:
                log.warning("1secmail poll error: %s", e)
                time.sleep(5)
                continue

            for msg in messages:
                msg_id = msg.get("id")
                if not msg_id:
                    continue
                if issued_after is not None:
                    msg_date_str = msg.get("date", "")
                    if msg_date_str:
                        try:
                            msg_ts = datetime.strptime(
                                msg_date_str, "%Y-%m-%d %H:%M:%S"
                            ).replace(tzinfo=timezone.utc).timestamp()
                            if msg_ts < issued_after:
                                continue
                        except ValueError:
                            pass
                try:
                    detail = requests.get(
                        _API,
                        params={
                            "action": "readMessage",
                            "login": login,
                            "domain": domain,
                            "id": msg_id,
                        },
                        timeout=15,
                    ).json()
                except Exception:
                    continue
                body = detail.get("body", "") + " " + detail.get("textBody", "")
                subject = detail.get("subject", "")
                otp = self._extract_otp(f"{subject}\n{body}")
                if otp:
                    log.info("Received OTP: %s", otp)
                    return otp
            time.sleep(5)

        raise TimeoutError(f"OTP timeout ({timeout}s) for {email_addr}")

    @staticmethod
    def _extract_otp(text: str) -> str | None:
        patterns = [
            r"(?:verification\s*code|one[-\s]*time\s*code|code\s*is)[^\d]{0,24}(\d{6})",
            r">\s*(\d{6})\s*<",
        ]
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        candidates = re.findall(r"(?<!\d)(\d{6})(?!\d)", text)
        return candidates[-1] if candidates else None
