# Project spec — mockdrift

**Name:** mockdrift
**Category:** source-review
**Target user:** a Python developer maintaining a test suite built on
`unittest.mock`, and the reviewer who has to trust it.

## 1. Vision

A loose `MagicMock` accepts any call. That is the point of a mock, and it is also
the reason a test suite can stay green while the real function changed shape.
mockdrift resolves each patch target to its real definition in the repository and
checks how the test calls the mock against that real signature — before the test
runs, without importing or executing anything.

## 2. Target audience

- Teams whose tests patch internal functions and assert call arguments.
- Reviewers who see a patch target in a diff and cannot tell whether it still
  exists.
- Maintainers of `autospec`-less suites, where signature drift is invisible.

## 3. Problem statement

`@patch("pkg.mod.send")` replaces a name with a mock that has no signature
constraints unless `autospec=True` is used. If `send(to, subject)` later becomes
`send(to, subject, *, channel)`, tests calling `mock_send(to, subject, channel="x")`
keep passing, the mock records the call, `assert_called_with` agrees with itself,
and production raises `TypeError` on the next deploy. Renaming the target
entirely produces the same silent outcome: the patch is applied to a name nobody
reads, so the test exercises the real code without noticing.

## 4. Existing alternatives

- `unittest.mock`'s `autospec=True` / `create_autospec`: enforces the signature at
  runtime, but only for patches that opt in, and it cannot detect that a patched
  name is never used.
- `mock-inspector`: a static analyzer for mock anti-patterns (silent assertions,
  bogus assertion method names, signature-blind patches as a design smell). It
  does not resolve the patched symbol's real signature.
- pylint / pyright: no mock-target resolution.
- pytest-testmon / coverage contexts: decide selection, not call-shape validity.

## 5. Competitive differentiation

- Resolves `patch("a.b.c")`, `patch.object(Cls, "attr")`, `mock.patch`,
  `mocker.patch`, decorator and context-manager aliases to the real symbol in the
  repository, using the test file's own imports.
- Compares positional count, keyword names, required positional and required
  keyword-only parameters of the test's *call* and its
  `assert_called_*_with` assertions against that symbol.
- Reports a stale target as an error, distinguishing "this repository's module,
  renamed attribute" from "outside this repository, cannot check".
- Purely static: no imports, no fixture execution, no runtime patching.

## 6. Core functionality

1. Module discovery with a symbol table: functions, async functions, classes
   (children and `__init__`), methods (receiver dropped), assignments.
2. Import-aware resolution of patch targets: `import x`, `import x as y`,
   `from x import y`, `from x import y as z`.
3. Patch-site discovery: decorator, `with`, assignment, `.start()`, `patch.object`.
4. Alias tracking per scope, with a documented skip when one name is bound to two
   different targets.
5. Call-shape checks: `too-many-arguments`, `unknown-keyword`,
   `missing-required-argument`, plus `stale-target`.
6. Text and JSON reports, `--show-ok` site inventory, `--fail-on` gate.

## 7. Technical architecture

`symbols.py` discovers modules and resolves dotted paths. `analyze.py` scans each
scope, binds aliases and checks calls. `signature.py` turns AST arguments into a
name-only shape. `render.py` formats; `cli.py` gates. See
`docs/ARCHITECTURE.md`.

## 8. Main components

| Module | Responsibility |
|---|---|
| `signature.py` | positional/required/kwonly/varargs shape, rendering |
| `symbols.py` | discovery, symbol table, dotted resolution, parse notes |
| `analyze.py` | patch sites, aliases, call checks, findings |
| `render.py` | text and JSON |
| `cli.py` | `check` command and exit codes |

## 9. Data flow

`source tree → discover/parse → symbol table → per-scope patch sites and aliases
→ resolve targets → check calls → findings → gate`.

## 10. Dependencies

Python 3.12+ standard library (`ast`, `dataclasses`, `json`, `os`, `pathlib`).
pytest for development only.

## 11. Security considerations

Read-only analysis: no imports of the analysed code, no execution, no network.
The tool reads file contents only to parse them. Findings quote only the test's
own source line (`ast.unparse`) and the signature shape, never any runtime value.
A hostile Python file can at most cause a `SyntaxError`, which is reported as a
note and skipped.

## 12. User workflows

- `mockdrift check .` before pushing, or in CI.
- `mockdrift check . --show-ok` to see which patch targets resolved and which
  were treated as external.
- `mockdrift check . --json` for dashboards.
- Reviewing a diff: run with `--fail-on error`.

## 13. Testing strategy

- Signature table tests (defaults, positional-only, kwonly, varargs, methods).
- Discovery and resolution tests, including unparsable files and third-party
  targets.
- Analysis tests on a fixture package with marked drift and clean cases,
  including `patch.object`, `with` aliases, `*args`/`**kwargs`, and required
  keyword-only parameters.
- CLI tests for exit codes, JSON and error handling.

## 14. Definition of done

Fixture produces exactly the intended findings at the intended lines, the clean
fixture produces none, the suite passes, and the report distinguishes internal
missing targets from external ones.

## 15. Known limitations

- Only `unittest.mock`-style patch calls are recognised; dependency-injection
  fakes and `monkeypatch.setattr` are not checked.
- Relative imports (`from . import x`) are not resolved; targets that rely on them
  are treated as external.
- `assert_has_calls` is checked for the direct `call(...)` list only; arbitrary
  data-driven constructions are skipped.
- Signature shape only: default values, annotations and parameter kinds beyond
  positional/keyword-only are not compared.
- A name rebound to two different targets in one scope is skipped rather than
  guessed.
- Classes without `__init__` have no signature, so instantiation calls are not
  checked.

## 16. Future development opportunities

- `monkeypatch.setattr` and `pytest-mock` attribute assertions.
- Optional `autospec` suggestion per site, with a count of call sites that would
  have been caught.
- Scope-aware import resolution instead of file-wide mapping.
- SARIF output.
