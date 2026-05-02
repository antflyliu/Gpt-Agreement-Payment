import datetime
import logging

from pydantic import BaseModel

from ._common import CheckResult, PreflightResult, aggregate

log = logging.getLogger("webui.preflight.card")

# Heuristic country↔currency map; warn-only on mismatch
COUNTRY_CURRENCY = {
    "US": "USD", "GB": "GBP", "DE": "EUR", "FR": "EUR", "IE": "EUR",
    "NL": "EUR", "ES": "EUR", "IT": "EUR", "PT": "EUR", "AT": "EUR",
    "JP": "JPY", "AU": "AUD", "CA": "CAD", "CH": "CHF", "SG": "SGD",
}


class CardInput(BaseModel):
    number: str
    cvc: str
    exp_month: str
    exp_year: str
    country: str
    currency: str


def _luhn(num: str) -> bool:
    digits = [int(c) for c in num if c.isdigit()]
    if len(digits) < 12:
        return False
    s = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        s += d
    return s % 10 == 0


def check(body: dict) -> PreflightResult:
    cfg = CardInput.model_validate(body)
    checks: list[CheckResult] = []

    if _luhn(cfg.number):
        checks.append(CheckResult(name="luhn", status="ok",
                                  message=f"valid (last4 {cfg.number[-4:]})"))
    else:
        log.warning("card.luhn_fail: last4=%s", cfg.number[-4:])
        checks.append(CheckResult(name="luhn", status="fail",
                                  message="card number fails Luhn"))

    try:
        m, y = int(cfg.exp_month), int(cfg.exp_year)
    except ValueError:
        checks.append(CheckResult(name="exp", status="fail",
                                  message="exp_month / exp_year must be numeric"))
    else:
        if not (1 <= m <= 12):
            checks.append(CheckResult(name="exp", status="fail",
                                      message=f"exp_month {m} out of range"))
        else:
            now = datetime.date.today()
            exp_year = y + 2000 if y < 100 else y
            last_day = (datetime.date(exp_year + (m == 12), (m % 12) + 1, 1)
                        - datetime.timedelta(days=1))
            if last_day < now:
                log.warning("card.expired: %02d/%d", m, exp_year)
                checks.append(CheckResult(name="exp", status="fail",
                                          message=f"expired {m:02d}/{exp_year}"))
            else:
                checks.append(CheckResult(name="exp", status="ok",
                                          message=f"{m:02d}/{exp_year}"))

    expected = COUNTRY_CURRENCY.get(cfg.country.upper())
    if expected and expected != cfg.currency.upper():
        checks.append(CheckResult(
            name="country_currency", status="warn",
            message=f"{cfg.country} typically uses {expected}, got {cfg.currency}",
        ))
    else:
        checks.append(CheckResult(name="country_currency", status="ok",
                                  message=f"{cfg.country} / {cfg.currency}"))

    return aggregate(checks)
