# Bugfix Report: PayPal DataDome Manual Handoff

**Date:** 2026-05-04
**Status:** Fixed

## Description of the Issue

The PayPal browser authorization flow reached
`https://www.paypal.com/agreements/approve?...` and passed an initial DataDome
slider, but later remained on the same agreements page with a DataDome iframe.
The B6 wait loop treated that state as another visible slider, attempted the
drag solver, and failed the entire payment flow with
`RuntimeError: DataDome 滑块 solver 失败`.

**Reproduction steps:**
1. Start the WebUI in WSL with `python -m webui.server`.
2. Open `http://127.0.0.1:8765/webui/run`, sign in, and start a PayPal payment
   run.
3. Let the flow reach the PayPal agreements approval page.
4. Observe logs ending with `CARD_DATADOME_SLIDER=1` and
   `RuntimeError: DataDome 滑块 solver 失败`.

**Impact:** The pipeline aborted even when the browser was visible and the
operator could manually complete PayPal's challenge.

## Investigation Summary

- **Symptoms examined:** User-provided `wsl_test_02.log` showed successful
  ChatGPT account registration, successful Stripe PayPal payment method
  creation, successful ChatGPT manual approval, and failure only after PayPal
  redirected to the agreements approval page.
- **Code inspected:** `CTF-pay/card.py` PayPal redirect handling, especially
  `_paypal_browser_authorize(...)`, `_slider_visible()`,
  `_try_solve_ddc_slider(...)`, and the B6 agreements wait loop.
- **Hypotheses tested:** The first DataDome event can pass, but a later
  agreements-page DataDome iframe may remain or reappear. The old code had no
  safe recovery path except automatic drag retry or immediate failure.

## Discovered Root Cause

The B6 loop conflated two states:

- a confirmed visible DataDome slider; and
- an agreements page that still had a DataDome/captcha iframe after 15 seconds.

Both states entered the same auto-drag branch. If the second state did not expose
a usable slider handle, `_try_solve_ddc_slider(...)` returned false and the
browser flow raised immediately.

**Defect type:** Browser state-machine recovery gap.

**Why it occurred:** The code assumed the automation should keep trying the
legacy drag path whenever PayPal's DataDome iframe was present.

**Contributing factors:** The browser was already visible, but the code did not
offer a manual handoff/resume point for challenges that require human action.

## Resolution for the Issue

**Changes made:**
- `CTF-pay/card.py` - Added environment helpers for boolean/integer feature
  flags.
- `CTF-pay/card.py` - Added PayPal DataDome manual handoff defaults:
  `CARD_PAYPAL_DDC_MANUAL_HANDOFF=1` behavior when a visible browser is
  available.
- `CTF-pay/card.py` - Made the legacy DataDome auto-drag behavior opt-in through
  `CARD_PAYPAL_DDC_AUTO_DRAG=1`.
- `CTF-pay/card.py` - Changed B-DDC and B6 handling to pause for manual
  completion, watch for the page to progress, and then resume the existing
  PayPal authorization flow.
- `tests/paypal_datadome_handoff_test.py` - Added regression tests for the
  default/manual and opt-in/auto-drag switches plus continuation readiness.

**Approach rationale:** The safe recovery path is to keep the visible browser
open and let the operator complete PayPal's challenge. The automation then
continues only after the page reaches a normal next state such as signin,
authflow, Hermes, checkout, ChatGPT, or the consent button.

**Alternatives considered:**
- Strengthen the drag solver - Rejected because the failure is an anti-bot
  challenge and should not be solved automatically.
- Keep failing with `CARD_DATADOME_SLIDER=1` - Rejected because it wastes a
  recoverable visible-browser run.
- Remove DataDome detection entirely - Rejected because the logs and screenshots
  are still important for diagnosing PayPal risk checks.

## Regression Test

**Test file:** `tests/paypal_datadome_handoff_test.py`

**Test names:**
- `test_paypal_ddc_manual_handoff_defaults_to_visible_browser`
- `test_paypal_ddc_auto_drag_is_opt_in`
- `test_paypal_ddc_continuation_ready_detects_hermes_url`
- `test_paypal_ddc_continuation_ready_detects_visible_login_input`

**What it verifies:** The PayPal DataDome path now defaults to manual handoff
when the browser is visible, keeps automatic dragging opt-in, and recognizes
normal continuation states after a challenge is completed.

**Run command:** `python -m pytest tests/paypal_datadome_handoff_test.py -q`

## Affected Files

| File | Change |
|------|--------|
| `CTF-pay/card.py` | Adds DataDome manual handoff and opt-in auto-drag controls. |
| `tests/paypal_datadome_handoff_test.py` | Adds focused regression coverage. |
| `specs/bugfixes/paypal-datadome-manual-handoff/report.md` | Documents root cause and verification. |

## Verification

**Automated:**
- [x] `python -m pytest tests/paypal_datadome_handoff_test.py -q`
- [x] `python -m pytest tests/paypal_datadome_handoff_test.py tests/camoufox_geoip_test.py tests/browser_register_otp_timing_test.py tests/browser_register_otp_error_test.py -q`
- [x] `python -m compileall -q CTF-pay/card.py tests/paypal_datadome_handoff_test.py`
- [x] `python -m ruff check --select=E9,F63,F7,F82 --no-fix CTF-pay/card.py tests/paypal_datadome_handoff_test.py`
- [x] `python -m ruff check --select=E9,F63,F7,F82 --no-fix .`

**Manual verification:**
- Reviewed the provided WSL log and matched the failure to B6 DataDome handling
  in `CTF-pay/card.py`.
- Did not run a live end-to-end PayPal payment attempt during this fix because
  it would interact with third-party payment and anti-bot systems.

## Prevention

**Recommendations to avoid similar bugs:**
- Keep anti-bot challenges as explicit manual handoff states when the browser is
  visible.
- Treat iframe presence and visible-slider presence as different browser states.
- Preserve screenshots and markers (`CARD_DATADOME_*`) so operators can see
  exactly why the flow paused or failed.

## Related

- User-provided `C:/Users/Administrator/Downloads/wsl_test_02.log`.
