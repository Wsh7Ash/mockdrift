"""Text and JSON rendering."""

from __future__ import annotations

import json

from .analyze import SEVERITY_RANK, Report


def render_text(report: Report, threshold: str, show_ok: bool = False) -> str:
    counts = report.counts()
    lines = [
        "mockdrift - mock calls checked against the real definitions",
        f"root: {report.root}",
        f"modules: {report.module_count}, patch sites: {len(report.sites)}, checked calls: {report.checked_calls}",
        "",
    ]

    if not report.findings:
        lines.append("No drift: every checked mock call matches the real signature.")
    for finding in report.findings:
        lines.append(f"{finding.severity.upper():7} {finding.code:<25} {finding.file}:{finding.line}")
        lines.append(f"  {finding.message}")
        lines.append(f"  fix: {finding.remedy}")
        lines.append("")

    summary = ", ".join(f"{counts[name]} {name}" for name in ("error", "warn", "info"))
    gate = "pass" if not _failed(report, threshold) else "FAIL"
    lines.append(f"SUMMARY  {summary}")
    lines.append(f"GATE     fail-on={threshold} -> {gate}")

    if show_ok:
        lines.append("")
        lines.append(f"PATCH SITES ({len(report.sites)})")
        for site in report.sites:
            alias = f" as {site.alias}" if site.alias else ""
            lines.append(f"  {site.file}:{site.line}  {site.label} {site.target} [{site.status}]{alias}")

    if report.notes:
        lines.append("")
        lines.append("NOTES")
        for note in report.notes:
            lines.append(f"  - {note}")

    return "\n".join(lines).rstrip() + "\n"


def render_json(report: Report, threshold: str) -> str:
    payload = {
        "root": report.root,
        "modules": report.module_count,
        "checked_calls": report.checked_calls,
        "sites": [site.as_dict() for site in report.sites],
        "findings": [finding.as_dict() for finding in report.findings],
        "summary": {
            "counts": report.counts(),
            "worst": report.worst,
            "fail_on": threshold,
            "gate": "fail" if _failed(report, threshold) else "pass",
        },
        "notes": report.notes,
    }
    return json.dumps(payload, indent=2) + "\n"


def _failed(report: Report, threshold: str) -> bool:
    if threshold == "none":
        return False
    limit = SEVERITY_RANK[threshold]
    return any(SEVERITY_RANK[finding.severity] >= limit for finding in report.findings)
