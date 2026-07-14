# Streamlit Environment Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run `apps/web/streamlit/app_v3.py` from one project-managed environment that can import both Streamlit and `tau_ai`.

**Architecture:** Preserve the editable-install package boundary and repair only the repository `.venv`. Invoke Streamlit through the `.venv` interpreter so package and frontend resolution cannot split across Python installations.

**Tech Stack:** Python, uv, Streamlit, setuptools editable install

## Global Constraints

- Keep `src/tau_ai` and the documented editable-install requirement.
- Do not add `src` to `sys.path` or `PYTHONPATH`.
- Do not modify the Homebrew Python environment.
- Do not modify runtime source files.

---

### Task 1: Repair and Verify the Project Environment

**Files:**
- Modify environment only: `.venv/`
- Verify: `pyproject.toml`
- Verify: `apps/web/streamlit/app_v3.py`

**Interfaces:**
- Consumes: the `ui` optional dependency group and editable Tau distribution from `pyproject.toml`.
- Produces: a `.venv` interpreter that imports `tau_ai` and Streamlit and starts `app_v3.py`.

- [x] **Step 1: Confirm the red state**

Run:

```bash
uv run --no-sync python -c 'import streamlit'
```

Expected: exit 1 with `ModuleNotFoundError: No module named 'streamlit'`.

- [x] **Step 2: Install Tau with the UI extra into `.venv`**

Run:

```bash
uv pip install -e ".[ui]"
```

Expected: exit 0; `tau==0.1.0` and `streamlit>=1.58.0` are installed in `.venv`.

- [x] **Step 3: Verify both packages use the project environment**

Run:

```bash
uv run --no-sync python -c 'import sys, streamlit, tau_ai; print(sys.executable); print(streamlit.__version__); print(tau_ai.__file__)'
```

Expected: the executable is `.venv/bin/python`, Streamlit is at least 1.58.0, and `tau_ai` resolves to `src/tau_ai/__init__.py`.

- [x] **Step 4: Run package regression checks**

Run:

```bash
uv run --no-sync python scripts/smoke_tau_ai.py
uv run --no-sync python scripts/smoke_packaging.py
```

Expected: both commands print `[SMOKE-OK]` and exit 0.

- [x] **Step 5: Start the real Streamlit entry point**

Run:

```bash
uv run --no-sync python -m streamlit run apps/web/streamlit/app_v3.py --server.port 18503 --server.address 127.0.0.1 --server.headless true
```

Expected: the server listens on port 18503 without `ModuleNotFoundError: No module named 'tau_ai'`. Request `http://127.0.0.1:18503/_stcore/health`, verify `ok`, then stop the temporary server.

- [x] **Step 6: Confirm tracked source remains unchanged**

Run:

```bash
git status --short
```

Expected: no runtime source file changed; pre-existing user changes remain untouched.
