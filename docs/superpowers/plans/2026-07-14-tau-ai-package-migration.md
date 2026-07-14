# `tau_ai` Package Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the complete LLM implementation from `core/llm` to `src/tau_ai`, make `tau_ai` the only supported import path, and ship it correctly in editable installs and wheels without changing runtime behavior.

**Architecture:** Keep Tau's existing root packages in place and add `src/tau_ai` as a second setuptools discovery root. Preserve the current module boundaries and facade, use absolute imports only for the retained `core.paths` dependency, and hard-switch every repository consumer without a compatibility shim.

**Tech Stack:** Python 3.10–3.13, setuptools ≥68, uv, unittest, wheel/zip inspection

## Global Constraints

- Keep `core/`, `TMWebDriver/`, and the other intentional top-level modules in place.
- Use `uv`; do not use pip, venv, or poetry directly.
- `tau_ai` remains part of the existing `tau` distribution and may depend on `core.paths`.
- Do not change public names, configuration fields, provider behavior, retry behavior, logging, trimming, or key reload semantics.
- Remove `core/llm` completely; do not add an alias, compatibility shim, or deprecation layer.
- Preserve the existing editable-install requirement; do not mutate `sys.path` for an uninstalled checkout.
- Keep the user's existing `memory/l3_capability_inventory.md` worktree change untouched and out of every commit.

## Baseline

Recorded on 2026-07-14 before implementation:

- `uv run --no-sync python -m unittest discover -s tests -v`: 8 tests passed.
- `uv run --no-sync python scripts/smoke_llmcore.py`: passed.
- `uv run --no-sync python scripts/smoke_packaging.py`: passed.

---

### Task 1: Migrate the Package and Every Runtime Consumer

**Files:**
- Create: `tests/test_tau_ai_package.py`
- Create by exact move: `src/tau_ai/__init__.py`
- Create by exact move: `src/tau_ai/clients.py`
- Create by exact move: `src/tau_ai/convert.py`
- Create by exact move: `src/tau_ai/keys.py`
- Create by exact move: `src/tau_ai/response.py`
- Create by exact move: `src/tau_ai/session.py`
- Create by exact move: `src/tau_ai/transport.py`
- Create by exact move: `src/tau_ai/trim.py`
- Create by exact move: `src/tau_ai/taukey.json`
- Create by exact move: `src/tau_ai/providers/__init__.py`
- Create by exact move: `src/tau_ai/providers/claude.py`
- Create by exact move: `src/tau_ai/providers/openai.py`
- Delete after exact move: `core/llm/`
- Modify: `pyproject.toml:1-52`

**Interfaces:**
- Consumes: `core.paths.TAUKEY_PATH`, `core.paths.TEMP`, and the existing `core.llm` file contents.
- Produces: importable `tau_ai`, `tau_ai.keys`, `tau_ai.transport`, `tau_ai.providers.claude`, and `tau_ai.providers.openai`; packaged data file `tau_ai/taukey.json`.

- [ ] **Step 1: Add a failing package-boundary test**

Create `tests/test_tau_ai_package.py` with this complete content:

```python
import importlib.util
import unittest
from pathlib import Path


class TestTauAiPackage(unittest.TestCase):

    def test_facade_exports_come_from_tau_ai(self):
        from tau_ai import BaseSession, ClaudeSession, LLMSession, ToolClient

        for exported in (BaseSession, ClaudeSession, LLMSession, ToolClient):
            self.assertTrue(exported.__module__.startswith("tau_ai."))

    def test_core_llm_is_removed(self):
        self.assertIsNone(importlib.util.find_spec("core.llm"))

    def test_legacy_key_json_is_beside_keys_module(self):
        import tau_ai.keys

        legacy = Path(tau_ai.keys.__file__).with_name("taukey.json")
        self.assertTrue(legacy.is_file(), legacy)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the boundary test and verify the red state**

Run:

```bash
uv run --no-sync python -m unittest tests.test_tau_ai_package -v
```

Expected: failure or error because `tau_ai` does not exist, and
`test_core_llm_is_removed` reports a non-`None` module spec.

- [ ] **Step 3: Move the package without changing implementation logic**

Use `apply_patch` to move every tracked file from `core/llm/` to the matching
path under `src/tau_ai/`. Preserve each file byte-for-byte except for these
two required namespace corrections:

```python
# src/tau_ai/transport.py
from core.paths import TEMP
```

```python
# src/tau_ai/session.py
"""Abstract Session base. Provider subclasses live in tau_ai/providers/."""
```

`src/tau_ai/keys.py` already uses the correct retained dependency:

```python
from core.paths import TAUKEY_PATH
```

Do not copy `.DS_Store`, `__pycache__`, or `.pyc` files. Confirm the old
directory has no tracked or source files left:

```bash
find core/llm -type f -not -path '*/__pycache__/*' -not -name '.DS_Store' 2>/dev/null
git diff --name-status -- core/llm src/tau_ai
```

Expected: `find` prints no source files. The diff lists each old tracked path
as deleted and each destination path as added; Git may display them as renames
after staging.

- [ ] **Step 4: Configure mixed-root discovery and package data**

Change the dependency comment and replace the setuptools discovery section
with exactly:

```toml
dependencies = [
    "requests>=2.28",                 # src/tau_ai/transport.py
    "beautifulsoup4>=4.12",           # simphtml.py
    "bottle>=0.12",                   # TMWebDriver.py
    "simple-websocket-server>=0.4",   # TMWebDriver.py
]

[tool.setuptools]
py-modules = []

[tool.setuptools.packages.find]
where = [".", "src"]
include = ["core*", "reflect*", "tau_cli*", "plugins*", "memory*", "TMWebDriver*", "tau_ai*"]
exclude = ["apps*", "tests*", "scripts*", "docs*", "assets*", "sche_tasks*", "temp*"]
namespaces = false

[tool.setuptools.package-data]
tau_ai = ["taukey.json"]
```

Do not alter project metadata, dependencies, extras, or the `tau` entry point.

- [ ] **Step 5: Refresh the editable installation**

Run:

```bash
uv pip install -e .
```

Expected: `tau==0.1.0` installs successfully and the refreshed editable
mapping exposes `tau_ai` from `src/tau_ai`.

- [ ] **Step 6: Run the boundary test and verify the green state**

Run:

```bash
uv run --no-sync python -m unittest tests.test_tau_ai_package -v
```

Expected: all 3 tests pass.

- [ ] **Step 7: Confirm the package boundary before switching consumers**

```bash
git diff --check -- pyproject.toml tests/test_tau_ai_package.py src/tau_ai core/llm
```

Expected: no output. Do not commit yet: the old runtime consumers must switch
in the same atomic commit so every commit remains runnable.

#### Phase B: Switch Every Runtime Consumer to `tau_ai`

**Files:**
- Modify: `core/taumain.py:8-11`
- Modify: `apps/im/dingtalk.py:14`
- Modify: `apps/im/feishu.py:21`
- Modify: `apps/im/qq.py:14`
- Modify: `apps/im/telegram.py:36`
- Modify: `apps/im/wecom.py:30`
- Modify: `apps/pet/app.py:24`
- Modify: `apps/common/cost_tracker.py:127`
- Modify: `plugins/langfuse_tracing.py:13,21`
- Modify: `tests/test_taukey_path.py:26-42`
- Create: `scripts/smoke_tau_ai.py`
- Delete: `scripts/smoke_llmcore.py`
- Modify: `scripts/smoke_packaging.py:5-6`

**Interfaces:**
- Consumes: the `tau_ai` facade and submodules produced by Task 1.
- Produces: all Tau runtime entry points, integrations, plugins, and key tests importing only `tau_ai`; smoke coverage for the hard-cut namespace.

- [ ] **Step 1: Run affected tests to expose old-import failures**

Run:

```bash
uv run --no-sync python -m unittest discover -s tests -v
uv run --no-sync python scripts/smoke_packaging.py
uv run --no-sync python scripts/smoke_llmcore.py
```

Expected: failures identify remaining `core.llm` or `.llm` consumers. The
exact first failure may differ by import order; do not change exception
handling to hide it.

- [ ] **Step 2: Update production imports with exact replacements**

Apply these replacements and no behavioral edits:

```python
# core/taumain.py
from tau_ai.keys import reload_taukeys
from tau_ai.clients import ToolClient, NativeToolClient, MixinSession, resolve_client
from tau_ai.providers.openai import LLMSession, NativeOAISession
from tau_ai.providers.claude import ClaudeSession, NativeClaudeSession
```

```python
# apps/im/{dingtalk,feishu,qq,telegram,wecom}.py and apps/pet/app.py
from tau_ai.keys import taukeys
```

```python
# apps/common/cost_tracker.py
import tau_ai as llmcore
```

```python
# plugins/langfuse_tracing.py
from tau_ai import _load_taukeys
```

```python
# plugins/langfuse_tracing.py inside install()
import plugins.hooks as hooks, tau_ai as llmcore
```

Keep the existing local import positions so optional integrations retain their
current import-time behavior.

- [ ] **Step 3: Update key-loader test isolation for the new module**

In `tests/test_taukey_path.py`, replace the module cleanup and imports with:

```python
# Reload core.paths and tau_ai with TAU_HOME=tmp.
for mod in list(sys.modules):
    if mod == "core.paths" or mod == "tau_ai" or mod.startswith("tau_ai."):
        del sys.modules[mod]
from core.paths import TAU, TAUKEY_PATH  # noqa
from tau_ai.keys import _load_taukeys, reload_taukeys  # noqa
```

After the imports, locate the fallback beside the loaded module:

```python
import tau_ai.keys as keys_module

self._legacy_json = Path(keys_module.__file__).with_name("taukey.json")
```

Update the adjacent comments from `core/llm` to `tau_ai`; leave the temporary
file backup/restore behavior unchanged.

- [ ] **Step 4: Replace the LLM smoke test with the new namespace**

Use `apply_patch` to create `scripts/smoke_tau_ai.py` from the complete content
of `scripts/smoke_llmcore.py`, then delete the old file. Apply all of these
exact textual changes:

```text
core.llm       -> tau_ai
core/llm       -> src/tau_ai
llm.trim       -> tau_ai.trim
llm.transport  -> tau_ai.transport
llm.convert    -> tau_ai.convert
llm.response   -> tau_ai.response
llm.session    -> tau_ai.session
llm.providers  -> tau_ai.providers
llm.clients    -> tau_ai.clients
```

The resulting assertions must compare exact module suffixes such as:

```python
assert BaseSession.__module__.endswith("tau_ai.session")
assert ClaudeSession.__module__.endswith("tau_ai.providers.claude")
assert LLMSession.__module__.endswith("tau_ai.providers.openai")
assert ToolClient.__module__.endswith("tau_ai.clients")
```

Retain coverage of every public facade export and load-bearing private export
present in the original smoke test.

- [ ] **Step 5: Include `tau_ai` in the clean-cwd packaging smoke**

Make the first entry in `scripts/smoke_packaging.py` explicit:

```python
TOPLEVEL = ["tau_ai", "core.paths", "core.taumain", "TMWebDriver",
            "TMWebDriver.simphtml", "plugins.hooks", "memory.email_config",
            "reflect.scheduler"]
```

- [ ] **Step 6: Run focused and full verification**

Run:

```bash
uv run --no-sync python -m unittest tests.test_tau_ai_package tests.test_taukey_path -v
uv run --no-sync python scripts/smoke_tau_ai.py
uv run --no-sync python scripts/smoke_packaging.py
uv run --no-sync python -m unittest discover -s tests -v
```

Expected: 7 focused tests pass, both smoke scripts print `[SMOKE-OK]`, and all
11 tests pass.

- [ ] **Step 7: Commit the atomic package and consumer migration**

```bash
git add pyproject.toml src/tau_ai core/llm core/taumain.py apps/im apps/pet/app.py apps/common/cost_tracker.py plugins/langfuse_tracing.py tests/test_tau_ai_package.py tests/test_taukey_path.py scripts/smoke_tau_ai.py scripts/smoke_llmcore.py scripts/smoke_packaging.py
git commit -m "refactor: move llm package to tau_ai"
```

Expected: one runnable commit contains the package move, packaging changes,
all consumer switches, tests, and smoke updates. The user's
`memory/l3_capability_inventory.md` remains unstaged.

---

### Task 2: Update Integration Documentation and Verify the Distribution

**Files:**
- Modify: `scripts/README.md:13`
- Verify: `pyproject.toml`
- Verify: `src/tau_ai/**`
- Verify: `dist/tau-0.1.0-py3-none-any.whl`

**Interfaces:**
- Consumes: the migrated source tree and consumer imports from Task 1.
- Produces: accurate integration documentation and evidence that the wheel ships only the new LLM package boundary.

- [ ] **Step 1: Update the remaining active documentation reference**

Change the `scripts/README.md` table cell to:

```markdown
| `api_examples/` | 直接调 `tau_ai.transport` 的示范 | 第三方接入 demo |
```

- [ ] **Step 2: Prove active code and docs contain no old namespace**

Run:

```bash
rg -n "(from|import) core\.llm|from \.llm|core/llm" core apps plugins tests scripts pyproject.toml README.md docs --glob '!docs/superpowers/**'
```

Expected: no output. The narrower expression checks active imports and stale
path documentation without rejecting the intentional negative assertion
`find_spec("core.llm")`. Historical design and implementation documents under
`docs/superpowers/` are excluded because they intentionally describe the
before/after boundary.

- [ ] **Step 3: Compile every affected Python area**

Run:

```bash
uv run --no-sync python -m compileall -q src/tau_ai core apps plugins tests scripts
```

Expected: exit code 0 and no output.

- [ ] **Step 4: Build the wheel with uv**

Run:

```bash
uv build --wheel
```

Expected: success and `dist/tau-0.1.0-py3-none-any.whl` is created.

- [ ] **Step 5: Assert exact wheel contents**

Run:

```bash
uv run --no-sync python -c 'import zipfile; p="dist/tau-0.1.0-py3-none-any.whl"; n=set(zipfile.ZipFile(p).namelist()); assert "tau_ai/__init__.py" in n; assert "tau_ai/providers/claude.py" in n; assert "tau_ai/providers/openai.py" in n; assert "tau_ai/taukey.json" in n; assert not any(x.startswith("core/llm/") for x in n); print("wheel contents: PASS")'
```

Expected: `wheel contents: PASS`.

- [ ] **Step 6: Run the final behavioral verification**

Run:

```bash
uv run --no-sync python -m unittest discover -s tests -v
uv run --no-sync python scripts/smoke_tau_ai.py
uv run --no-sync python scripts/smoke_packaging.py
git diff --check -- scripts/README.md
git status --short
```

Expected: all 11 tests pass; both smokes print `[SMOKE-OK]`; `git diff --check`
prints nothing for the task-owned file; status shows only the planned
documentation change plus the user's pre-existing
`memory/l3_capability_inventory.md` modification. The check is scoped because
that excluded user file has pre-existing trailing whitespace.

- [ ] **Step 7: Commit the documentation update**

```bash
git add scripts/README.md
git commit -m "docs: update tau_ai integration reference"
```

Expected: the commit contains only `scripts/README.md`.

- [ ] **Step 8: Review the completed migration**

Invoke the repository's code-review workflow against the commit immediately
before Task 1. Review both axes:

```text
Standards: AGENTS.md, memory/code_review_principles.md, CONTRIBUTING.md
Spec: docs/superpowers/specs/2026-07-14-tau-ai-package-migration-design.md
```

Address only actionable findings within this migration's approved scope, then
repeat the affected tests and wheel-content assertion before declaring the
work complete.
