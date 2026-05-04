# Bugfix Report: Camoufox Invalid GeoIP MMDB

**Date:** 2026-05-04
**Status:** Fixed

## Description of the Issue

The WSL pipeline failed during the registration step before any browser page
opened. `CTF-reg/browser_register.py` launched Camoufox with `geoip=True`, which
caused Camoufox to open its bundled `GeoLite2-City.mmdb`. The file existed but
was not a valid MaxMind database, so `maxminddb` raised `InvalidDatabaseError`.

**Reproduction steps:**
1. Run `xvfb-run -a python -u pipeline.py --config /mnt/d/WORKSPACE/ai-space/Gpt-Agreement-Payment/CTF-pay/config.paypal.json --paypal`.
2. Let the pipeline enter Step 1 registration.
3. Observe `maxminddb.errors.InvalidDatabaseError` from Camoufox startup.

**Impact:** Registration aborted before the ChatGPT signup page loaded. The same
hardcoded `geoip=True` pattern also existed in the PayPal browser authorization
and Codex refresh-token browser login paths.

## Investigation Summary

- **Symptoms examined:** The traceback pointed to `camoufox.utils.launch_options`
  calling `get_geolocation(geoip)`, then failing in
  `maxminddb.open_database(...)`.
- **Code inspected:** `CTF-reg/browser_register.py`,
  `CTF-pay/card.py`, Camoufox's installed `utils.py` and `locale.py`, and
  `docs/debugging.md`.
- **Hypotheses tested:** Confirmed in WSL that the exact MMDB path from the
  traceback could not be opened by `maxminddb` while it was corrupted.

## Discovered Root Cause

`geoip=True` was hardcoded in every Camoufox launch site. Camoufox downloads the
MMDB only when the file is missing; it does not recover when the file exists but
is invalid. That made a corrupt generated dependency artifact fatal for all
browser-based flows.

**Defect type:** Missing dependency-artifact validation.

**Why it occurred:** The project assumed Camoufox's packaged GeoIP database was
always readable when present.

**Contributing factors:** The WSL runtime stores Camoufox under
`webui/.venv_build/base/...`, so a bad generated artifact can persist across
runs even after project code is unchanged.

## Resolution for the Issue

**Changes made:**
- `shared/camoufox_runtime.py` - Added a shared resolver for Camoufox's `geoip`
  option. It validates an existing MMDB with `maxminddb.open_database()` and
  returns `False` when the DB is unusable.
- `CTF-reg/browser_register.py` - Uses the resolver for registration browser
  launch instead of hardcoding `geoip=True`.
- `CTF-pay/card.py` - Uses the resolver for PayPal browser authorization and
  Codex refresh-token browser login.
- `tests/camoufox_geoip_test.py` - Added a regression test for an invalid MMDB.

**Approach rationale:** A code-level guard keeps the pipeline from aborting when
the generated MMDB is corrupt, while preserving normal `geoip=True` behavior
when the database is valid or missing and Camoufox can download it.

**Alternatives considered:**
- Delete or redownload the MMDB during every launch - Rejected because it mutates
  the virtual environment and still fails if the network is unavailable.
- Disable GeoIP everywhere unconditionally - Rejected because valid installs
  should keep Camoufox's normal geolocation behavior.

## Regression Test

**Test file:** `tests/camoufox_geoip_test.py`
**Test name:** `test_resolve_camoufox_geoip_disables_invalid_mmdb`

**What it verifies:** When Camoufox's MMDB exists but `maxminddb.open_database`
raises an invalid-database error, the project passes `geoip=False` to Camoufox.

**Run command:** `python -m pytest tests/camoufox_geoip_test.py -q`

## Affected Files

| File | Change |
|------|--------|
| `shared/__init__.py` | Added shared helper package marker. |
| `shared/camoufox_runtime.py` | Added safe Camoufox GeoIP option resolution. |
| `CTF-reg/browser_register.py` | Applied safe GeoIP resolution to registration. |
| `CTF-pay/card.py` | Applied safe GeoIP resolution to browser payment/login flows. |
| `tests/camoufox_geoip_test.py` | Added invalid-MMDB regression coverage. |

## Verification

**Automated:**
- [x] Regression test passes: `python -m pytest tests/camoufox_geoip_test.py -q`
- [x] Syntax check passes:
  `python -m compileall -q shared CTF-reg/browser_register.py CTF-pay/card.py tests/camoufox_geoip_test.py`
- [ ] Full test suite passes

**Manual verification:**
- Reproduced the original WSL `maxminddb.open_database(...)` failure against the
  Camoufox MMDB path while it was corrupt.
- Verified the WSL Camoufox MMDB now opens as `GeoLite2-City` after the local
  environment refreshed the generated artifact.
- Ran `python -m pytest webui/tests -q`; it failed with existing WebUI API route
  404/405 failures unrelated to this registration Camoufox launch fix.

## Prevention

**Recommendations to avoid similar bugs:**
- Route all Camoufox launch options through `shared.camoufox_runtime` instead of
  adding direct `geoip=True` call-site literals.
- Keep generated virtual environments and MMDB files out of source control.
- If strict geolocation spoofing is required for a specific run, refresh the
  Camoufox MMDB first and verify it with `maxminddb.open_database()`.

## Related

- User-provided WSL traceback for
  `webui/.venv_build/base/lib/python3.12/site-packages/camoufox/GeoLite2-City.mmdb`.
