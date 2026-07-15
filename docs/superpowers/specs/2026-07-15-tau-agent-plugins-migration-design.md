# Top-Level Plugins to `tau_agent.plugins` Migration

**Date:** 2026-07-15

## Goal

Move the complete top-level `plugins/` package into
`src/tau_agent/plugins/` without changing hook dispatch or plugin behavior.
Make `tau_agent.plugins` the only supported namespace and remove the old
`plugins` package without a compatibility shim.

## Chosen Approach

Use a nested plugin package inside the existing `tau_agent` runtime:

```text
src/tau_agent/plugins/
├── __init__.py
├── hooks.py
└── langfuse_tracing.py
```

The hook registry and built-in Langfuse integration move together. Keeping
them in a named subpackage preserves the distinction between the Agent loop,
the extension mechanism, and individual plugins. Flattening these modules
into the `tau_agent` root would obscure that boundary; leaving concrete
plugins at the repository root would retain the split package shape this
migration is intended to remove.

## Runtime Imports

The Agent loop uses its package-local hook mechanism:

```python
from .plugins.hooks import trigger as _hook
```

`core.taumain` loads built-in plugins through the installed runtime package:

```python
from tau_agent.plugins.hooks import discover_and_load
```

The Langfuse integration imports its sibling hook registry relatively:

```python
from . import hooks
```

All other Langfuse behavior remains unchanged, including optional activation,
observation lifetimes, SSE usage extraction, and failure handling.

## Discovery Semantics

`discover_and_load()` continues to accept an optional plugin directory.

For the default call:

- The discovery directory is the directory containing `hooks.py`.
- Modules are imported as `tau_agent.plugins.<name>`.
- The loader does not mutate `sys.path`.

For an explicit `plugin_dir`:

- The directory must exist and be importable as a Python package directory.
- Its parent is added to `sys.path` if absent, preserving the existing custom
  directory mechanism.
- Modules are imported using the directory's basename as the package name.
- Custom plugins use `tau_agent.plugins.hooks` to register callbacks; the old
  `plugins.hooks` API is intentionally unsupported.

`load(name)` continues to load a built-in plugin by short name. An internal
package argument may be used by `discover_and_load(plugin_dir=...)` to retain
explicit-directory support without duplicating import logic.

Discovery order remains sorted by filename. Files beginning with `_` and
non-Python files remain ignored. Plugin import failures continue to be
reported to stderr and do not abort discovery.

## Hook Behavior and Failure Boundaries

The registry API remains unchanged:

- `register(event)` decorates and registers a callback.
- `trigger(event, ctx)` calls callbacks in registration order and threads
  dictionary return values into the next callback.
- Callback exceptions are reported to stderr without aborting later hooks.
- `unregister(event, fn)`, `clear(event=None)`, and `has(event)` retain their
  current semantics.

The migration adds no blanket exception handling and does not change the
Agent loop's existing `ImportError` fallback when the hook package is absent.

## Packaging and Documentation

Setuptools already includes `tau_agent*`, so the new nested package is
discovered automatically. Remove `plugins*` from the root-package include
list so wheels cannot retain the deleted namespace.

The clean-working-directory packaging smoke imports
`tau_agent.plugins.hooks` instead of `plugins.hooks`. Current architecture and
integration references switch to the new namespace. Historical design and
plan documents remain unchanged.

## Testing and Verification

Record the current unit and smoke baseline before moving files. Add tests
before implementation that require:

1. Hook API symbols to come from `tau_agent.plugins.hooks`.
2. `plugins`, `plugins.hooks`, and `plugins.langfuse_tracing` to have no import
   spec after migration.
3. Registration order, context threading, unregistering, clearing, and
   callback-error isolation to remain intact.
4. An explicit temporary package directory to be discovered and loaded while
   registering through `tau_agent.plugins.hooks`.

The new tests must first fail against the current namespace. After migration,
verify:

1. The full unit-test suite passes.
2. Agent and clean-working-directory packaging smokes pass.
3. The migrated modules compile.
4. A clean wheel contains `tau_agent/plugins/**` and no top-level `plugins/**`.
5. Repository-wide current-reference search finds no active `plugins.*`
   import or top-level `plugins/` architecture instruction outside intentional
   negative tests and historical migration documents.

The recorded baseline is 14 passing unit tests plus both passing smoke tests.
Any unrelated worktree modification or pre-existing build warning is reported
separately.

## Non-goals

- Designing a new plugin API or event model.
- Changing Langfuse tracing, configuration, or optional dependency behavior.
- Supporting the legacy `plugins.*` namespace.
- Adding entry-point-based plugin discovery or marketplace installation.
- Moving `core.taumain`, `tau_ai`, or other application packages.
- Modifying the user's existing `tau_cli/start_scheduler.sh` change.
