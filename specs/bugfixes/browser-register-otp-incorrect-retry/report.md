# Bugfix Report: Browser Register OTP Incorrect Retry

**Date:** 2026-05-04
**Status:** Fixed

## Description of the Issue

The browser registration flow successfully read an OTP from Cloudflare KV and
entered it into the OpenAI email-verification page, but the page displayed
`Incorrect code`. The automation then continued into the about-you wait path
instead of treating the OTP page as failed or retrying with a fresh code.

**Reproduction steps:**
1. Run `xvfb-run -a python -u pipeline.py --config /mnt/d/WORKSPACE/ai-space/Gpt-Agreement-Payment/CTF-pay/config.paypal.json --paypal`.
2. Let registration reach `/email-verification`.
3. Observe logs showing `收到 OTP=...`.
4. Observe the page showing `Incorrect code` while the automation continues.

**Impact:** Registration could hang on the OTP page and later fail as an
about-you timeout, hiding the actual verification failure.

## Investigation Summary

- **Symptoms examined:** KV polling succeeded and returned a code, but the UI
  rejected it.
- **Code inspected:** `CTF-reg/browser_register.py`,
  `CTF-reg/cf_kv_otp_provider.py`, and `scripts/otp_email_worker.js`.
- **Hypotheses tested:** The KV key not appearing in Cloudflare dashboard is
  expected because `delete_after_read=True` deletes the key immediately after a
  successful read. The mail web UI not listing the generated address is also
  expected because catch-all Worker delivery does not create mailbox accounts.

## Discovered Root Cause

`browser_register.py` did not inspect the OTP page after clicking Continue. It
assumed any submitted OTP was accepted and moved on to the next registration
phase.

**Defect type:** Missing UI error handling.

**Why it occurred:** Earlier logic only handled “OTP input not found” and did not
model rejected-code states.

**Contributing factors:** KV read success logs did not include the email subject
or timestamp, making it harder to determine whether the Worker extracted the
correct message.

## Resolution for the Issue

**Changes made:**
- `CTF-reg/browser_register.py` - Detects `Incorrect code` and related OTP error
  text after submitting a code.
- `CTF-reg/browser_register.py` - Clicks `Resend email`, waits for a new KV OTP,
  refills the input, and retries once by default.
- `CTF-reg/browser_register.py` - Raises a direct OTP verification error if all
  attempts fail, instead of continuing to about-you.
- `CTF-reg/cf_kv_otp_provider.py` - Logs OTP payload timestamp and subject on
  successful KV reads.
- `tests/browser_register_otp_error_test.py` - Adds regression coverage for
  incorrect-code text detection.

**Approach rationale:** Retrying through the page's own resend control gets a
fresh code tied to the current challenge and preserves KV stale-code filtering.

**Alternatives considered:**
- Keep KV entries after read - Useful for manual inspection, but it would not
  fix rejected-code handling and risks stale-code reuse.
- Continue waiting on about-you - Rejected because the page explicitly reported
  OTP failure.

## Regression Test

**Test file:** `tests/browser_register_otp_error_test.py`

**Test names:**
- `test_text_has_incorrect_otp_matches_openai_message`
- `test_text_has_incorrect_otp_ignores_normal_page`

**What it verifies:** The browser flow can recognize the OpenAI incorrect-code
message and keep normal OTP pages separate.

**Run command:** `python -m pytest tests/browser_register_otp_error_test.py -q`

## Affected Files

| File | Change |
|------|--------|
| `CTF-reg/browser_register.py` | Adds OTP rejection detection and resend retry. |
| `CTF-reg/cf_kv_otp_provider.py` | Logs subject and timestamp for read OTP payloads. |
| `tests/browser_register_otp_error_test.py` | Adds OTP error detection tests. |
| `specs/bugfixes/browser-register-otp-incorrect-retry/report.md` | Documents root cause and verification. |

## Verification

**Automated:**
- [x] `python -m pytest tests/browser_register_otp_timing_test.py tests/browser_register_otp_error_test.py tests/camoufox_geoip_test.py -q`
- [x] `python -m compileall -q shared CTF-reg/browser_register.py CTF-reg/cf_kv_otp_provider.py CTF-pay/card.py tests/browser_register_otp_timing_test.py tests/browser_register_otp_error_test.py tests/camoufox_geoip_test.py`
- [x] `python -m ruff check --select=E9,F63,F7,F82 --no-fix shared CTF-reg/browser_register.py CTF-reg/cf_kv_otp_provider.py CTF-pay/card.py tests/browser_register_otp_timing_test.py tests/browser_register_otp_error_test.py tests/camoufox_geoip_test.py`

**Manual verification:**
- Reviewed the provided screenshot and log: the UI rejected the entered code,
  while the code continued as if verification had passed.
- Did not run the live pipeline because it consumes external registration,
  mailbox, proxy, and payment-related resources.

## Prevention

**Recommendations to avoid similar bugs:**
- Treat visible page errors as state transitions, not as incidental text.
- Log enough OTP metadata to diagnose extraction mistakes without opening the KV
  value manually.
- Keep generated catch-all addresses distinct from mailbox-account expectations;
  the Worker/KV path is not the same storage surface as the mail web inbox.

## Related

- User-provided screenshot showing `Incorrect code` after entering the OTP.
