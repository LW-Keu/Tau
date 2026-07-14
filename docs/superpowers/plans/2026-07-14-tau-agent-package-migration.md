# `tau_agent` Package Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the Agent loop, handler, and tools from `core` to `src/tau_agent`, make `tau_agent` their only supported import path, and preserve runtime behavior.

**Architecture:** Keep Tau's intentional mixed package layout and retain `core.paths` plus `core.taumain`. Move the requested runtime modules as one atomic package boundary, use absolute imports only for the retained `core.paths` dependency, switch every active consumer, and remove the old modules without compatibility shims.

**Tech Stack:** Python 3.10–3.13, setuptools ≥68, uv, unittest, compileall, wheel/zip inspection

## Global Constraints

- Keep `core/`, `TMWebDriver/`, and the other intentional top-level modules in place.
- Move only `core/agent_loop.py`, `core/handler.py`, and `core/tools/`; do not move `core.paths` or `core.taumain`.
- Preserve Agent loop, handler, tool, subprocess, browser, file I/O, hook, error, and exit behavior.
- Remove `core.agent_loop`, `core.handler`, and `core.tools` completely; do not add aliases, fallback imports, deprecation modules, or compatibility shims.
- Keep `tau_agent.__init__` lightweight and do not re-export implementation symbols.
- Add no dependency and do not change Tau's command-line entry point.
- Use `uv`; do not use pip, venv, or poetry directly.
- Do not mutate `sys.path` to support an uninstalled checkout.
- Leave the user's existing `.gitignore`, `memory/l3_capability_inventory.md`, `scripts/asrun`, `.todos/`, and `bin/` changes untouched and out of every commit.

## Baseline

Recorded on 2026-07-14 before implementation with `UV_CACHE_DIR` redirected
to `/tmp` because the sandbox cannot write the default uv cache:

- `uv run --no-sync python -m unittest discover -s tests -v`: 11 tests passed.
- `uv run --no-sync python scripts/smoke_tau.py`: passed.
- `uv run --no-sync python scripts/smoke_packaging.py`: passed.

---

### Task 1: Move the Runtime Package and Switch Consumers Atomically

**Files:**
- Create: `tests/test_tau_agent_package.py`
- Create: `src/tau_agent/__init__.py`
- Create by exact move: `src/tau_agent/agent_loop.py`
- Create by exact move: `src/tau_agent/handler.py`
- Create by exact move: `src/tau_agent/tools/__init__.py`
- Create by exact move: `src/tau_agent/tools/code_run.py`
- Create by exact move: `src/tau_agent/tools/file_io.py`
- Create by exact move: `src/tau_agent/tools/web.py`
- Create by exact move: `src/tau_agent/tools/utils.py`
- Delete after exact move: `core/agent_loop.py`
- Delete after exact move: `core/handler.py`
- Delete after exact move: `core/tools/__init__.py`
- Delete after exact move: `core/tools/code_run.py`
- Delete after exact move: `core/tools/file_io.py`
- Delete after exact move: `core/tools/web.py`
- Delete after exact move: `core/tools/utils.py`
- Modify: `core/taumain.py:12-18`
- Modify: `pyproject.toml:1-54`
- Modify: `scripts/smoke_tau.py:1-10`
- Modify: `scripts/smoke_packaging.py:5-7`

**Interfaces:**
- Consumes: `core.paths.MEMORY`, `core.paths.TEMP`, `core.paths.ASSETS`, the current runtime module contents, and the existing setuptools mixed-root layout.
- Produces: `tau_agent.agent_loop.BaseHandler`, `tau_agent.agent_loop.StepOutcome`, `tau_agent.agent_loop.agent_runner_loop`, `tau_agent.handler.TauHandler`, and the existing tool functions under `tau_agent.tools.<module>`.

- [ ] **Step 1: Add the failing package-boundary test**

Create `tests/test_tau_agent_package.py` with this complete content:

```python
import importlib.util
import unittest


class TestTauAgentPackage(unittest.TestCase):

    def test_runtime_symbols_come_from_tau_agent(self):
        from tau_agent.agent_loop import BaseHandler, StepOutcome
        from tau_agent.handler import TauHandler

        self.assertEqual(BaseHandler.__module__, "tau_agent.agent_loop")
        self.assertEqual(StepOutcome.__module__, "tau_agent.agent_loop")
        self.assertEqual(TauHandler.__module__, "tau_agent.handler")

    def test_tool_symbols_come_from_tau_agent(self):
        from tau_agent.tools.code_run import code_run
        from tau_agent.tools.file_io import file_read
        from tau_agent.tools.utils import smart_format
        from tau_agent.tools.web import web_scan

        self.assertEqual(code_run.__module__, "tau_agent.tools.code_run")
        self.assertEqual(file_read.__module__, "tau_agent.tools.file_io")
        self.assertEqual(smart_format.__module__, "tau_agent.tools.utils")
        self.assertEqual(web_scan.__module__, "tau_agent.tools.web")

    def test_old_core_modules_are_removed(self):
        for module in ("core.agent_loop", "core.handler", "core.tools"):
            with self.subTest(module=module):
                self.assertIsNone(importlib.util.find_spec(module))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the boundary test and verify the red state**

Run:

```bash
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python -m unittest tests.test_tau_agent_package -v
```

Expected: the first two tests error because `tau_agent` does not exist, and
`test_old_core_modules_are_removed` fails because each old module still has a
module spec. The command must not fail because of a syntax or test-discovery
error.

- [ ] **Step 3: Create the lightweight package marker**

Create `src/tau_agent/__init__.py` with exactly:

```python
"""Tau Agent runtime package."""
```

Do not import or re-export any submodule from this file.

- [ ] **Step 4: Move the runtime files and correct only their namespaces**

Use `apply_patch` to move each listed source file to its matching destination.
Preserve implementation code byte-for-byte except for these required import
and documentation corrections:

```python
# src/tau_agent/handler.py
from .agent_loop import BaseHandler, StepOutcome, json_default
from .tools.utils import (smart_format, consume_file, log_memory_access,
                          expand_file_refs, get_global_memory)
from .tools.code_run import code_run, ask_user
from .tools.file_io import file_read, file_patch, file_write
from .tools.web import web_scan, web_execute_js
from core.paths import MEMORY
```

```python
# src/tau_agent/tools/code_run.py
from .utils import smart_format
from core.paths import TEMP, ASSETS
```

```python
# src/tau_agent/tools/utils.py
from core.paths import MEMORY, ASSETS, TEMP
```

Replace `src/tau_agent/tools/__init__.py` with exactly:

```python
"""Tool implementations; consumers import from tau_agent.tools submodules."""
```

`agent_loop.py`, `file_io.py`, and `web.py` require no code change beyond the
move. Delete every old source path after its destination exists. Do not move
`core/__init__.py`, `core/paths.py`, or `core/taumain.py`.

Confirm the physical boundary:

```bash
find core/tools -type f -not -path '*/__pycache__/*' -not -name '.DS_Store' 2>/dev/null
git diff --name-status -- core/agent_loop.py core/handler.py core/tools src/tau_agent
```

Expected: `find` prints no source files. The diff lists the seven old paths as
deleted and the eight destination files as added; Git may display the seven
matching files as renames after staging.

- [ ] **Step 5: Switch the retained runtime entry point**

Replace only `core/taumain.py:12-18` with:

```python
from tau_agent.agent_loop import agent_runner_loop
try:
    from plugins.hooks import discover_and_load; discover_and_load()
except Exception: pass
from tau_agent.handler import TauHandler
from tau_agent.tools.utils import smart_format, get_global_memory, format_error, consume_file
from .paths import TAU_HOME, MEMORY, ASSETS, TEMP
```

Keep the four `tau_ai` imports above this block and all executable behavior
below it unchanged.

- [ ] **Step 6: Include `tau_agent` in package discovery**

Update the install hint and package include list in `pyproject.toml` to:

```toml
# base deps = what the installed packages (core* + tau_agent* + tau_ai* +
# simphtml/TMWebDriver) import;
```

```toml
[tool.setuptools.packages.find]
where = [".", "src"]
include = ["core*", "reflect*", "tau_cli*", "plugins*", "memory*", "TMWebDriver*", "tau_ai*", "tau_agent*"]
exclude = ["apps*", "tests*", "scripts*", "docs*", "assets*", "sche_tasks*", "temp*"]
namespaces = false
```

Do not change project metadata, dependencies, extras, package data, or the
`tau` entry point.

- [ ] **Step 7: Switch the Agent symbol smoke test**

Replace `scripts/smoke_tau.py` with:

```python
"""Smoke test: tau_agent symbols import from their defining modules."""
from tau_agent.handler import TauHandler
from tau_agent.tools.utils import smart_format, format_error, consume_file, get_global_memory
from tau_agent.tools.code_run import code_run, ask_user
from tau_agent.tools.file_io import file_read, file_patch
from tau_agent.tools.web import web_scan, web_execute_js, first_init_driver
from tau_agent.tools.utils import smart_format as sf2
print(f'[SMOKE-OK] handler={TauHandler.__module__} smart_format={smart_format is sf2} '
      f'code_run={code_run.__module__} file_io={file_read.__module__} web={web_scan.__module__}')
```

The intentionally imported-but-not-called symbols retain import coverage for
the complete tool surface used by the existing smoke test.

- [ ] **Step 8: Include `tau_agent` in the clean-directory packaging smoke**

Change only `TOPLEVEL` in `scripts/smoke_packaging.py` to:

```python
TOPLEVEL = ["tau_agent", "tau_ai", "core.paths", "core.taumain",
            "TMWebDriver", "TMWebDriver.simphtml", "plugins.hooks",
            "memory.email_config", "reflect.scheduler"]
```

- [ ] **Step 9: Refresh the editable installation**

Run:

```bash
UV_CACHE_DIR=/tmp/tau-uv-cache uv pip install -e .
```

Expected: `tau==0.1.0` installs successfully and the editable mapping exposes
`tau_agent` from `src/tau_agent`.

- [ ] **Step 10: Verify the green state and affected entry points**

Run:

```bash
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python -m unittest tests.test_tau_agent_package -v
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python scripts/smoke_tau.py
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python scripts/smoke_packaging.py
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python -m unittest discover -s tests -v
git diff --check -- pyproject.toml core src/tau_agent scripts/smoke_tau.py scripts/smoke_packaging.py tests/test_tau_agent_package.py
```

Expected: all 3 boundary tests pass; both smoke scripts print `[SMOKE-OK]`;
all 14 tests pass; `git diff --check` prints nothing.

- [ ] **Step 11: Commit the atomic runtime migration**

Review the staged scope before committing:

```bash
git add pyproject.toml src/tau_agent core/agent_loop.py core/handler.py core/tools core/taumain.py scripts/smoke_tau.py scripts/smoke_packaging.py tests/test_tau_agent_package.py
git diff --cached --check
git diff --cached --stat
git commit -m "refactor: move agent runtime to tau_agent"
```

Expected: the staged diff contains only the package move, package discovery,
runtime consumer changes, and their tests/smokes. It does not include any
pre-existing user modification.

---

### Task 2: Update Current References and Verify the Distribution Boundary

**Files:**
- Modify: `README.md:132-145`
- Modify: `tau_cli/__init__.py:1-4`
- Modify: `scripts/README.md:1-5`
- Modify: `assets/scripts/README.md:9`
- Modify: `docs/installation.md:130-137,259-267`
- Modify: `docs/installation_zh.md:130-137,259-267`
- Modify: `apps/common/continue_cmd.py:275-359`
- Modify: `apps/tui/app.py:106,2041`

**Interfaces:**
- Consumes: the `tau_agent` package and hard-cut import boundary produced by Task 1.
- Produces: current architecture, installation, CLI, script, and source references that name `tau_agent`; a verified wheel containing the new package and excluding the removed modules.

- [ ] **Step 1: Update the architecture tree**

Replace the first two package lines in the `README.md` architecture tree with:

```text
├── core/         # Tau 入口与路径配置:taumain · paths
├── src/          # 可安装内核包:tau_agent · tau_ai
```

Keep every other architecture entry unchanged.

- [ ] **Step 2: Update current import guidance**

Apply these exact replacements:

```python
# tau_cli/__init__.py
"""tau_cli - Tau CLI 命令包。

`python -m tau_cli`（或安装后的 `tau` 命令）进入 CLI，见 tau_cli/cli.py。
核心类请直接从真实模块导入，例如 `from tau_agent.handler import TauHandler`."""
```

```markdown
<!-- scripts/README.md line 4 -->
Agent 不可见；agent 在 SOP/工具中**只**通过 `tau_agent.tools.*` API 调用业务逻辑。
```

```markdown
<!-- assets/scripts/README.md table row -->
| `code_run_header.py` | `code_run` 工具的 subprocess 注入头 | `src/tau_agent/tools/code_run.py` |
```

In both occurrences in `docs/installation.md`, replace the verification
command with:

```bash
python -c "import tau_agent.agent_loop; print('OK')"
```

In both occurrences in `docs/installation_zh.md`, use the same command.

- [ ] **Step 3: Qualify source comments that reference the moved loop**

In `apps/common/continue_cmd.py`, replace each prose occurrence of
`agent_loop` or `agent_loop.py` with `tau_agent.agent_loop`. In
`apps/tui/app.py`, make the same replacement in the comments at lines 106 and
2041. Do not change executable code, strings presented to users, marker
formats, or line-number references.

The resulting examples include:

```python
"""Match tau_agent.agent_loop:72 verbose tool-call header."""
```

```python
# Strip the leading marker that tau_agent.agent_loop yields per turn.
```

- [ ] **Step 4: Check current references without rewriting history or user data**

Run:

```bash
rg -n "core\.(agent_loop|handler|tools)|core/(agent_loop\.py|handler\.py|tools)|import agent_loop|agent_loop\.py" --glob '!docs/superpowers/**' --glob '!memory/l3_capability_inventory.md' --glob '!**/__pycache__/**' .
```

Expected: no output. Historical design/plan documents remain unchanged.
`memory/l3_capability_inventory.md` is explicitly excluded because it contains
an unrelated user modification; report its stale reference instead of editing
or staging that file.

- [ ] **Step 5: Compile the migrated Python boundary**

Run:

```bash
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python -m compileall -q src/tau_agent core/taumain.py scripts/smoke_tau.py tests/test_tau_agent_package.py
```

Expected: exit code 0 and no output.

- [ ] **Step 6: Build and inspect the wheel**

Run:

```bash
UV_CACHE_DIR=/tmp/tau-uv-cache uv build --wheel --out-dir /tmp/tau-agent-wheel
unzip -l /tmp/tau-agent-wheel/tau-0.1.0-py3-none-any.whl
```

Expected: build exits 0. The wheel listing includes all eight files under
`tau_agent/` and includes `core/paths.py` plus `core/taumain.py`; it contains
no `core/agent_loop.py`, `core/handler.py`, or `core/tools/` entry.

- [ ] **Step 7: Run final verification from fresh process boundaries**

Run:

```bash
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python -m unittest discover -s tests -v
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python scripts/smoke_tau.py
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python scripts/smoke_packaging.py
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python -c "import importlib.util; assert importlib.util.find_spec('tau_agent.handler'); assert importlib.util.find_spec('core.handler') is None; print('package boundary: PASS')"
git diff --check -- README.md tau_cli/__init__.py scripts/README.md assets/scripts/README.md docs/installation.md docs/installation_zh.md apps/common/continue_cmd.py apps/tui/app.py
git status --short
```

Expected: all 14 tests pass; both smokes print `[SMOKE-OK]`; the explicit
boundary check prints `package boundary: PASS`; `git diff --check` prints
nothing. `git status --short` may show the known unrelated user modifications,
but no untracked or unstaged migration file.

- [ ] **Step 8: Commit reference updates**

```bash
git add README.md tau_cli/__init__.py scripts/README.md assets/scripts/README.md docs/installation.md docs/installation_zh.md apps/common/continue_cmd.py apps/tui/app.py
git diff --cached --check
git diff --cached --stat
git commit -m "docs: update tau_agent package references"
```

Expected: the staged diff contains only current reference updates and no
pre-existing user modification.

- [ ] **Step 9: Re-run the completion gate after the final commit**

Run:

```bash
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python -m unittest discover -s tests -v
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python scripts/smoke_tau.py
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python scripts/smoke_packaging.py
git status --short
```

Expected: all 14 tests and both smoke scripts pass. Status contains only the
known user-owned changes; the migration is fully committed.
