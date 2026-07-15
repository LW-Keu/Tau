# `tau_coding` Package Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move Tau's remaining composition, CLI, reflect, and launcher-script code into `src/tau_coding` and make that package the only supported boundary.

**Architecture:** Keep `tau_coding.paths` as a standard-library-only leaf and `tau_coding.taumain` as the composition root over `tau_ai` and `tau_agent`. Move source, package configuration, entry points, and all active runtime consumers atomically so no commit mixes deleted packages with old imports.

**Tech Stack:** Python 3.10–3.13, setuptools ≥68, uv, unittest, importlib, shell/cmd launchers, wheel/zip inspection

## Global Constraints

- Create one installable `src/tau_coding` package containing `taumain.py`, `paths.py`, `cli.py`, `commands/`, `reflect/`, and `scripts/`.
- Remove top-level `core`, `tau_cli`, and `reflect` completely; add no aliases, fallback imports, deprecation modules, or compatibility shims.
- Keep `tau_coding.__init__` lightweight: it must not import `Tau`, load model configuration, discover plugins, or re-export implementation symbols.
- Preserve Tau, Agent, model, CLI, scheduler, goal, autonomous, team-worker, PID, log, and stop-script behavior.
- Keep `TAU_HOME` as the single root anchor and preserve its environment override.
- Support both `tau_coding.reflect.<name>` module targets and user-authored reflect file paths.
- Include `tau_coding/scripts/*.sh` and `tau_coding/scripts/*.cmd` in the wheel.
- Add no dependency and do not package repository-only `apps/` or `assets/` into the wheel.
- Use `uv`; do not use pip, venv, or poetry directly.
- Preserve the user's current `tau_cli/start_scheduler.sh` expansion byte-for-byte except for the two required target changes.
- Move ignored runtime PID/log files to `src/tau_coding/scripts/`; do not delete or commit them.
- Keep historical `docs/superpowers` records and retired-path notes in `docs/SETUP_EMAIL.md` unchanged.

## Baseline

Recorded on 2026-07-15 with `UV_CACHE_DIR=/tmp/tau-uv-cache`:

- Full unit suite: 20 tests passed.
- `scripts/smoke_tau.py`, `scripts/smoke_tau_ai.py`, and `scripts/smoke_packaging.py`: passed.
- Pre-existing tracked change: only `tau_cli/start_scheduler.sh` is modified.

---

### Task 1: Move the Runtime Boundary Atomically

**Files:**
- Create: `tests/test_tau_coding_package.py`
- Move: `core/__init__.py`, `core/paths.py`, `core/taumain.py` → `src/tau_coding/`
- Move: `tau_cli/__main__.py`, `tau_cli/cli.py` → `src/tau_coding/`
- Move: `tau_cli/commands/{__init__,_common,_launchers,list,run,status,update}.py` → `src/tau_coding/commands/`
- Move: `reflect/{__init__,agent_team_worker,autonomous,goal_mode,scheduler}.py` → `src/tau_coding/reflect/`
- Move: `tau_cli/{start,start_autonomous,start_scheduler,stop_autonomous,stop_scheduler}.sh` → `src/tau_coding/scripts/`
- Move: `tau_cli/tau-cli-install.cmd`, `tau_cli/tau_cli.cmd` → `src/tau_coding/scripts/`
- Rename: `tests/test_core_paths.py` → `tests/test_tau_coding_paths.py`
- Delete after moves: `core/`, `tau_cli/`, `reflect/`
- Modify: `.gitignore`, `pyproject.toml`, `tau`, `tau.cmd`
- Modify: `src/tau_ai/keys.py`, `src/tau_ai/transport.py`
- Modify: `src/tau_agent/handler.py`, `src/tau_agent/tools/code_run.py`, `src/tau_agent/tools/utils.py`
- Modify: `memory/email_config.py`, `memory/email_send.py`
- Modify: `apps/common/acp_bridge.py`, `apps/common/chatapp_common.py`
- Modify: `apps/gui/app.py`, `apps/hub/hub.pyw`, `apps/hub/launch.pyw`
- Modify: `apps/im/dingtalk.py`, `apps/im/feishu.py`, `apps/im/qq.py`
- Modify: `apps/im/telegram.py`, `apps/im/wechat.py`, `apps/im/wecom.py`
- Modify: `apps/pet/app.py`, `apps/pet/bridge.py`, `apps/tui/app.py`
- Modify: `apps/web/conductor.py`, `apps/web/streamlit/app.py`
- Modify: `apps/web/streamlit/app_v2.py`, `apps/web/streamlit/app_v3.py`, `apps/web/streamlit/app_v4.py`
- Modify: `scripts/smoke_email_send.py`, `scripts/smoke_packaging.py`, `scripts/smoke_tau_ai.py`
- Modify: `tests/test_taukey_path.py`

**Interfaces:**
- Consumes: current Tau runtime, CLI registry, reflect protocol, `TAU_HOME`, `tau_ai`, and `tau_agent`.
- Produces: `tau_coding.cli:main`, `python -m tau_coding`, `python -m tau_coding.taumain`, `tau_coding.paths`, `tau_coding.reflect.*`, `_load_reflect(target, current=None) -> tuple[module, str]`, and packaged launcher scripts.

- [ ] **Step 1: Add the failing package-boundary test**

Create `tests/test_tau_coding_package.py`:

```python
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def find_spec(name):
    try:
        return importlib.util.find_spec(name)
    except ModuleNotFoundError:
        return None

class TestTauCodingPackage(unittest.TestCase):
    def test_new_modules_have_specs(self):
        modules = (
            "tau_coding.paths", "tau_coding.taumain", "tau_coding.cli",
            "tau_coding.reflect.autonomous", "tau_coding.reflect.goal_mode",
            "tau_coding.reflect.scheduler",
            "tau_coding.reflect.agent_team_worker",
        )
        for module in modules:
            with self.subTest(module=module):
                self.assertIsNotNone(find_spec(module))

    def test_old_packages_are_removed(self):
        for package in ("core", "tau_cli", "reflect"):
            with self.subTest(package=package):
                self.assertIsNone(find_spec(package))

    def test_console_entry_uses_tau_coding(self):
        text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('tau = "tau_coding.cli:main"', text)
        self.assertNotIn('tau = "tau_cli.cli:main"', text)

    def test_package_import_is_lightweight(self):
        code = ("import sys,tau_coding; "
                "assert 'tau_coding.taumain' not in sys.modules; "
                "assert 'tau_ai' not in sys.modules; "
                "assert 'tau_agent' not in sys.modules")
        result = subprocess.run([sys.executable, "-c", code],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_reflect_module_target_resolves(self):
        from tau_coding.taumain import _load_reflect
        module, source = _load_reflect("tau_coding.reflect.autonomous")
        self.assertEqual(module.__name__, "tau_coding.reflect.autonomous")
        self.assertEqual(Path(source).name, "autonomous.py")

    def test_reflect_file_target_resolves(self):
        from tau_coding.taumain import _load_reflect
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "custom_reflect.py"
            script.write_text("INTERVAL=1\nONCE=True\ndef check(): return None\n",
                              encoding="utf-8")
            module, source = _load_reflect(str(script))
        self.assertTrue(module.ONCE)
        self.assertEqual(Path(source), script.resolve())

    def test_launcher_scripts_are_package_files(self):
        scripts = ROOT / "src" / "tau_coding" / "scripts"
        expected = {"start.sh", "start_autonomous.sh", "start_scheduler.sh",
                    "stop_autonomous.sh", "stop_scheduler.sh",
                    "tau-cli-install.cmd", "tau_cli.cmd"}
        actual = {p.name for p in scripts.iterdir()
                  if p.suffix in {".sh", ".cmd"}}
        self.assertEqual(actual, expected)
```

- [ ] **Step 2: Verify the red state**

Run:

```bash
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python -m unittest tests.test_tau_coding_package -v
```

Expected: requirement failures because `tau_coding` is absent, all old packages exist, and the console target is old. Fix syntax/discovery errors before proceeding.

- [ ] **Step 3: Snapshot the overlapping user script and move files**

Run:

```bash
cp tau_cli/start_scheduler.sh /tmp/tau-coding-start_scheduler.before.sh
mkdir -p src/tau_coding/commands src/tau_coding/reflect src/tau_coding/scripts
mv core/__init__.py src/tau_coding/__init__.py
mv core/paths.py core/taumain.py src/tau_coding/
mv tau_cli/__main__.py tau_cli/cli.py src/tau_coding/
mv tau_cli/commands/*.py src/tau_coding/commands/
mv reflect/*.py src/tau_coding/reflect/
mv tau_cli/*.sh tau_cli/*.cmd src/tau_coding/scripts/
for name in autonomous.log autonomous.pid scheduler.log scheduler.pid; do
    if [ -e "tau_cli/$name" ]; then
        mv "tau_cli/$name" "src/tau_coding/scripts/$name"
    fi
done
rm -f core/.DS_Store tau_cli/.DS_Store reflect/.DS_Store
rmdir tau_cli/commands core tau_cli reflect
```

Expected: ignored PID/log contents survive under the new scripts directory and no old top-level directory remains.

- [ ] **Step 4: Establish the package marker and src-layout path anchor**

Set `src/tau_coding/__init__.py` to:

```python
"""Tau application composition and command package."""
```

Set `src/tau_coding/__main__.py` to:

```python
"""Run the Tau command dispatcher with ``python -m tau_coding``."""
from .cli import main

if __name__ == "__main__":
    main()
```

In `src/tau_coding/paths.py`, retain all constants and use:

```python
TAU_HOME = Path(os.environ.get("TAU_HOME")
                or Path(__file__).resolve().parents[2])
```

Rename `tests/test_core_paths.py` to `tests/test_tau_coding_paths.py`, rename
the class to `TestTauCodingPaths`, and replace both old imports with:

```python
from tau_coding import paths
```

- [ ] **Step 5: Correct CLI imports and repository launch roots**

In `src/tau_coding/cli.py`, update its documentation and use:

```python
from .commands import _launchers as _launchers_mod
from .commands import run, list as list_cmd, status as status_cmd, update as update_cmd
```

Set `src/tau_coding/commands/__init__.py` to:

```python
"""Command implementations used by :mod:`tau_coding.cli`."""
```

In `src/tau_coding/commands/_common.py`, use:

```python
from tau_coding.paths import TAU_HOME

PROJECT_DIR = str(TAU_HOME)

def _reflect():
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "reflect")
```

Retain `_apps()`, placeholder expansion, subprocess waiting, and interrupt
behavior. In `_launchers.py`, change the CLI command only:

```python
"cmd": ["python", "-m", "tau_coding.taumain"],
```

Update `tau_cli` documentation strings to `tau_coding`. In `commands/run.py`,
retain the lazy import and change it to:

```python
from tau_coding.taumain import Tau
```

- [ ] **Step 6: Add module/file reflect resolution**

Add `import importlib` and `import importlib.util` to
`src/tau_coding/taumain.py`, then add this helper before `class Tau`:

```python
def _load_reflect(target, current=None):
    if os.path.isfile(target):
        spec = importlib.util.spec_from_file_location("reflect_script", target)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load reflect script: {target}")
        module = current or importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    else:
        module = importlib.reload(current) if current else importlib.import_module(target)
    source = getattr(module, "__file__", None)
    if not source:
        raise ImportError(f"Reflect target has no source file: {target}")
    return module, os.path.abspath(source)
```

Change background respawning to module execution without duplicating
`--nobg`:

```python
cmd = [sys.executable, "-m", "tau_coding.taumain"] + [
    arg for arg in sys.argv[1:] if arg != "--nobg"
] + ["--nobg"]
p = subprocess.Popen(
    cmd,
    cwd=str(TAU_HOME),
    creationflags=0x08000000 if platform.system() == "Windows" else 0,
    stdout=open(os.path.join(d, "stdout.log"), "w", encoding="utf-8"),
    stderr=open(os.path.join(d, "stderr.log"), "w", encoding="utf-8"),
)
```

Delete the now-obsolete `script_dir = str(TAU_HOME / "core")` assignment.

Replace initial load, mtime, and hot reload with:

```python
mod, reflect_path = _load_reflect(args.reflect)
if hasattr(mod, "init"):
    mod.init(_reflect_args)
_mt = os.path.getmtime(reflect_path)

if os.path.getmtime(reflect_path) != _mt:
    try:
        mod, reflect_path = _load_reflect(args.reflect, mod)
        _mt = os.path.getmtime(reflect_path)
        if hasattr(mod, "init"):
            mod.init(_reflect_args)
        print("[Reflect] reloaded")
    except Exception as e:
        print(f"[Reflect] reload error: {e}")
```

Use `reflect_path` for the log stem:

```python
script_name = os.path.splitext(os.path.basename(reflect_path))[0]
```

Keep `init`, `check`, `on_done`, `INTERVAL`, `ONCE`, and all current local
error boundaries unchanged.

- [ ] **Step 7: Correct built-in reflect paths**

In `src/tau_coding/reflect/scheduler.py`, use:

```python
from tau_coding.paths import SCHE_TASKS, TEMP, MEMORY
```

In `src/tau_coding/reflect/goal_mode.py`, use:

```python
from tau_coding.paths import TAU_HOME, TEMP
```

Replace only `init()` path resolution with:

```python
def init(a):
    global STATE_FILE
    STATE_FILE = (a.get("goal_state") or os.environ.get("GOAL_STATE")
                  or str(TEMP / "goal_state.json"))
    if not os.path.isabs(STATE_FILE):
        STATE_FILE = str(TAU_HOME / STATE_FILE)
```

Retain the module-local location for `agent_team_setting.json`; change no
prompt, interval, state transition, scheduler format, or network behavior.

- [ ] **Step 8: Switch every active Python consumer**

Apply these exact module-prefix substitutions to every Python consumer named
in this task's **Files** block:

```text
core.paths       → tau_coding.paths
core.taumain     → tau_coding.taumain
```

In `tests/test_taukey_path.py`, delete/reload `tau_coding.paths` instead of
`core.paths`, import `TAU` and `TAUKEY_PATH` from `tau_coding.paths`, and
update its comment. Update `scripts/smoke_tau_ai.py` and
`scripts/smoke_email_send.py` the same way.

Set `scripts/smoke_packaging.py` to import this exact boundary:

```python
TOPLEVEL = ["tau_coding", "tau_coding.paths", "tau_coding.taumain",
            "tau_coding.cli", "tau_coding.reflect.scheduler",
            "tau_agent", "tau_agent.plugins.hooks", "tau_ai",
            "TMWebDriver", "TMWebDriver.simphtml", "memory.email_config"]
```

- [ ] **Step 9: Switch Hub reflect discovery and scheduler launch**

In `apps/hub/hub.pyw`, add `pkgutil`, import the package search path without
importing reflect implementations, and replace only built-in reflect discovery:

```python
from tau_coding.reflect import __path__ as REFLECT_PATH

def discover_services():
    services = []
    excludes = {"goal_mode"}
    modules = sorted(info.name for info in pkgutil.iter_modules(REFLECT_PATH))
    for name in modules:
        if not name.startswith("_") and name not in excludes:
            target = f"tau_coding.reflect.{name}"
            services.append({
                "name": target,
                "cmd": [sys.executable, "-m", "tau_coding.taumain",
                        "--reflect", target],
            })
```

Retain the existing application discovery after this block. In
`apps/hub/launch.pyw`, use:

```python
scheduler_proc = subprocess.Popen(
    [sys.executable, "-m", "tau_coding.taumain", "--reflect",
     "tau_coding.reflect.scheduler", "--llm_no", str(args.llm_no)],
    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
)
```

- [ ] **Step 10: Switch package configuration and executable scripts**

Use this package configuration and entry point in `pyproject.toml`:

```toml
[tool.setuptools.packages.find]
where = [".", "src"]
include = ["memory*", "TMWebDriver*", "tau_ai*", "tau_agent*", "tau_coding*"]
exclude = ["apps*", "tests*", "scripts*", "docs*", "assets*", "sche_tasks*", "temp*"]
namespaces = false

[tool.setuptools.package-data]
tau_ai = ["taukey.json"]
tau_coding = ["scripts/*.sh", "scripts/*.cmd"]

[project.scripts]
tau = "tau_coding.cli:main"
```

Update the base-dependency comment to the three `src` packages. Set root
`tau` to:

```bash
#!/usr/bin/env bash
cd "$(dirname "$0")"
exec python -m tau_coding "$@"
```

Make root `tau.cmd` and moved `tau_cli.cmd` invoke:

```bat
python -m tau_coding %*
```

Retain root `tau.cmd`'s `cd`; make both moved cmd scripts reach the repository
root with `%~dp0..\..\..`. In `start_autonomous.sh`, use:

```bash
nohup python3 -u -m tau_coding.taumain \
  --reflect tau_coding.reflect.autonomous \
  > autonomous.log 2>&1 & echo $! > autonomous.pid
```

In the user's moved scheduler script, change exactly:

```bash
MODULE="tau_coding.taumain"
REFLECT_MODULE="tau_coding.reflect.scheduler"
```

Make moved `start.sh` resolve and `cd` to the repository root three parents
above its directory before running Streamlit. Stop scripts retain current PID
behavior. Remove the obsolete `.gitignore` `reflect/*` block and update its
root-script comment from `tau_cli/` to `src/tau_coding/scripts/`.

- [ ] **Step 11: Verify scheduler preservation**

Run:

```bash
diff -u /tmp/tau-coding-start_scheduler.before.sh src/tau_coding/scripts/start_scheduler.sh
```

Expected: exactly the `MODULE` and `REFLECT_MODULE` assignments differ.

- [ ] **Step 12: Refresh installation and verify green**

Run:

```bash
UV_CACHE_DIR=/tmp/tau-uv-cache uv pip install --no-deps -e .
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python -m unittest tests.test_tau_coding_package -v
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python -m unittest discover -s tests -v
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python scripts/smoke_tau.py
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python scripts/smoke_tau_ai.py
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python scripts/smoke_packaging.py
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python -m tau_coding --help
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python -m tau_coding.taumain --help
```

Expected: 7 boundary tests and 27 total tests pass; all smoke scripts print
`[SMOKE-OK]`; both help commands exit 0 without starting a task.

- [ ] **Step 13: Check and commit the atomic runtime migration**

Run:

```bash
test ! -e core
test ! -e tau_cli
test ! -e reflect
git diff --check
git status --short
git diff --stat
```

Stage the runtime move, consumers, tests, and deleted tracked paths, then run
`git diff --cached --check` and commit:

```bash
git add .gitignore pyproject.toml tau tau.cmd src/tau_coding src/tau_ai \
  src/tau_agent apps memory/email_config.py memory/email_send.py \
  scripts/smoke_email_send.py scripts/smoke_packaging.py \
  scripts/smoke_tau_ai.py tests/test_tau_coding_package.py \
  tests/test_tau_coding_paths.py tests/test_taukey_path.py
git add -A -- core tau_cli reflect tests/test_core_paths.py
git diff --cached --check
git diff --cached --stat
git commit -m "refactor: move coding runtime to tau_coding"
```

Do not force-add ignored PID/log files.

---

### Task 2: Update Current Architecture and Operating Instructions

**Files:**
- Modify: `README.md`
- Modify: `docs/installation.md`
- Modify: `docs/installation_zh.md`
- Modify: `memory/scheduled_task_sop.md`
- Modify: `memory/goal_mode_sop.md`
- Modify: `memory/goal_hive_sop.md`
- Modify: `assets/template/global_mem_insight_template.txt`
- Modify: `assets/template/global_mem_insight_template_en.txt`

**Interfaces:**
- Consumes: the hard-cut package and entry points from Task 1.
- Produces: current user, installer, memory, scheduling, goal, and architecture instructions using only supported paths.

- [ ] **Step 1: Update README startup and architecture**

Use:

```markdown
通过 `tau` 命令(等价于 `python -m tau_coding`)选择前端:

tau cli        # CLI 对话,最轻量(tau_coding.taumain)
```

Replace the architecture rows for `core`, `src`, `reflect`, and `tau_cli`
with one package row:

```text
├── src/          # 可安装包:tau_coding(入口 · CLI · reflect) · tau_agent · tau_ai
```

Retain the existing `apps`, `memory`, `TMWebDriver`, `sche_tasks`, `docs`, and
`assets` rows.

- [ ] **Step 2: Update installation conflict guidance**

In `docs/installation.md`, use:

```markdown
- For code such as `src/tau_coding/*`, `src/tau_agent/*`, `src/tau_ai/*`,
  `apps/*`, and `TMWebDriver/*`: usually prefer upstream unless the user says
  otherwise.
```

In `docs/installation_zh.md`, use:

```markdown
- `src/tau_coding/*`、`src/tau_agent/*`、`src/tau_ai/*`、`apps/*`、
  `TMWebDriver/*` 等代码：通常 upstream 优先，除非用户另有说明。
```

- [ ] **Step 3: Update scheduler and goal SOP commands**

Identify the scheduled-task poller as `tau_coding.reflect.scheduler`. Replace
the three Goal Mode commands with:

```bat
start /b python -m tau_coding.taumain --reflect tau_coding.reflect.goal_mode
set GOAL_STATE=temp/goal_xxx.json && start /b python -m tau_coding.taumain --reflect tau_coding.reflect.goal_mode
set GOAL_STATE=temp/goal_xxx.json && start /b python -m tau_coding.taumain --reflect tau_coding.reflect.goal_mode --llm_no 1
```

Replace the Goal Hive worker command with:

```text
start /b python -m tau_coding.taumain --reflect tau_coding.reflect.agent_team_worker --base_url http://127.0.0.1:<PORT> --board_key <BOARD_KEY> --name hive-worker-1
```

Do not change prompts, budget rules, worker limits, or process guidance.

- [ ] **Step 4: Update generated memory templates**

Use these exact hints:

```text
watchdog/反射:python -m tau_coding.taumain --reflect tau_coding.reflect.<name>
watchdog/reflect: python -m tau_coding.taumain --reflect tau_coding.reflect.<name>
```

Do not edit ignored user state in `memory/global_mem_insight.txt`.

- [ ] **Step 5: Verify current references and commit**

Run:

```bash
rg -n "from core\.|import core\.|core\.taumain|core\.paths|python -m tau_cli|tau_cli/|--reflect reflect/|<CodeRoot>/reflect/|├── (core|reflect|tau_cli)/" --glob '!docs/superpowers/**' --glob '!docs/SETUP_EMAIL.md' .
git diff --check -- README.md docs memory assets/template
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python -m unittest discover -s tests -v
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python scripts/smoke_packaging.py
```

Expected: search prints nothing; 27 tests pass; the smoke prints
`[SMOKE-OK]`. `docs/SETUP_EMAIL.md` stays excluded because its two old paths
explicitly describe an already removed v1 tool.

Stage only the eight current-reference files, run
`git diff --cached --check`, and commit:

```bash
git add README.md docs/installation.md docs/installation_zh.md \
  memory/scheduled_task_sop.md memory/goal_mode_sop.md \
  memory/goal_hive_sop.md assets/template/global_mem_insight_template.txt \
  assets/template/global_mem_insight_template_en.txt
git diff --cached --check
git commit -m "docs: update tau_coding package references"
```

---

### Task 3: Verify the Distribution Boundary and Final State

**Files:**
- Verify only: repository, editable installation, wheel, committed diff

**Interfaces:**
- Consumes: Tasks 1–2.
- Produces: fresh evidence that source, CLI, reflect, packaging, documentation, and scheduler preservation satisfy the design.

- [ ] **Step 1: Compile the migrated package**

Run:

```bash
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python -m compileall -q src/tau_coding
printf "%s\n" "compileall: PASS"
```

Expected: exit 0 and `compileall: PASS`.

- [ ] **Step 2: Build and inspect the wheel**

Run:

```bash
rm -rf /tmp/tau-coding-wheel
UV_CACHE_DIR=/tmp/tau-uv-cache uv build --wheel --out-dir /tmp/tau-coding-wheel
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python -c "import glob,zipfile; wheels=glob.glob('/tmp/tau-coding-wheel/*.whl'); assert len(wheels)==1,wheels; names=set(zipfile.ZipFile(wheels[0]).namelist()); required={'tau_coding/__init__.py','tau_coding/__main__.py','tau_coding/taumain.py','tau_coding/paths.py','tau_coding/cli.py','tau_coding/reflect/scheduler.py','tau_coding/scripts/start_scheduler.sh','tau_coding/scripts/tau_cli.cmd'}; assert required <= names,required-names; assert not any(n.startswith(('core/','tau_cli/','reflect/')) for n in names); print('tau_coding wheel boundary: PASS')"
```

Expected: build succeeds and inspection prints
`tau_coding wheel boundary: PASS`.

- [ ] **Step 3: Run complete fresh verification**

Run:

```bash
UV_CACHE_DIR=/tmp/tau-uv-cache uv pip install --no-deps -e .
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python -m unittest discover -s tests -v
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python scripts/smoke_tau.py
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python scripts/smoke_tau_ai.py
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python scripts/smoke_packaging.py
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python -m tau_coding --help
UV_CACHE_DIR=/tmp/tau-uv-cache uv run --no-sync python -m tau_coding.taumain --help
diff -u /tmp/tau-coding-start_scheduler.before.sh src/tau_coding/scripts/start_scheduler.sh
git diff --check HEAD~2..HEAD
git status --short
```

Expected: 27 tests pass; smoke and help commands exit 0; scheduler diff has
only two approved target assignments; committed whitespace check is clean;
status has no tracked modifications. Ignored moved PID/log files may remain.

- [ ] **Step 4: Review requirements before reporting completion**

Confirm explicitly:

```text
[ ] src/tau_coding contains core runtime, CLI, commands, reflect, and scripts
[ ] core, tau_cli, and reflect do not exist and have no import specs
[ ] tau and python -m tau_coding share tau_coding.cli:main
[ ] built-in reflect uses module names; custom file paths are tested
[ ] TAU_HOME default and override tests pass
[ ] scheduler user work differs only at two approved targets
[ ] active code and current instructions contain no removed path
[ ] wheel contains tau_coding and scripts, with no old package members
[ ] no dependency or unrelated feature change was introduced
```

Do not create another commit unless verification reveals a required fix. If
it does, return to a failing focused test before changing production code.
