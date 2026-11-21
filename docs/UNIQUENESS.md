# Uniqueness

## Closest existing alternatives (researched 2026-11-21)

| Tool / source | What it does | Why it does not cover this |
|---|---|---|
| `unittest.mock` `autospec=True` / `create_autospec` | makes the mock enforce the real signature at runtime | opt-in per patch; cannot detect a target that no longer exists or is never read; needs the test to run |
| `mock-inspector` | static analyzer for mock anti-patterns: silent assertions, bogus assertion method names, signature-blind patches as a design smell | pattern-based; it never resolves the patched symbol or compares a call's shape to the real signature |
| `pylint` / `pyright` / `mypy` | type and lint checking | patch targets are strings and mock objects are dynamically typed at those seams; no target resolution for `@patch("a.b")` |
| `pytest-mock` / `mock` docs on "where to patch" | guidance about namespaces | documentation, not a checkable artifact |
| `pytest-testmon`, coverage contexts | test selection from coverage | answers "which tests touch this line", not "does this call match the real signature" |

## Similarities

Like `autospec`, the tool compares calls against a real signature. Like
`mock-inspector`, it reads test files with the `ast` module and reports
file:line. It shares the patch-target vocabulary with the mock documentation.

## Meaningful differences

1. **Resolution, not pattern matching.** The target string is resolved through
   the test file's imports into the repository's symbol table, so the report can
   say *why* a target is stale and what names exist instead.
2. **Static, opt-in-free coverage.** Every patch site is checked without
   `autospec=True` and without running the suite; existing tests do not have to
   change to benefit.
3. **Assertions included.** `assert_called_with` /
   `assert_called_once_with` call shapes are checked too — that is where a stale
   expectation hides after a rename.
4. **External targets are explicit.** Third-party patch targets are reported as
   `external` and not guessed at, which keeps the gate honest.
5. **Method support.** `patch.object(Cls, "method")` resolves the class through
   the imports and checks the method signature with the receiver dropped.

## Unique mechanism

Import-aware dotted resolution over a repository-wide symbol table (longest
module prefix, then attribute walk), followed by per-scope alias binding for
decorator parameters, `with ... as` names and `.start()` assignments, then a
name-only signature comparison against the test's calls and assertion helpers.

## Why an independent repository

The reusable part is the resolver and the alias tracker, not a lint rule. It can
serve other questions (unused patches, autospec suggestions, call-site inventory)
and does not belong inside a general-purpose linter. No published tool found in
the research performs this resolution.

## Remaining originality uncertainties

- Search covered web results on 2026-11-21; a private or very recent tool may
  exist.
- `mock-inspector` lists "signature-blind patch" as a finding; if it later adds
  resolution, the overlap would grow. This project's differentiation is the
  resolved comparison and the stale-target diagnosis.
- Because the analysis is static, results depend on import style; relative
  imports reduce coverage, which is disclosed rather than papered over.
