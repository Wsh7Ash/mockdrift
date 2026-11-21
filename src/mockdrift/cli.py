"""Command line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .analyze import SEVERITY_RANK, analyze
from .render import render_json, render_text
from .symbols import DiscoveryError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mockdrift",
        description="Check mock call shapes against the real definitions they patch.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="scan a repository")
    check.add_argument("root", nargs="?", default=".", help="repository root (default: .)")
    check.add_argument("--json", action="store_true", dest="as_json", help="machine-readable report")
    check.add_argument("--show-ok", action="store_true", help="list every patch site and its resolution")
    check.add_argument(
        "--fail-on",
        default="error",
        choices=("error", "warn", "info", "none"),
        help="lowest severity that makes the command exit 1 (default: error)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command != "check":
        return 2
    try:
        report = analyze(Path(args.root))
    except DiscoveryError as exc:
        print(f"mockdrift: error: {exc}", file=sys.stderr)
        return 2

    output = (
        render_json(report, args.fail_on)
        if args.as_json
        else render_text(report, args.fail_on, args.show_ok)
    )
    sys.stdout.write(output)
    return 1 if _failed(report, args.fail_on) else 0


def _failed(report, threshold: str) -> bool:
    if threshold == "none":
        return False
    return any(SEVERITY_RANK[finding.severity] >= SEVERITY_RANK[threshold] for finding in report.findings)
