#!/usr/bin/env python3
"""Capture real CLI runs for the README and RESULTS.md."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTHONIOENCODING": "utf-8"}
EXPECTED = {"app": 1, "clean": 0}


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "mockdrift", *args],
        cwd=ROOT,
        env=ENV,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def main() -> int:
    cases = [
        ("app", ("check", "fixtures/app", "--show-ok")),
        ("clean", ("check", "fixtures/clean")),
    ]
    chunks = ["mockdrift demo - captured CLI output", ""]
    gates: list[str] = []
    for name, args in cases:
        proc = run(*args)
        chunks.append("$ mockdrift " + " ".join(args[1:]))
        chunks.append(proc.stdout.rstrip())
        if proc.stderr.strip():
            chunks.append("stderr: " + proc.stderr.strip())
        chunks.append(f"exit code: {proc.returncode}")
        chunks.append("")
        gates.append(f"{name}: exit code {proc.returncode} (expected {EXPECTED[name]})")

    payload = json.loads(run("check", "fixtures/app", "--json").stdout)
    chunks.append("json summary: " + json.dumps(payload["summary"], sort_keys=True))
    chunks.append("json finding codes: " + ", ".join(item["code"] for item in payload["findings"]))
    chunks.append("json checked calls: " + str(payload["checked_calls"]))

    results = ROOT / "results"
    results.mkdir(exist_ok=True)
    (results / "demo.txt").write_text("\n".join(chunks) + "\n", encoding="utf-8")

    ok = all(
        int(line.split("exit code ")[1].split()[0]) == EXPECTED[line.split(":")[0]] for line in gates
    )
    (results / "gate.txt").write_text("\n".join(gates) + f"\nexpectations met: {ok}\n", encoding="utf-8")
    print("\n".join(chunks))
    print("\n".join(gates))
    print("expectations met:", ok)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
