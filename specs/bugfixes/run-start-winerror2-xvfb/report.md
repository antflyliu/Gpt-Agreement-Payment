# Bugfix Report: Run Start Winerror2 Xvfb

**Date:** 2026-05-04
**Status:** Fixed

## Description of the Issue

Clicking "开始运行" on the WebUI Run page failed immediately with:

`failed to spawn: [WinError 2] 系统找不到指定的文件。`

**Reproduction steps:**
1. Run the WebUI backend with Windows Python.
2. Open `/webui/run?mode=single`.
3. Click "开始运行".

**Impact:** The Run page could not launch `pipeline.py` from a Windows-hosted backend.

## Investigation Summary

- **Symptoms examined:** Browser toast, `/webui/api/run/status`, and WebUI server logs.
- **Code inspected:** `webui/backend/runner.py`, `webui/backend/routes/run.py`, and `webui/tests/test_run.py`.
- **Hypotheses tested:** Config health failure, stale active process, and missing runner executable.

## Discovered Root Cause

`runner.build_cmd()` always returned a Linux-oriented command:

`xvfb-run -a python -u pipeline.py ...`

When the WebUI backend runs on Windows, `subprocess.Popen(["xvfb-run", ...])` cannot resolve that command reliably and raises `FileNotFoundError`.

**Defect type:** Platform-specific process launcher bug.

**Why it occurred:** The runner assumed the backend always ran in Linux/WSL, but the WebUI can also run under Windows Python.

**Contributing factors:** A Windows `xvfb-run.cmd` shim may exist, but it forwards arguments into WSL and is not safe for Windows paths such as `D:\WORKSPACE\...`.

## Resolution for the Issue

**Changes made:**
- `webui/backend/runner.py` - Added a platform-safe base command builder. Linux uses `xvfb-run` when available; Windows uses `sys.executable -u pipeline.py`.
- `webui/tests/test_run.py` - Added regression coverage for Windows/no-xvfb command generation and the start path.

**Approach rationale:** Use the current Python interpreter to preserve the active virtualenv/runtime, and only use `xvfb-run` in non-Windows environments where it is actually valid.

**Alternatives considered:**
- Use the Windows `xvfb-run.cmd` shim - rejected because it forwards Windows paths into WSL without conversion.
- Always remove `xvfb-run` - rejected because Linux/WSL deployments still need it for browser automation.

## Regression Test

**Test file:** `webui/tests/test_run.py`

**Test name:** `test_runner_uses_current_python_when_xvfb_unavailable`

**What it verifies:** Windows command generation uses the current Python executable and does not include `xvfb-run`.

**Run command:** `python -m pytest webui/tests/test_run.py -v`

## Affected Files

| File | Change |
|------|--------|
| `webui/backend/runner.py` | Platform-aware pipeline launcher |
| `webui/tests/test_run.py` | Regression tests for no-xvfb launcher |
| `specs/bugfixes/run-start-winerror2-xvfb/report.md` | Bugfix report |

## Verification

**Automated:**
- [x] Regression test passes
- [x] Run controller tests pass
- [x] Full test suite passes
- [x] Syntax validation passes

**Manual verification:**
- `/webui/api/run/preview` now returns `C:\Python312\python.exe -u pipeline.py ...` on the current Windows-hosted WebUI service.
- `/webui/api/run/status` is idle after restart.

## Prevention

**Recommendations to avoid similar bugs:**
- Build process commands from resolved executables, not hardcoded bare command names.
- Keep platform-sensitive launchers behind small helper functions with tests.
- Avoid Windows-to-WSL `.cmd` shims for commands that receive repo-local Windows paths.

## Related

- User report: Run page "开始运行" failed with `[WinError 2]`.
