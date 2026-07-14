# `core.llm` to `tau_ai` Package Migration

**Date:** 2026-07-14

## Goal

Move the complete LLM package from `core/llm/` to `src/tau_ai/` without
changing runtime behavior. Make `tau_ai` the only import path and remove
`core.llm` completely.

`tau_ai` remains part of the existing `tau` distribution. It is not an
independent SDK in this change and may continue to depend on `core.paths`.

## Chosen Approach

Use a mixed package layout:

- Keep `core/`, `tau_cli/`, `plugins/`, and the other existing top-level
  packages in place.
- Move only `core/llm/` to `src/tau_ai/`.
- Configure setuptools to discover packages from both the repository root and
  `src/`.
- Keep the documented editable-install requirement. Do not add `sys.path`
  mutation for running an uninstalled checkout.

This limits the change radius and preserves Tau's intentional top-level
structure. Moving every package under `src/` would violate that constraint;
runtime path injection would restore a path hack that the repository has
already removed.

## Package Shape

The destination preserves the existing module boundaries:

```text
src/tau_ai/
├── __init__.py
├── session.py
├── transport.py
├── convert.py
├── response.py
├── clients.py
├── keys.py
├── trim.py
├── taukey.json
└── providers/
    ├── __init__.py
    ├── claude.py
    └── openai.py
```

Public classes, functions, configuration fields, retry behavior, logging,
message conversion, context trimming, and key reloading remain unchanged.
Internal relative imports remain relative. Cross-package dependencies use
absolute imports; in particular, `tau_ai.keys` and `tau_ai.transport` may
import path constants from `core.paths`.

## Import Migration

All repository consumers switch directly to `tau_ai` or its submodules:

- `core.taumain`
- application integrations under `apps/`
- `plugins.langfuse_tracing` and `apps.common.cost_tracker`
- tests and smoke scripts
- documentation and dependency comments that name the old module

The facade continues to expose the current public API. `_load_taukeys` and
`_record_usage` remain facade exports because existing plugin consumers read
or monkey-patch them.

No compatibility package, alias, or deprecation shim remains at `core.llm`.
After migration, `import core.llm` failing is intentional.

Rename `scripts/smoke_llmcore.py` to `scripts/smoke_tau_ai.py` so the smoke
test names the new package boundary.

## Packaging and Legacy Key Data

Setuptools must include both the existing root packages and `src/tau_ai` in
editable installs and wheels. `tau_ai/taukey.json` is declared explicitly as
package data so the installed package retains the legacy key fallback.

The fallback lookup remains relative to `tau_ai.keys.__file__`. The preferred
key path remains `$TAU_HOME/.tau/taukey.py` through `core.paths.TAUKEY_PATH`.
No key format or reload semantics change.

## Failure Boundaries

Existing runtime error behavior stays intact, including HTTP retry decisions,
stream interruption output, missing-key errors, and legacy JSON fallback.
The migration adds no blanket exception handling.

Tests continue to isolate key loading with a temporary `TAU_HOME`; they must
not inspect or modify the user's real configuration. Tests locate the legacy
JSON beside the imported `tau_ai.keys` module instead of hard-coding the old
repository path.

## Verification

Record the relevant unit and smoke results before moving files. After the
migration, verify:

1. The full unit-test suite passes.
2. `scripts/smoke_tau_ai.py` passes.
3. The clean-working-directory packaging smoke test imports `tau_ai` and the
   existing Tau entry points.
4. All migrated Python files compile.
5. A wheel builds successfully.
6. The wheel contains `tau_ai/**` and `tau_ai/taukey.json` and contains no
   `core/llm/**` entries.
7. A repository-wide search finds no active `core.llm` imports or stale
   `core/llm` documentation references introduced by this migration.

Any pre-existing baseline failure is reported separately and is not presented
as a successful migration result.

## Non-goals

- Making `tau_ai` independently installable or removing its dependency on
  `core.paths`.
- Changing LLM provider behavior or public API names.
- Moving other top-level Tau packages into `src/`.
- Supporting execution from an uninstalled checkout through path injection.
- Refactoring unrelated code or modifying existing user worktree changes.
