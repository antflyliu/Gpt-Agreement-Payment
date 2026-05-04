# Bugfix Report: Browser Register OTP Issued After

**Date:** 2026-05-04
**Status:** Fixed

## Description of the Issue

The browser registration flow reached the OpenAI email-verification page and
then waited for the Cloudflare KV OTP. KV polling repeatedly found a value for
the exact recipient address, but ignored it because the value timestamp was
earlier than the `issued_after` threshold.

**Reproduction steps:**
1. Run `xvfb-run -a python -u pipeline.py --config /mnt/d/WORKSPACE/ai-space/Gpt-Agreement-Payment/CTF-pay/config.paypal.json --paypal`.
2. Let the browser flow submit the signup email and reach `/email-verification`.
3. Observe logs like `key=... 命中但 ts=1777868445 < threshold=1777868485，忽略旧值`.

**Impact:** The flow timed out waiting for OTP even though Cloudflare Email
Routing, the Worker, and KV had already received and stored a code.

## Investigation Summary

- **Symptoms examined:** KV was not empty; it contained an OTP for the generated
  address.
- **Code inspected:** `CTF-reg/browser_register.py`,
  `CTF-reg/cf_kv_otp_provider.py`, `CTF-reg/auth_flow.py`, and
  `scripts/otp_email_worker.js`.
- **Hypotheses tested:** The code set `otp_sent_at = time.time()` only after the
  page had already reached OTP input. In the provided log, the OTP was written
  around 40 seconds before that threshold, right after email submission.

## Discovered Root Cause

`browser_register.py` recorded the OTP acceptance timestamp too late. On the
passwordless signup branch, OpenAI can send the email OTP immediately after the
email Continue click, while the automation may spend tens of seconds waiting
for password-page timeout and anti-fraud checks before it starts KV polling.

**Defect type:** Timing/window logic error.

**Why it occurred:** The code treated “OTP input visible” as the moment an OTP
was sent. In reality, the send can happen much earlier in the browser flow.

**Contributing factors:** The old log text still said `IMAP OTP`, even though
the active path is Cloudflare KV, making the failure look like a mailbox problem
instead of a timestamp filter problem.

## Resolution for the Issue

**Changes made:**
- `CTF-reg/browser_register.py` - Added `_OtpIssueWindow` to record the browser
  actions that can trigger an OTP email.
- `CTF-reg/browser_register.py` - Marked the timestamp before clicking email
  Continue and before clicking password Continue.
- `CTF-reg/browser_register.py` - Reused that earlier timestamp when waiting for
  KV OTP and updated the log wording to `等待邮箱 OTP`.
- `tests/browser_register_otp_timing_test.py` - Added regression tests for the
  OTP timing window.

**Approach rationale:** Moving the timestamp to the triggering browser action
keeps stale-code protection while accepting the real OTP that arrives before the
automation reaches the OTP input.

**Alternatives considered:**
- Widen the KV provider's global grace window - Rejected because it weakens stale
  OTP protection for every caller.
- Ignore timestamps entirely - Rejected because leftover KV values can remain
  for the configured TTL.

## Regression Test

**Test file:** `tests/browser_register_otp_timing_test.py`

**Test names:**
- `test_otp_issue_window_uses_first_trigger_time`
- `test_otp_issue_window_updates_for_later_trigger`

**What it verifies:** The registration flow can keep the timestamp from the
action that likely sent the OTP instead of using the later polling start time.

**Run command:** `python -m pytest tests/browser_register_otp_timing_test.py -q`

## Affected Files

| File | Change |
|------|--------|
| `CTF-reg/browser_register.py` | Tracks possible OTP send time before email/password submit. |
| `tests/browser_register_otp_timing_test.py` | Adds timing-window regression coverage. |
| `specs/bugfixes/browser-register-otp-issued-after/report.md` | Documents root cause and verification. |

## Verification

**Automated:**
- [x] Regression test passes:
  `python -m pytest tests/browser_register_otp_timing_test.py -q`
- [x] Existing Camoufox GeoIP regression test still passes:
  `python -m pytest tests/camoufox_geoip_test.py -q`
- [x] Syntax check passes:
  `python -m compileall -q CTF-reg/browser_register.py tests/browser_register_otp_timing_test.py`

**Manual verification:**
- Interpreted the provided timestamps: KV `ts=1777868445` was earlier than the
  old threshold `1777868485` but after the email Continue click, so it matches
  the current run rather than a domain-delivery failure.

## Prevention

**Recommendations to avoid similar bugs:**
- For browser flows, record OTP send windows at browser actions that can trigger
  email delivery, not when the OTP input becomes visible.
- Keep timestamp filtering in KV polling, but avoid setting `issued_after` after
  long challenge/navigation waits.
- Use logs that name the active backend (`CF KV`/`邮箱 OTP`) so mailbox routing
  and local filtering failures are easier to separate.

## Related

- User-provided pipeline log with repeated `命中但 ts < threshold` messages.
