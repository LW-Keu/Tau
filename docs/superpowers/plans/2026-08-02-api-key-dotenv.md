# API Key `.tau/.env` Loading Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let `tau api` load `TAU_API_KEY` from `<TAU_HOME>/.tau/.env` while preserving an explicit process-environment override.

**Architecture:** Keep parsing at the API process boundary in `apps/api/server.py`. Resolve the file through `tau_paths.TAU`, parse only the supported key with the standard library, and pass the result into the existing `create_app` boundary.

**Tech Stack:** Python 3.10+, pathlib, pytest, FastAPI/uvicorn; no new dependency.

## Global Constraints

- The process environment takes precedence over `.tau/.env`.
- Resolve the file as `<TAU_HOME>/.tau/.env`, never relative to the caller's working directory.
- Accept unquoted, single-quoted, and double-quoted `TAU_API_KEY` values.
- Ignore blank lines, comment lines, and malformed unrelated lines.
- Refuse startup when neither source supplies a non-empty key.
- Do not generate, overwrite, log, or return the key.
- Add no dependency and do not restructure repository directories.

---

### Task 1: Load the API Key at the API Boundary

**Files:**
- Modify: `apps/api/server.py:1-18,385-392`
- Test: `tests/test_api_server.py:103-124`

**Interfaces:**
- Consumes: `tau_paths.TAU: pathlib.Path`
- Produces: `_read_env_key(path: pathlib.Path) -> str` and `load_api_key() -> str`

- [ ] **Step 1: Write failing key-resolution tests**

Add `load_api_key` to the import from `apps.api.server`, then replace and extend the startup tests with:

```python
@pytest.mark.parametrize("line", [
    "TAU_API_KEY=file-secret\n",
    "TAU_API_KEY='file-secret'\n",
    'TAU_API_KEY="file-secret"\n',
])
def test_load_api_key_from_tau_env(monkeypatch, tmp_path, line):
    tau_dir = tmp_path / ".tau"
    tau_dir.mkdir()
    (tau_dir / ".env").write_text(
        "# local API authentication\nINVALID LINE\n" + line,
        encoding="utf-8",
    )
    monkeypatch.delenv("TAU_API_KEY", raising=False)
    monkeypatch.setattr(server, "TAU", tau_dir)
    assert load_api_key() == "file-secret"


def test_process_api_key_overrides_tau_env(monkeypatch, tmp_path):
    tau_dir = tmp_path / ".tau"
    tau_dir.mkdir()
    (tau_dir / ".env").write_text(
        "TAU_API_KEY=file-secret\n", encoding="utf-8",
    )
    monkeypatch.setenv("TAU_API_KEY", "process-secret")
    monkeypatch.setattr(server, "TAU", tau_dir)
    assert load_api_key() == "process-secret"


def test_main_refuses_to_start_without_api_key(monkeypatch, tmp_path):
    monkeypatch.delenv("TAU_API_KEY", raising=False)
    monkeypatch.setattr(server, "TAU", tmp_path / ".tau")
    with pytest.raises(SystemExit) as raised:
        server.main([])
    assert raised.value.code == 2
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
uv run --with pytest --with httpx2 pytest tests/test_api_server.py::test_load_api_key_from_tau_env tests/test_api_server.py::test_process_api_key_overrides_tau_env tests/test_api_server.py::test_main_refuses_to_start_without_api_key -q
```

Expected: collection fails because `load_api_key` is not defined or importable.

- [ ] **Step 3: Implement the minimal standard-library loader**

Import the shared Tau configuration directory:

```python
from tau_paths import TAU
```

Add above `main`:

```python
def _read_env_key(path):
    if not path.is_file():
        return ""
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        name, separator, value = line.partition("=")
        if separator and name.strip() == "TAU_API_KEY":
            value = value.strip()
            if (len(value) >= 2 and value[0] == value[-1]
                    and value[0] in "'\""):
                value = value[1:-1]
            return value.strip()
    return ""


def load_api_key():
    return (os.environ.get("TAU_API_KEY", "").strip()
            or _read_env_key(TAU / ".env"))
```

Change `main` to use the loader and name the file in its actionable error:

```python
api_key = load_api_key()
if not api_key:
    parser.error(
        "TAU_API_KEY is required; set it in .tau/.env or the process environment"
    )
```

- [ ] **Step 4: Run the focused tests and verify GREEN**

Run the command from Step 2. Expected: all five parametrized/focused cases pass.

- [ ] **Step 5: Run the complete API test module**

Run:

```bash
uv run --with pytest --with httpx2 pytest tests/test_api_server.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit the runtime change**

```bash
git add apps/api/server.py tests/test_api_server.py
git diff --cached --check
git commit -m "feat: load API key from Tau env file"
```

### Task 2: Document File-Based Startup

**Files:**
- Modify: `README.md:141-157`
- Modify: `docs/superpowers/specs/2026-08-02-workbuddy-api-server-design.md:70-110`

**Interfaces:**
- Consumes: `load_api_key()` behavior from Task 1
- Produces: exact user setup instructions for `.tau/.env`

- [ ] **Step 1: Update the WorkBuddy setup example**

Replace the inline environment launch example in `README.md` with:

````markdown
安装 API 依赖，在 `.tau/.env` 中设置一个仅供本机使用的密钥，然后启动服务：

```bash
uv pip install -e ".[api]"
mkdir -p .tau
printf 'TAU_API_KEY=请替换为本机密钥\n' > .tau/.env
tau api
```
````

Keep the WorkBuddy field list, but change the Key description to:

```markdown
- API Key：与 `.tau/.env` 中的 `TAU_API_KEY` 相同
```

- [ ] **Step 2: Reconcile the design verification wording**

Ensure the design document says the process environment overrides the file and the manual smoke test starts from `.tau/.env`. Do not duplicate parser pseudocode or add another configuration source.

- [ ] **Step 3: Verify documentation and diff hygiene**

Run:

```bash
rg -n "TAU_API_KEY=.*tau api|\.tau/\.env|process environment" README.md docs/superpowers/specs/2026-08-02-workbuddy-api-server-design.md
git diff --check
```

Expected: no inline-key startup remains in the WorkBuddy instructions, both documents name `.tau/.env`, and `git diff --check` exits zero.

- [ ] **Step 4: Commit only the WorkBuddy documentation changes**

`README.md` already contains unrelated user edits. Stage only the WorkBuddy hunk, then stage the design document if it changed:

```bash
git diff -- README.md
git add -p README.md
git add docs/superpowers/specs/2026-08-02-workbuddy-api-server-design.md
git diff --cached --check
git commit -m "docs: explain API key env file"
```

At the `git add -p` prompt, accept only the hunk under `### WorkBuddy 接入`.
Before committing, inspect `git diff --cached` and confirm it contains no
unrelated README edits.

### Task 3: Verify the Real Startup Path

**Files:**
- No source changes expected.

**Interfaces:**
- Consumes: `.tau/.env` loading and `tau api --port PORT`
- Produces: runtime evidence that file-based authentication works

- [ ] **Step 1: Protect the user's configuration**

Check only whether `.tau/.env` exists. If it exists, do not overwrite it; use a temporary `TAU_HOME` checkout fixture or ask the user before changing it. If it does not exist, create it with a temporary local-only key for the smoke test.

- [ ] **Step 2: Start the API on an unused loopback port**

Run `tau api --port 8643`. Expected: uvicorn reports `http://127.0.0.1:8643` without requiring an inline environment variable.

- [ ] **Step 3: Verify authenticated model discovery**

Call `GET /v1/models` with the same temporary key. Expected:

```json
{"object":"list","data":[{"id":"tau-agent","object":"model","created":0,"owned_by":"tau"}]}
```

- [ ] **Step 4: Restore temporary configuration and run final checks**

Stop only the smoke-test process. Remove only a `.tau/.env` created by this task; never delete or rewrite a pre-existing file. Then run:

```bash
uv run --with pytest --with httpx2 pytest tests/test_api_server.py -q
git diff --check
git status --short
```

Expected: tests pass, diff check is clean, and only pre-existing user changes remain unstaged.
