# `tau_coding` Package Migration Design

## Goal

Move Tau's remaining application composition layer from the top-level
`core`, `tau_cli`, and `reflect` packages into one installable
`src/tau_coding` package. Make `tau_coding` the only supported import and
execution boundary for these modules without changing Agent, model, CLI,
scheduler, goal, autonomous, or team-worker behavior.

## Package Boundary

The migration creates this package:

```text
src/tau_coding/
├── __init__.py
├── __main__.py
├── taumain.py
├── paths.py
├── cli.py
├── commands/
├── reflect/
└── scripts/
```

The source mapping is exact:

| Current source | Destination |
|---|---|
| `core/taumain.py` | `src/tau_coding/taumain.py` |
| `core/paths.py` | `src/tau_coding/paths.py` |
| `tau_cli/__main__.py` | `src/tau_coding/__main__.py` |
| `tau_cli/cli.py` | `src/tau_coding/cli.py` |
| `tau_cli/commands/` | `src/tau_coding/commands/` |
| `reflect/` | `src/tau_coding/reflect/` |
| `tau_cli/*.sh` and `tau_cli/*.cmd` | `src/tau_coding/scripts/` |

`tau_coding.__init__` remains a lightweight package marker. It does not
import `Tau`, load model configuration, discover plugins, or re-export CLI or
reflect implementation symbols.

The old top-level `core`, `tau_cli`, and `reflect` packages are removed. The
migration intentionally provides no aliases, fallback imports, deprecation
modules, or compatibility shims. Importing any old package after the move must
fail.

## Dependency Direction

`tau_coding.paths` is a foundational leaf module. `tau_ai`, `tau_agent`,
`memory`, applications, and reflect implementations may import path constants
from it. It imports only the standard library.

`tau_coding.taumain` is the composition root. It imports `tau_ai` and
`tau_agent`, constructs `Tau`, and owns the task, reflect, and interactive CLI
runtime. This arrangement creates no module import cycle: consumers depend on
the leaf `tau_coding.paths` module, while only the separate
`tau_coding.taumain` module composes the runtime packages.

Application frontends import `Tau` from `tau_coding.taumain`. CLI command
modules use package-relative imports and retain the existing lazy import of
`Tau` for `tau run`, so listing and dispatching lightweight commands does not
initialize model dependencies.

## Paths

`TAU_HOME` remains the single repository-root anchor and keeps its environment
override. Without the override, `src/tau_coding/paths.py` resolves the root by
walking from the src-layout package to the repository root rather than
mistaking `src/` for the root.

The existing constants keep their names and meanings:

```text
ASSETS, MEMORY, TEMP, SCHE_TASKS, TAU, TAUKEY_PATH
```

All active imports of `core.paths` change to `tau_coding.paths`. Tests must
cover both default source-layout resolution and `TAU_HOME` override behavior.

## Execution Entry Points

The console entry point changes from `tau_cli.cli:main` to
`tau_coding.cli:main`. `python -m tau_coding` delegates to the same `main()`.
The core runtime is invoked as `python -m tau_coding.taumain`.

Subprocess launch templates use module execution for the core CLI rather than
executing `taumain.py` as a filesystem script. Background task respawning also
uses `python -m tau_coding.taumain`, preserving package-relative imports and
setting the working directory from `TAU_HOME`.

Application launchers that still require repository-only `apps/` or `assets/`
paths obtain the root from `tau_coding.paths`; they do not infer it with a
fixed number of parent-directory calls from a command module.

The shell and Windows command scripts move under `tau_coding/scripts`. Their
Tau invocations change to the new module names and their repository-relative
paths account for the src layout. The scripts are included as package data in
the wheel. Existing process, PID-file, log-file, port-check, stop, and user
prompt behavior remains unchanged.

The current uncommitted expansion of `tau_cli/start_scheduler.sh` is user work.
It must be moved intact, with only the module and reflect target adapted to the
new package. A before/after comparison must demonstrate that none of its
diagnostics or process-control behavior was lost.

## Reflect Loading

`--reflect` supports two explicit input forms:

1. A module name such as `tau_coding.reflect.scheduler`.
2. A filesystem path to a user-authored Python reflect script.

A small resolver in `tau_coding.taumain` loads the requested form and returns
the module plus its source path. The source path drives the existing mtime
hot-reload loop and log filename. Built-in scripts and launchers use module
names; arbitrary user scripts retain file-path support.

The reflect protocol remains unchanged: optional `init(args)`, required
`check()`, optional `on_done(result)`, `INTERVAL`, and `ONCE`. Initial load
errors fail immediately. Existing local recovery for reload, `check`, result
drain, and `on_done` failures remains unchanged; the migration adds no blanket
exception handling.

Built-in reflect modules move without behavioral rewrites. Repository paths
that would otherwise break under `src/tau_coding/reflect` use
`tau_coding.paths` explicitly. In particular, scheduler storage remains under
`SCHE_TASKS`, `TEMP`, and `MEMORY`, and goal state defaults under `TEMP`.

## Packaging and Current References

Setuptools discovery includes `tau_coding*` and removes `core*`, `tau_cli*`,
and `reflect*`. Package data includes the files under `tau_coding/scripts`.
No dependency or project metadata changes are required beyond the console
entry point and package configuration.

All active code, tests, scripts, templates, SOPs, README architecture trees,
and current installation documentation switch to the new paths. Historical
design and implementation records under `docs/superpowers` remain unchanged
when they accurately describe an earlier repository state.

The Hub and application launchers stop scanning a removed top-level
`reflect/` directory. Built-in reflect choices come from the
`tau_coding.reflect` package, and their subprocess commands use module names.

## Behavior and Failure Boundaries

The migration does not change:

- `Tau` construction, queues, model selection, task processing, or slash
  commands;
- Agent and model package APIs;
- CLI command names, parsing, output, or exit codes;
- scheduler timing, locking, task formats, logs, or cooldown behavior;
- goal budget state transitions and prompts;
- autonomous intervals or team-worker BBS protocol;
- foreground, background, PID, log, and stop-script semantics.

Critical import, path, reflect initial-load, and packaging failures remain
visible. The implementation must not hide an incomplete migration with
fallback imports or broad exception handling.

## Testing and Verification

The recorded pre-migration baseline on 2026-07-15 is:

- `python -m unittest discover -s tests -v`: 20 tests passed.
- `scripts/smoke_tau.py`: passed.
- `scripts/smoke_tau_ai.py`: passed.
- `scripts/smoke_packaging.py`: passed from a clean working directory.

Before moving production files, add a package-boundary test that requires:

1. `tau_coding.paths`, `tau_coding.taumain`, `tau_coding.cli`, and the four
   built-in reflect modules to have import specs.
2. `core`, `tau_cli`, and `reflect` to have no import specs.
3. the `tau` console target to be `tau_coding.cli:main`.

Run the test before implementation and confirm it fails for the missing new
package and present old packages. Add focused tests for path anchors, lazy CLI
imports, reflect module/path resolution, and package script data as their
boundaries move.

After the migration, verify:

1. The package-boundary and focused migration tests pass.
2. The full unit-test suite passes.
3. Existing Tau, Agent, AI, and clean-directory packaging smoke tests pass
   after switching their expected imports.
4. `python -m tau_coding --help` and `python -m tau_coding.taumain --help`
   succeed without starting a task.
5. All Python files under `src/tau_coding` compile.
6. A wheel builds successfully and contains `tau_coding/**`, including its
   scripts, with no `core/**`, `tau_cli/**`, or `reflect/**` members.
7. A repository-wide search finds no active import, executable command, or
   current instruction using the removed package paths.
8. `git diff --check` reports no whitespace errors.
9. The scheduler script comparison shows only relocation and new module/path
   adaptations relative to the user's uncommitted version.

## Non-goals

- Redesigning `Tau` or splitting `taumain.py`.
- Changing CLI commands or adding a new CLI framework.
- Reworking reflect protocols, scheduler formats, prompts, or timing.
- Packaging repository-only applications and assets into the wheel.
- Preserving any old import or execution path.
- Moving `tau_ai`, `tau_agent`, `memory`, `TMWebDriver`, or `apps`.
- Adding dependencies or unrelated cleanup.
