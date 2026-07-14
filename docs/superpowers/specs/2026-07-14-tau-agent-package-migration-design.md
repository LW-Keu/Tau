# `core` Agent Runtime to `tau_agent` Package Migration

**Date:** 2026-07-14

## Goal

Move the Agent loop, handler, and tool implementations from `core/` to
`src/tau_agent/` without changing runtime behavior. Make `tau_agent` the only
supported import path for these modules and remove their old `core` paths.

`tau_agent` remains part of the existing `tau` distribution. This migration
does not move `core.paths` or `core.taumain`; the new package may continue to
depend on `core.paths`.

## Chosen Approach

Use an atomic hard cut within the existing mixed package layout:

- Move only `core/agent_loop.py`, `core/handler.py`, and `core/tools/`.
- Keep the intentional top-level packages, including `core/`, in place.
- Switch every active repository consumer directly to `tau_agent`.
- Remove the migrated `core` modules without aliases or compatibility shims.
- Continue using setuptools discovery from both the repository root and
  `src/`; add `tau_agent*` to the included packages.

This keeps the change radius aligned with the requested boundary. Moving
`core.paths` or `core.taumain` would expand the migration into application
entry points and violate Tau's constraint against unnecessary top-level
reorganization.

## Package Shape

The destination preserves the existing module responsibilities:

```text
src/tau_agent/
├── __init__.py
├── agent_loop.py
├── handler.py
└── tools/
    ├── __init__.py
    ├── code_run.py
    ├── file_io.py
    ├── web.py
    └── utils.py
```

`tau_agent.__init__` remains lightweight and does not re-export implementation
symbols. Consumers import from the defining submodule, which avoids importing
the browser stack as a side effect of importing the package.

The migration preserves public classes, functions, generator behavior, tool
dispatch, error results, global driver state, subprocess behavior, file I/O,
memory formatting, and hook order. Internal imports become package-relative.
Dependencies on retained path constants use absolute imports from
`core.paths`.

## Import Migration

`core.taumain` switches to:

```python
from tau_agent.agent_loop import agent_runner_loop
from tau_agent.handler import TauHandler
from tau_agent.tools.utils import smart_format, get_global_memory, format_error, consume_file
```

The Agent smoke test imports `TauHandler` and tool functions from their new
defining modules. Active documentation and package descriptions that instruct
consumers to use `core.handler` or `core.tools` switch to `tau_agent`.

No module remains at `core.agent_loop`, `core.handler`, or `core.tools`.
Importing any of those paths after the migration failing is intentional.

## Packaging

The existing mixed-root package discovery adds `tau_agent*` alongside
`tau_ai*`. The migration adds no dependency and no package data. Editable
installs and wheels must expose both `tau_agent` and the retained root
packages.

Running an uninstalled checkout through `sys.path` mutation remains out of
scope. Verification uses the project's documented editable installation and
a clean working directory.

## Failure Boundaries

Existing exceptions and error dictionaries remain unchanged. The migration
adds no fallback imports, blanket exception handling, or silent recovery.

The module move must not alter subprocess cleanup, timeout handling, browser
initialization, file mutation semantics, hook behavior, or Agent loop exit
conditions. A failure in the new package should continue to identify the
defining `tau_agent` module in its traceback.

## Testing and Verification

Record the existing unit and smoke results before moving files. Add a package
boundary test before implementation that requires:

1. `TauHandler`, `BaseHandler`, and `StepOutcome` to come from `tau_agent`.
2. Representative tool functions to come from `tau_agent.tools`.
3. `core.agent_loop`, `core.handler`, and `core.tools` to have no import spec.

The boundary test must first fail against the current package layout. After
the migration, verify:

1. The full unit-test suite passes.
2. The Agent symbol smoke test passes through `tau_agent`.
3. The clean-working-directory packaging smoke imports `tau_agent`,
   `core.taumain`, and the existing Tau entry points.
4. All migrated Python files compile.
5. A wheel builds successfully.
6. The wheel contains `tau_agent/**` and no migrated `core` module paths.
7. A repository-wide search finds no active imports or current instructions
   for the removed paths.

The recorded baseline is 11 passing unit tests, a passing Agent symbol smoke
test, and a passing clean-working-directory packaging smoke. Any unrelated
worktree modification or pre-existing failure is reported separately.

## Non-goals

- Moving `core.paths`, `core.taumain`, or any application package.
- Changing Agent loop, handler, or tool behavior.
- Designing a facade API in `tau_agent.__init__`.
- Supporting legacy `core` imports through shims or aliases.
- Adding dependencies or changing Tau's command-line entry point.
- Editing unrelated user changes in `.gitignore`, `memory/`, `scripts/asrun`,
  `.todos/`, or `bin/`.
