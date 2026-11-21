# Results

## Environment

- OS: Windows (win32), Git Bash
- Runtime: Python 3.14.3
- Dependency manager: none at runtime; pytest for the dev extra

## Validation performed

- install: N/A — standard library only, suite runs with `PYTHONPATH=src`
- build: PASS — `python -m compileall -q src`
- unit tests: PASS — 36 passed
- integration tests: PASS — CLI tests run the package as a subprocess with UTF-8
  pipes, covering exit codes 0/1/2, `--json` and `--show-ok`
- lint: N/A — no linter configured
- type check: N/A — no type checker configured
- demo run: PASS — `python scripts/demo.py` exited 0 with
  `expectations met: True`

## Commands executed

```shell
PYTHONPATH=src python -m pytest tests -q
python -m compileall -q src
python scripts/demo.py
```

## Observed result

```text
36 passed in 1.90s

app: exit code 1 (expected 1)
clean: exit code 0 (expected 0)
expectations met: True
```

`results/demo.txt` holds the full captured output. On `fixtures/app`:

- 4 modules, 11 patch sites, 11 checked calls;
- 4 errors: `unknown-keyword` (timeout), `too-many-arguments` (3 vs 2),
  `stale-target` (missing_symbol, with the available names listed), and
  `unknown-keyword` on the `patch.object` method (`approve` vs `dry_run`);
- 2 warnings: `missing-required-argument` for `amount_cents` and for the
  keyword-only `at`;
- `requests.get` reported as `external` in the notes, with no finding;
- the `with ... as send_mock` alias and the `*args/**kwargs` call produce no
  findings.

## Defects found while building the suite and fixed

1. **Methods were collected with `self` in the signature.** Class bodies used the
   generic collector, so every method appeared to take one extra positional
   argument and any one-argument call was flagged. Class bodies now use the
   method-aware collector, which drops the receiver.
2. **`patch.object(...)` was never recognised.** The detector only accepted
   `mock.patch.object`, where the value is an attribute chain; the plain
   `patch.object` form has a bare `patch` name as the base. Both shapes are now
   accepted, and the fixture exercises the plain form.

## Notes

- `pip install -e .` was not run here; the suite and demo run from source with
  `PYTHONPATH=src`. CI installs with `pip install -e ".[dev]"`.
- No third-party runtime code is used, so there are no third-party notices.
