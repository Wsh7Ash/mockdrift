# Changelog

## 0.1.0 — 2026-11-21

First release.

- Static symbol table: functions, async functions, classes, methods (receiver
  dropped), nested classes, module-level assignments.
- Import-aware resolution of dotted patch targets, with `external` versus
  `missing` distinction.
- Patch sites: decorator, `with ... as`, assignment, `.start()`, `patch.object`,
  `mock.patch`, `mocker.patch`.
- Alias tracking for decorator parameters, `with` names and assignment targets;
  ambiguous bindings are skipped with a note.
- Checks: `stale-target`, `too-many-arguments`, `unknown-keyword`,
  `missing-required-argument`, applied to direct calls and to
  `assert_called_with` / `assert_called_once_with` / `assert_any_call` /
  `assert_has_calls`.
- Text and JSON reports, `--show-ok`, `--fail-on` gate.
- Fixtures for a drifted suite and a clean control.
