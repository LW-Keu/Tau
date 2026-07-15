# `tau_agent.plugins` Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the complete top-level `plugins` package into `src/tau_agent/plugins`, preserve hook and discovery behavior, and remove the legacy namespace.

**Architecture:** Keep the hook registry and built-in Langfuse integration together under `tau_agent.plugins`. Default discovery imports installed package modules without changing `sys.path`; explicit plugin directories retain their existing parent-path import mechanism. Switch every active consumer atomically and remove the top-level package without a shim.

**Tech Stack:** Python 3.10–3.13, setuptools ≥68, uv, unittest, compileall, wheel/zip inspection

## Global Constraints

- Move all three tracked files from `plugins/` to `src/tau_agent/plugins/`.
- Preserve hook registration order, dictionary context threading, error isolation, clearing, unregistering, and discovery ordering.
- Preserve optional Langfuse activation, tracing, SSE usage extraction, and failure handling.
- Preserve `discover_and_load(plugin_dir=None)` and `load(name)` as public interfaces.
- Remove `plugins`, `plugins.hooks`, and `plugins.langfuse_tracing` completely; do not add aliases, fallback modules, or compatibility shims.
- Default built-in discovery must not mutate `sys.path`.
- Explicit plugin directories remain importable by adding only their parent directory when absent.
- Add no dependency and do not change Tau's command-line entry point.
- Use `uv`; do not use pip, venv, or poetry directly.
- Do not modify or stage the user's existing `tau_cli/start_scheduler.sh` change.

## Baseline

Recorded on 2026-07-15 before implementation:

- `uv run --no-sync python -m unittest discover -s tests -v`: 14 tests passed.
- `uv run --no-sync python scripts/smoke_tau.py`: passed.
- `uv run --no-sync python scripts/smoke_packaging.py`: passed.

---

### Task 1: Move the Plugin Runtime and Switch Consumers Atomically

**Files:**
- Create: `tests/test_tau_agent_plugins.py`
- Create by exact move: `src/tau_agent/plugins/__init__.py`
- Create by move and targeted edit: `src/tau_agent/plugins/hooks.py`
- Create by move and targeted edit: `src/tau_agent/plugins/langfuse_tracing.py`
- Delete after move: `plugins/__init__.py`
- Delete after move: `plugins/hooks.py`
- Delete after move: `plugins/langfuse_tracing.py`
- Modify: `src/tau_agent/agent_loop.py:4-5`
- Modify: `core/taumain.py:13-15`
- Modify: `pyproject.toml:48-52`
- Modify: `scripts/smoke_packaging.py:5-7`

**Interfaces:**
- Consumes: `tau_agent.plugins.hooks.register(event)`, `trigger(event, ctx)`, `unregister(event, fn)`, `clear(event=None)`, `has(event)`, `discover_and_load(plugin_dir=None)`, and `load(name)` from the current top-level implementation.
- Produces: the same interfaces under `tau_agent.plugins.hooks`; built-in module names `tau_agent.plugins.hooks` and `tau_agent.plugins.langfuse_tracing`; explicit-directory imports by directory basename.

- [ ] **Step 1: Add failing namespace and behavior tests**

Create `tests/test_tau_agent_plugins.py` with this complete content:

```python
import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path


def _find_spec(name):
    try:
        return importlib.util.find_spec(name)
    except ModuleNotFoundError:
        return None


class TestTauAgentPluginBoundary(unittest.TestCase):

    def test_hook_symbols_come_from_tau_agent(self):
        from tau_agent.plugins.hooks import discover_and_load, register, trigger

        for exported in (discover_and_load, register, trigger):
            self.assertEqual(exported.__module__, "tau_agent.plugins.hooks")

    def test_old_plugins_package_is_removed(self):
        for module in ("plugins", "plugins.hooks", "plugins.langfuse_tracing"):
            with self.subTest(module=module):
                self.assertIsNone(_find_spec(module))


class TestHookRegistry(unittest.TestCase):

    def setUp(self):
        from tau_agent.plugins import hooks

        self.hooks = hooks
        self.hooks.clear()

    def tearDown(self):
        self.hooks.clear()

    def test_trigger_threads_context_in_registration_order(self):
        seen = []

        @self.hooks.register("event")
        def first(ctx):
            seen.append(("first", ctx["value"]))
            return {"value": ctx["value"] + 1}

        @self.hooks.register("event")
        def second(ctx):
            seen.append(("second", ctx["value"]))
            return {"value": ctx["value"] * 2}

        self.assertTrue(self.hooks.has("event"))
        self.assertEqual(self.hooks.trigger("event", {"value": 3}), {"value": 8})
        self.assertEqual(seen, [("first", 3), ("second", 4)])

        self.hooks.unregister("event", first)
        self.assertEqual(self.hooks.trigger("event", {"value": 3}), {"value": 6})

    def test_clear_removes_one_event_or_the_whole_registry(self):
        @self.hooks.register("first")
        def first(ctx):
            return ctx

        @self.hooks.register("second")
        def second(ctx):
            return ctx

        self.hooks.clear("first")
        self.assertFalse(self.hooks.has("first"))
        self.assertTrue(self.hooks.has("second"))

        self.hooks.clear()
        self.assertFalse(self.hooks.has("second"))

    def test_callback_error_does_not_skip_later_callbacks(self):
        called = []

        @self.hooks.register("event")
        def broken(ctx):
            raise RuntimeError("boom")

        @self.hooks.register("event")
        def later(ctx):
            called.append(ctx["value"])

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            result = self.hooks.trigger("event", {"value": 7})

        self.assertEqual(result, {"value": 7})
        self.assertEqual(called, [7])
        self.assertIn("[hooks] event callback error: boom", stderr.getvalue())

    def test_explicit_plugin_directory_loads_by_package_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / "fixture_plugins"
            package.mkdir()
            (package / "__init__.py").write_text("", encoding="utf-8")
            (package / "demo.py").write_text(
                "from tau_agent.plugins.hooks import register\n"
                "@register('external')\n"
                "def callback(ctx):\n"
                "    return {'loaded': ctx['value']}\n",
                encoding="utf-8",
            )
            try:
                self.hooks.discover_and_load(str(package))
                self.assertEqual(
                    self.hooks.trigger("external", {"value": 9}),
                    {"loaded": 9},
                )
                self.assertIn("fixture_plugins.demo", sys.modules)
            finally:
                if tmp in sys.path:
                    sys.path.remove(tmp)
                for name in list(sys.modules):
                    if name == "fixture_plugins" or name.startswith("fixture_plugins."):
                        del sys.modules[name]


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the new tests and verify the RED state**

Run:

```bash
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python -m unittest tests.test_tau_agent_plugins -v
```

Expected: five tests error because `tau_agent.plugins` does not exist, and
`test_old_plugins_package_is_removed` fails because all three old module
specs are present. The command must reach test execution without syntax or
discovery errors.

- [ ] **Step 3: Move the package files**

Use `apply_patch` move operations for all three tracked files:

```text
plugins/__init__.py             -> src/tau_agent/plugins/__init__.py
plugins/hooks.py                -> src/tau_agent/plugins/hooks.py
plugins/langfuse_tracing.py     -> src/tau_agent/plugins/langfuse_tracing.py
```

Keep `__init__.py` empty. Preserve `langfuse_tracing.py` byte-for-byte except
for the import change in Step 5. Replace `hooks.py` with the complete code in
Step 4. Remove the residual top-level `plugins/` directory, including ignored
bytecode, after the tracked files have moved so `plugins` cannot survive as a
namespace package.

- [ ] **Step 4: Implement package-relative discovery without changing hook behavior**

Replace `src/tau_agent/plugins/hooks.py` with:

```python
import importlib
import os
import sys

_registry = {}


def register(event):
    def decorator(fn):
        _registry.setdefault(event, []).append(fn)
        return fn
    return decorator


def trigger(event, ctx: dict):
    for fn in _registry.get(event, []):
        try:
            r = fn(ctx)
            if isinstance(r, dict):
                ctx = r
        except Exception as e:
            sys.stderr.write(f"[hooks] {event} callback error: {e}\n")
    return ctx


def unregister(event, fn):
    try:
        _registry[event] = [f for f in _registry[event] if f is not fn]
    except KeyError:
        pass


def clear(event=None):
    if event:
        _registry.pop(event, None)
    else:
        _registry.clear()


def has(event):
    return bool(_registry.get(event))


def discover_and_load(plugin_dir=None):
    package = __package__
    if plugin_dir is None:
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
    else:
        plugin_dir = os.path.abspath(plugin_dir)
        parent = os.path.dirname(plugin_dir)
        if parent not in sys.path:
            sys.path.insert(0, parent)
        package = os.path.basename(plugin_dir)
    if not os.path.isdir(plugin_dir):
        return
    for fn in sorted(os.listdir(plugin_dir)):
        if fn.startswith('_') or not fn.endswith('.py'):
            continue
        load(fn[:-3], package)


def load(name, package=None):
    try:
        importlib.import_module(f'{package or __package__}.{name}')
        return True
    except Exception as e:
        sys.stderr.write(f"[hooks] plugin '{name}' load failed: {e}\n")
        return False
```

This preserves the existing registry and failure behavior. The only logic
change is namespace-aware discovery: default discovery uses
`tau_agent.plugins`, while an explicit directory uses its basename.

- [ ] **Step 5: Switch the built-in Langfuse plugin to its sibling hooks module**

In `src/tau_agent/plugins/langfuse_tracing.py`, replace only:

```python
if _lf:
    from . import hooks
    import tau_ai as llmcore
```

Keep every callback, exception boundary, usage parser, and monkey patch below
this import unchanged.

- [ ] **Step 6: Switch runtime consumers to the new namespace**

In `src/tau_agent/agent_loop.py`, use:

```python
try: from .plugins.hooks import trigger as _hook
except ImportError: _hook = lambda *a, **k: None
```

In `core/taumain.py`, use:

```python
try:
    from tau_agent.plugins.hooks import discover_and_load; discover_and_load()
except Exception: pass
```

Do not change hook call sites, discovery timing, or exception handling.

- [ ] **Step 7: Remove the root package from packaging and switch the smoke**

Change the setuptools include list in `pyproject.toml` to:

```toml
include = ["core*", "reflect*", "tau_cli*", "memory*", "TMWebDriver*", "tau_ai*", "tau_agent*"]
```

Change `TOPLEVEL` in `scripts/smoke_packaging.py` to:

```python
TOPLEVEL = ["tau_agent", "tau_agent.plugins.hooks", "tau_ai", "core.paths",
            "core.taumain", "TMWebDriver", "TMWebDriver.simphtml",
            "memory.email_config", "reflect.scheduler"]
```

- [ ] **Step 8: Refresh the editable installation**

Run:

```bash
UV_CACHE_DIR=/tmp/tau-uv-cache uv pip install -e .
```

Expected: `tau==0.1.0` installs successfully and exposes
`tau_agent.plugins` from `src/tau_agent/plugins`.

- [ ] **Step 9: Verify the GREEN state**

Run:

```bash
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python -m unittest tests.test_tau_agent_plugins -v
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python scripts/smoke_tau.py
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python scripts/smoke_packaging.py
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python -m unittest discover -s tests -v
git diff --check -- src/tau_agent plugins core/taumain.py pyproject.toml scripts/smoke_packaging.py tests/test_tau_agent_plugins.py
```

Expected: all 6 plugin tests pass; both smokes print `[SMOKE-OK]`; all 20
tests pass; the scoped diff check prints nothing.

- [ ] **Step 10: Commit the atomic runtime migration**

```bash
git add src/tau_agent/plugins src/tau_agent/agent_loop.py plugins core/taumain.py pyproject.toml scripts/smoke_packaging.py tests/test_tau_agent_plugins.py
git diff --cached --check
git diff --cached --stat
git commit -m "refactor: move plugins into tau_agent"
```

Expected: the staged diff contains only plugin moves, namespace/discovery
changes, active consumers, packaging smoke, and tests. It does not include
`tau_cli/start_scheduler.sh`.

---

### Task 2: Update Current References and Verify the Wheel Boundary

**Files:**
- Modify: `README.md:135-146`
- Modify: `src/tau_ai/__init__.py:11-16`
- Modify: `scripts/smoke_tau_ai.py:14`

**Interfaces:**
- Consumes: `tau_agent.plugins` produced by Task 1.
- Produces: current architecture and integration references naming the new namespace; a verified wheel with no top-level `plugins` package.

- [ ] **Step 1: Update the architecture tree**

Change the `src/` entry in `README.md` and delete the top-level `plugins/`
entry:

```text
├── src/          # 可安装内核包:tau_agent(Agent · tools · plugins) · tau_ai
```

Keep all other tree entries unchanged.

- [ ] **Step 2: Update current Langfuse integration references**

In `src/tau_ai/__init__.py`, replace the facade-consumer reference with:

```text
`_load_taukeys` (tau_agent.plugins.langfuse_tracing).
```

In `scripts/smoke_tau_ai.py`, replace the matching comment fragment with:

```text
(tau_agent.plugins.langfuse_tracing._load_taukeys, apps/common/cost_tracker._record_usage).
```

- [ ] **Step 3: Audit active old references**

Run:

```bash
rg -n "from plugins|import plugins|plugins\.hooks|plugins/langfuse_tracing|├── plugins/|plugins\*" --glob '!docs/superpowers/**' --glob '!tests/test_tau_agent_plugins.py' --glob '!**/__pycache__/**' .
```

Expected: no output. The negative namespace test and historical migration
documents are intentionally excluded.

- [ ] **Step 4: Compile the migrated boundary**

Run:

```bash
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python -m compileall -q src/tau_agent/plugins src/tau_agent/agent_loop.py core/taumain.py tests/test_tau_agent_plugins.py
```

Expected: exit code 0 and no output.

- [ ] **Step 5: Build a clean wheel and assert its contents**

Remove only the ignored setuptools build directory, then build:

```bash
rm -rf build
UV_CACHE_DIR=/tmp/tau-uv-cache uv build --wheel --out-dir /tmp/tau-agent-plugins-wheel
```

Inspect with:

```bash
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python -c "import zipfile; names=set(zipfile.ZipFile('/tmp/tau-agent-plugins-wheel/tau-0.1.0-py3-none-any.whl').namelist()); required={'tau_agent/plugins/__init__.py','tau_agent/plugins/hooks.py','tau_agent/plugins/langfuse_tracing.py'}; forbidden={'plugins/__init__.py','plugins/hooks.py','plugins/langfuse_tracing.py'}; assert required <= names, required-names; assert not forbidden & names, forbidden & names; print('plugin wheel boundary: PASS')"
```

Expected: the build succeeds and the assertion prints
`plugin wheel boundary: PASS`. Existing setuptools warnings about the license
table or `memory` package discovery are reported separately and are not fixed
in this migration.

- [ ] **Step 6: Run the final pre-commit verification gate**

Run:

```bash
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python -m unittest discover -s tests -v
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python scripts/smoke_tau.py
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python scripts/smoke_packaging.py
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python -c "import importlib.util; assert importlib.util.find_spec('tau_agent.plugins.hooks'); assert importlib.util.find_spec('plugins') is None; print('plugin package boundary: PASS')"
git diff --check -- README.md src/tau_ai/__init__.py scripts/smoke_tau_ai.py
git status --short
```

Expected: all 20 tests and both smokes pass; the boundary command prints
`plugin package boundary: PASS`; the scoped diff check prints nothing. Status
shows the three reference files plus the unrelated user-owned scheduler
change, with no untracked migration file.

- [ ] **Step 7: Commit current reference updates**

```bash
git add README.md src/tau_ai/__init__.py scripts/smoke_tau_ai.py
git diff --cached --check
git diff --cached --stat
git commit -m "docs: update tau_agent plugin references"
```

Expected: the staged diff contains exactly three reference files and excludes
`tau_cli/start_scheduler.sh`.

- [ ] **Step 8: Re-run the completion gate after the final commit**

Run:

```bash
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python -m unittest discover -s tests -v
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python scripts/smoke_tau.py
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python scripts/smoke_packaging.py
git status --short
```

Expected: all 20 tests and both smokes pass. Status contains only the existing
user-owned `tau_cli/start_scheduler.sh` modification.
