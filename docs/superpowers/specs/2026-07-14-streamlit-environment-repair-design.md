# Streamlit Environment Repair

**Date:** 2026-07-14

## Goal

Run `apps/web/streamlit/app_v3.py` with one project-managed Python
environment in which both the editable Tau distribution and Streamlit are
installed.

## Approach

- Keep the `src/tau_ai` package boundary and editable-install requirement.
- Do not add `src` to `sys.path` or `PYTHONPATH`.
- Install the existing `ui` extra into the repository `.venv` with `uv`.
- Start Streamlit through that environment's Python module entry point rather
  than the Homebrew `streamlit` executable.

## Verification

1. The `.venv` interpreter imports both `tau_ai` and `streamlit` and reports
   their paths and versions.
2. The existing `tau_ai` and clean-install packaging smoke tests pass.
3. A headless `app_v3.py` server starts on a temporary port without
   `ModuleNotFoundError: No module named 'tau_ai'`.

## Non-goals

- Supporting an uninstalled checkout through runtime path injection.
- Changing Streamlit application behavior or Tau's package layout.
- Installing or upgrading packages in the Homebrew Python environment.
