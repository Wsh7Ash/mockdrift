# Contributing

## Setup

```shell
python -m venv .venv
source .venv/bin/activate      # Windows: .venv/Scripts/activate
pip install -e ".[dev]"
```

## Checks

```shell
python -m pytest tests -q
python -m compileall -q src
python scripts/demo.py
```

`scripts/demo.py` captures real CLI runs into `results/`; if its output changes,
update `RESULTS.md` in the same pull request.

## Adding a check

1. Add the code and severity in `src/mockdrift/analyze.py`.
2. Make sure the message includes the file, line, target and real signature.
3. Add a fixture case that must produce it and one that must not.
4. Update `docs/USAGE.md` and `README.md` if the vocabulary changes.

## Style

- Standard library only at runtime.
- Never import or execute the analysed code.
- Deterministic output; sorted collections, no timestamps.
- Prefer skipping an ambiguous case with a note over guessing.
