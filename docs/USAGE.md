# Usage

## Install

Python 3.12+, no runtime dependencies.

```shell
python -m venv .venv
source .venv/bin/activate      # Windows: .venv/Scripts/activate
pip install -e .
```

Or from a checkout:

```shell
PYTHONPATH=src python -m mockdrift check .
```

## Commands

```shell
mockdrift check [ROOT] [--json] [--show-ok] [--fail-on LEVEL]
```

- `ROOT` — repository root to scan, default `.`.
- `--json` — machine-readable report.
- `--show-ok` — list every patch site with its resolution status.
- `--fail-on` — `error` (default) | `warn` | `info` | `none`.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | no finding reached the threshold |
| 1 | a finding reached the threshold |
| 2 | usage or input error |

## Findings

| Code | Severity | Meaning |
|---|---|---|
| `stale-target` | error | the patch target names an internal module but the attribute does not exist |
| `too-many-arguments` | error | the call passes more positional arguments than the real signature accepts |
| `unknown-keyword` | error | the call passes a keyword the real signature does not accept |
| `missing-required-argument` | warn | the call omits a required positional or keyword-only parameter |

The message includes the real shape, e.g.
`charge(customer_id, amount_cents, *, currency=..., idempotency_key=...)`.

## What is not checked

- Targets outside the repository (`requests.get`, `builtins.open`) are reported in
  the notes as external and never guessed at.
- Relative imports are not resolved; a target that depends on them is treated as
  external.
- A name bound to two different patch targets in one scope is skipped, with a
  note.

## Using it in CI

```yaml
- name: Mock drift gate
  run: |
    pip install -e .
    mockdrift check . --fail-on error
```

Because nothing is imported, the check works on a fresh checkout without the
project's dependencies installed.
