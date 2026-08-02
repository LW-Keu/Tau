# TAU_LANG Migration Design

## Goal

Finish the language environment-variable migration by making `TAU_LANG` the
only supported variable. The legacy variable is removed without a compatibility
fallback.

## Scope

- Update every runtime language reader in `src/` and `apps/` to read only
  `TAU_LANG`.
- Preserve each reader's current default language, normalization, and English
  selection behavior.
- Keep runtime initialization locale-based when `TAU_LANG` is absent.
- Remove documentation that advertises legacy-variable compatibility.
- Check local installation scripts for the legacy variable and update them only
  if a use exists.
- Ignore the externally hosted one-line installer sources and their `ga_install`
  filenames; those sources are not part of this repository.

## Behavior

`TAU_LANG=en` continues to select English wherever it does today. Any other
value, or an unset value, continues to follow the existing reader-specific
default. Setting only the removed variable has no effect. Runtime initialization
may populate `TAU_LANG` from the system locale, but must not read or mutate the
removed variable.

## Change Strategy

Use local edits at the existing read sites instead of introducing a shared
cross-package helper. This keeps the change radius small and avoids coupling the
frontends, agent package, and AI clients solely for environment lookup.

## Verification

- Add focused regression coverage proving the removed variable is ignored and
  `TAU_LANG` remains effective.
- Run the focused language tests and the relevant existing regression suite.
- Search tracked source, tests, documentation, and local installation scripts to
  confirm the removed variable has no literal residue.
- Run formatting or static checks applicable to the changed files.
