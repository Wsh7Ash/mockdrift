# mockdrift

Check that your mocks are called the way the real functions are defined — before
the test runs, without importing anything.

```text
$ mockdrift check fixtures/app
ERROR   unknown-keyword           tests/test_billing.py:15
  mock_charge(1, 500, currency='eur', timeout=3) passes unknown keyword(s) timeout
  to charge(customer_id, amount_cents, *, currency=..., idempotency_key=...)
```

## The problem

A `MagicMock` accepts any call. That is useful while writing a test and dangerous
afterwards: when `send(to, subject)` grows a required `*, channel` parameter, a
test calling `mock_send(to, subject)` keeps passing, `assert_called_with` agrees
with the mock, and production raises `TypeError` after deploy. Renaming the
patched function is worse — the patch replaces a name nobody reads, so the test
runs against the real implementation and still goes green.

`autospec=True` closes part of this, but only for patches that opt in, and it
cannot tell you that a target no longer exists.

mockdrift resolves each patch target to its real definition in your repository
and compares the calls your test makes against that signature:

1. Walk the source tree and build a symbol table (functions, classes, methods,
   assignments).
2. Read each test file's imports and resolve `patch("a.b.c")`,
   `patch.object(Cls, "method")`, `mock.patch`, `mocker.patch`, decorators,
   `with ... as` aliases and `.start()` assignments.
3. Check calls and `assert_called_*_with` shapes: positional count, keyword
   names, required positional and required keyword-only parameters.
4. Report `stale-target` for a renamed or deleted internal symbol, and stay quiet
   about third-party targets it cannot see.

## Features

- Import-aware target resolution, including `import x as y` and
  `from x import y as z`.
- Decorator, context-manager and assignment aliases, with ambiguity detection.
- `patch.object(Cls, "method")` support, with the receiver dropped from the
  signature.
- Checks both the mock call and the assertion helpers
  (`assert_called_with`, `assert_called_once_with`, `assert_any_call`,
  `assert_has_calls`).
- Distinguishes `missing` (internal module resolved, attribute gone) from
  `external` (outside this repository) so the gate is honest.
- `--show-ok` inventory of every patch site and how it resolved.
- Text and JSON output, deterministic ordering, `--fail-on` gate.
- Standard library only; never imports or executes your code.

## Quick start

```shell
git clone https://github.com/Wsh7Ash/mockdrift.git
cd mockdrift
PYTHONPATH=src python -m mockdrift check fixtures/app --show-ok
```

Observed output (see `results/demo.txt`):

```text
mockdrift - mock calls checked against the real definitions
root: fixtures/app
modules: 4, patch sites: 11, checked calls: 11

ERROR   unknown-keyword           tests/test_billing.py:15
  mock_charge(1, 500, currency='eur', timeout=3) passes unknown keyword(s) timeout to charge(customer_id, amount_cents, *, currency=..., idempotency_key=...)
  fix: align the test with the real signature; a loose mock accepts calls production rejects

ERROR   too-many-arguments        tests/test_billing.py:20
  mock_charge(1, 500, 9) passes 3 positional argument(s), but charge(customer_id, amount_cents, *, currency=..., idempotency_key=...) accepts 2

ERROR   stale-target              tests/test_billing.py:23
  patch target 'app.billing.missing_symbol' does not resolve: 'missing_symbol' is not defined in app.billing; available: InvoiceGateway, charge, log_event, schedule

ERROR   unknown-keyword           tests/test_billing.py:35
  mock_send(7, approve=True) passes unknown keyword(s) approve to send(invoice_id, *, dry_run=...)

WARN    missing-required-argument tests/test_billing.py:30
  mock_charge(1) omits required argument(s) amount_cents from charge(customer_id, amount_cents, *, currency=..., idempotency_key=...)

WARN    missing-required-argument tests/test_billing.py:45
  mock_schedule('backup') omits required argument(s) at from schedule(job, *, at)

SUMMARY  4 error, 2 warn, 0 info
GATE     fail-on=error -> FAIL

PATCH SITES (11)
  tests/test_billing.py:7  patch app.billing.charge [found]
  ...
  tests/test_billing.py:55  patch requests.get [external]

NOTES
  - tests/test_billing.py:55: 'requests.get' is outside this repository and was not checked
```

The clean control exits 0 with `No drift: every checked mock call matches the
real signature.`

## Install

Python 3.12+, no runtime dependencies.

```shell
python -m venv .venv
source .venv/bin/activate      # Windows: .venv/Scripts/activate
pip install -e .
mockdrift check .
```

Or without installing:

```shell
PYTHONPATH=src python -m mockdrift check .
```

## Usage

```shell
mockdrift check [ROOT] [--json] [--show-ok] [--fail-on LEVEL]
```

| Flag | Meaning |
|---|---|
| `ROOT` | repository root to scan, default `.` |
| `--json` | machine-readable report |
| `--show-ok` | list every patch site with its resolution status |
| `--fail-on` | `error` (default), `warn`, `info`, `none` |

Exit codes: `0` clean, `1` threshold reached, `2` usage or input error.

### Findings

| Code | Severity | Meaning |
|---|---|---|
| `stale-target` | error | internal module resolved, but the attribute does not exist |
| `too-many-arguments` | error | more positional arguments than the real signature accepts |
| `unknown-keyword` | error | a keyword the real signature does not accept |
| `missing-required-argument` | warn | a required positional or keyword-only parameter is omitted |

## Architecture

```text
source tree -> symbols.py (discover, parse, symbol table, resolve)
            -> analyze.py (patch sites, aliases, call checks)
            -> render.py (text | JSON) -> cli.py (gate)
```

See `docs/ARCHITECTURE.md` for the resolution rules and invariants.

## Testing

```shell
pip install -e ".[dev]"
python -m pytest tests -q     # 36 tests
python scripts/demo.py
```

## Limitations

- Only `unittest.mock`-style patching is understood; `monkeypatch.setattr` and
  dependency-injection fakes are not checked.
- Relative imports are not resolved; such targets are treated as external.
- Signature *shape* only: defaults, annotations and parameter kinds beyond
  positional/keyword-only are not compared.
- A patch name bound to two different targets in one scope is skipped with a
  note.
- Classes without `__init__` have no signature, so instantiation is not checked.

## Roadmap

- `monkeypatch.setattr` support.
- A count of sites that `autospec=True` would have protected.
- SARIF output for code scanning.

## License

MIT. See `LICENSE`.
