# TAU_LANG-Only Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `TAU_LANG` the only environment variable that controls runtime language selection.

**Architecture:** Keep language lookup local to each existing reader and remove only the legacy fallback branch. Extend the existing migration regression scan so source, documentation, tests, and tracked local installers cannot reintroduce the removed variable.

**Tech Stack:** Python 3.10+, `unittest`/pytest, shell-based repository scans.

## Global Constraints

- Preserve every reader's current default language, normalization, and English-selection behavior.
- Do not add a shared cross-package language helper.
- Do not modify or publish the externally hosted one-line installers.
- Do not rename the external `ga_install` URLs as part of this change.
- Do not touch unrelated worktree changes.

---

### Task 1: Remove the legacy language-variable contract

**Files:**
- Modify: `tests/test_migration_regressions.py:10-30,140-160`
- Modify: `src/tau_coding/runtime.py:9-11`
- Modify: `src/tau_ai/clients.py:46,207`
- Modify: `src/tau_agent/tools/utils.py:59`
- Modify: `apps/common/review_cmd.py:27,64`
- Modify: `apps/common/btw_cmd.py:49`
- Modify: `apps/web/streamlit/app.py:33`
- Modify: `README.md:187`
- Check only: `setup/install-macos-app.sh`
- Check only: `setup/install_python_windows.bat`

**Interfaces:**
- Consumes: process environment key `TAU_LANG` and the existing system-locale initialization in `tau_coding.runtime.initialize_runtime()`.
- Produces: unchanged reader return values and prompt/template selection, controlled only by `TAU_LANG`.

- [ ] **Step 1: Write failing migration and behavior regressions**

Add a constructed legacy name and its boundary pattern to the constants in
`tests/test_migration_regressions.py` so the removed spelling is not itself left
in tracked text:

```python
LEGACY_LANGUAGE_VARIABLE = "GA" + "_LANG"

LEGACY_PATTERNS = (
    re.compile(r"(?<![\w])(?:\.\.?/)*(?:core|tau_cli)/"),
    re.compile(r"(?<![\w])(?<!tau_coding/)(?<!tau_agent/)(?:\.\.?/)*(?:reflect|plugins)/"),
    re.compile(r"(?m)^\s*(?:from|import)\s+(?:core|tau_cli|reflect|plugins)(?:[.\s]|$)"),
    re.compile(r"(?P<q>['\"])(?:core|tau_cli|reflect|plugins)(?:\.[A-Za-z_]\w*)+(?::[A-Za-z_]\w*)?(?P=q)"),
    re.compile(r"/\s*(?P<q>['\"])(?:core|tau_cli|reflect|plugins)(?P=q)"),
    re.compile(r"(?:find_spec|import_module|__import__)\(\s*['\"](?:core|tau_cli|reflect|plugins)['\"]"),
    re.compile(r"sys\.modules\[\s*['\"](?:core|tau_cli|reflect|plugins)['\"]\s*\]"),
    re.compile(rf"(?<![\w]){LEGACY_LANGUAGE_VARIABLE}(?![\w])"),
)
```

Add a real runtime behavior test to `MigrationRegressionTests`:

```python
def test_removed_language_variable_does_not_select_english(self):
    env = {**os.environ, LEGACY_LANGUAGE_VARIABLE: "en"}
    env.pop("TAU_LANG", None)
    result = subprocess.run(
        [sys.executable, "-c",
         "from tau_coding.runtime import language_suffix;"
         "assert language_suffix() == ''"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    self.assertEqual(result.returncode, 0, result.stderr)
```

In `test_taumain_import_has_no_runtime_side_effects`, replace direct references
to the removed name with the shared constructed constant:

```python
env = {**os.environ, "TAU_HOME": directory}
env.pop(LEGACY_LANGUAGE_VARIABLE, None)
env.pop("TAU_LANG", None)
code = (
    "import os,pathlib,tau_coding.taumain;"
    "root=pathlib.Path(os.environ['TAU_HOME']);"
    "assert 'TAU_LANG' not in os.environ;"
    "assert not (root/'memory').exists();"
    "assert not (root/'external').exists()"
)
```

- [ ] **Step 2: Run the new regressions and verify RED**

Run:

```bash
uv run --with pytest pytest \
  tests/test_migration_regressions.py::MigrationRegressionTests::test_active_tracked_text_has_no_legacy_boundaries \
  tests/test_migration_regressions.py::MigrationRegressionTests::test_removed_language_variable_does_not_select_english \
  -q
```

Expected: two failures. The repository scan reports the current reader and
README offenders, and the behavior subprocess exits non-zero because the old
fallback still selects the English suffix.

- [ ] **Step 3: Remove fallback reads with minimal local edits**

Use these exact lookup forms while leaving surrounding behavior unchanged:

```python
# src/tau_coding/runtime.py
def _lang():
    return os.environ.get("TAU_LANG", "")

# src/tau_ai/clients.py (both sites)
os.environ.get('TAU_LANG', '') == 'en'

# src/tau_agent/tools/utils.py
os.environ.get('TAU_LANG', '') == 'en'

# apps/common/review_cmd.py (both sites)
os.environ.get('TAU_LANG', '').strip().lower()

# apps/common/btw_cmd.py
os.environ.get('TAU_LANG', '') == 'en'

# apps/web/streamlit/app.py
LANG = os.environ.get('TAU_LANG', 'zh')
```

Replace the README language sentence with:

```markdown
启动时按系统语言自动切换中 / 英（可用 `TAU_LANG` 覆盖）。
```

Do not edit either local installation script unless the Step 6 residue scan
finds an actual use.

- [ ] **Step 4: Run the focused regressions and verify GREEN**

Run:

```bash
uv run --with pytest pytest \
  tests/test_migration_regressions.py::MigrationRegressionTests::test_active_tracked_text_has_no_legacy_boundaries \
  tests/test_migration_regressions.py::MigrationRegressionTests::test_removed_language_variable_does_not_select_english \
  -q
```

Expected: `2 passed`.

- [ ] **Step 5: Run the complete migration regression suite**

Run:

```bash
uv run --with pytest pytest tests/test_migration_regressions.py -q
```

Expected: all tests pass with zero failures.

- [ ] **Step 6: Verify residue, syntax, and diff quality**

Run:

```bash
rg -n 'GA''_LANG' README.md docs setup src apps tests
```

Expected: exit status 1 and no matches.

Run:

```bash
uv run python -m compileall -q src apps/common apps/web/streamlit tests/test_migration_regressions.py
git diff --check
```

Expected: both commands exit 0 with no output.

- [ ] **Step 7: Commit the implementation**

```bash
git add README.md \
  apps/common/btw_cmd.py \
  apps/common/review_cmd.py \
  apps/web/streamlit/app.py \
  src/tau_agent/tools/utils.py \
  src/tau_ai/clients.py \
  src/tau_coding/runtime.py \
  tests/test_migration_regressions.py
git diff --cached --check
git commit -m "refactor: finish TAU_LANG migration"
```
