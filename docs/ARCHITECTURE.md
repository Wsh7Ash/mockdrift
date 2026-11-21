# Architecture

## Pipeline

```text
repository root
   │
   ├─ discover (symbols.py)
   │     walk *.py, parse, build Module{symbols}
   │     function/class/method/assignment symbols with signature shapes
   │
   ├─ per module (analyze.py)
   │     imports map: local name → dotted path
   │     scopes: module + every function
   │        patch sites: decorator, with, assignment, .start(), patch.object
   │        aliases: decorator parameter, `as` name, assignment target
   │        resolve target through imports and the symbol table
   │        check calls and assert_*_with shapes against the signature
   │
   └─ render (text | JSON) + gate exit code
```

## Modules

- **signature.py** — `from_arguments` computes the positional tuple, the number
  of required positional parameters (defaults apply to the tail), keyword-only
  names, required keyword-only names, and `*args`/`**kwargs` presence. Methods
  drop the receiver by name (`self`/`cls`).
- **symbols.py** — discovery skips virtualenvs, caches, build output, hidden
  directories and `node_modules`. `__init__.py` maps to its package name. A file
  that fails to parse becomes a note, not a crash. `resolve` finds the longest
  dotted prefix that is a module, then walks attributes; a missing attribute
  returns `missing` with the parent symbol, and no module prefix returns
  `external`.
- **analyze.py** — collects imports file-wide (last binding wins), scans each
  scope without descending into nested functions or classes (each is its own
  scope), then binds aliases. Two bindings of one name with different targets
  mark it ambiguous and its calls are skipped, with a note.
- **render.py** — findings sorted by severity, file, line, code; the text report
  includes the offending source line from `ast.unparse` and the rendered real
  signature.
- **cli.py** — `check ROOT`, `--json`, `--show-ok`, `--fail-on`.

## Invariants

- No import or execution of the analysed code.
- Deterministic: sorted discovery, sorted sites, sorted notes, stable findings.
- Every finding names a file, a line, a target and the real signature.
- Unknowns are reported (external target, ambiguous alias, unparsable file)
  rather than silently dropped.

## Error handling

- Missing root: `DiscoveryError`, exit 2.
- Unparsable file: note, file skipped, run continues.
- Missing patch argument or non-literal target: site ignored (cannot be resolved
  statically), no finding.

## Security posture

Read-only. The only file content used is the source text, and the only output is
paths, line numbers, signature shapes and unparsed test expressions.
