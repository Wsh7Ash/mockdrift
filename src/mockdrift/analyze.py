"""Patch-site discovery and call-shape checks."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path

from .signature import Signature
from .symbols import Module, Symbol, discover, resolve

ASSERT_METHODS = {
    "assert_called_with",
    "assert_called_once_with",
    "assert_any_call",
    "assert_has_calls",
}

SEVERITY_RANK = {"info": 0, "warn": 1, "error": 2}

REMEDY = "align the test with the real signature; a loose mock accepts calls production rejects"


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    file: str
    line: int
    target: str
    message: str
    remedy: str = REMEDY

    def as_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "severity": self.severity,
            "file": self.file,
            "line": self.line,
            "target": self.target,
            "message": self.message,
            "remedy": self.remedy,
        }


@dataclass
class Site:
    file: str
    line: int
    label: str
    target: str
    status: str
    alias: str | None
    signature: Signature | None
    available: tuple[str, ...] = ()

    def as_dict(self, root: str | None = None) -> dict[str, object]:
        return {
            "file": self.file,
            "line": self.line,
            "label": self.label,
            "target": self.target,
            "status": self.status,
            "alias": self.alias,
            "signature": self.signature.render(self.target.rsplit(".", 1)[-1]) if self.signature else None,
        }


@dataclass
class Report:
    root: str
    module_count: int
    sites: list[Site]
    findings: list[Finding]
    notes: list[str]
    checked_calls: int

    @property
    def worst(self) -> str:
        if not self.findings:
            return "none"
        return max((finding.severity for finding in self.findings), key=lambda name: SEVERITY_RANK[name])

    def counts(self) -> dict[str, int]:
        counts = {"error": 0, "warn": 0, "info": 0}
        for finding in self.findings:
            counts[finding.severity] += 1
        return counts


def analyze(root: Path) -> Report:
    root = Path(root)
    modules, notes = discover(root)
    findings: list[Finding] = []
    sites: list[Site] = []
    checked = 0

    for module in modules.values():
        file = _relative(module.path, root)
        imports = _imports(module.tree)
        scopes: list[tuple[ast.AST, bool]] = [(module.tree, False)]
        for node in ast.walk(module.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                scopes.append((node, True))
        for scope, is_function in scopes:
            scope_sites, aliases, calls, scope_findings, scope_notes = _scan_scope(
                scope, is_function, imports, modules, file
            )
            sites.extend(scope_sites)
            findings.extend(scope_findings)
            notes.extend(scope_notes)
            checked += calls
        for site in sites:
            if site.status == "external":
                notes.append(f"{site.file}:{site.line}: '{site.target}' is outside this repository and was not checked")

    findings = _dedupe(findings)
    findings.sort(key=lambda item: (-SEVERITY_RANK[item.severity], item.file, item.line, item.code))
    sites.sort(key=lambda item: (item.file, item.line, item.target))
    notes = sorted(set(notes))
    return Report(
        root=str(root),
        module_count=len(modules),
        sites=sites,
        findings=findings,
        notes=notes,
        checked_calls=checked,
    )


def _scan_scope(
    scope: ast.AST,
    is_function: bool,
    imports: dict[str, str],
    modules: dict[str, Module],
    file: str,
) -> tuple[list[Site], dict[str, Site], int, list[Finding], list[str]]:
    sites: list[Site] = []
    findings: list[Finding] = []
    notes: list[str] = []
    bindings: dict[str, list[Site]] = {}

    if is_function:
        for decorator in getattr(scope, "decorator_list", []):
            site = _patch_site(decorator, imports, modules, file)
            if site is None:
                continue
            sites.append(site)
            if _has_replacement(decorator):
                continue
            parameter = _first_parameter(scope)
            if parameter:
                bindings.setdefault(parameter, []).append(site)

    for node in _iter_scope(getattr(scope, "body", [])):
        if isinstance(node, ast.With):
            for item in node.items:
                if not isinstance(item.context_expr, ast.Call):
                    continue
                site = _patch_site(item.context_expr, imports, modules, file)
                if site is None:
                    continue
                sites.append(site)
                if isinstance(item.optional_vars, ast.Name):
                    bindings.setdefault(item.optional_vars.id, []).append(site)
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            call = _patcher_call(node.value)
            if call is None:
                continue
            site = _patch_site(call, imports, modules, file)
            if site is None:
                continue
            sites.append(site)
            bindings.setdefault(node.targets[0].id, []).append(site)

    aliases: dict[str, Site] = {}
    for name, bound in bindings.items():
        distinct = {site.target for site in bound}
        if len(distinct) > 1:
            notes.append(f"{file}: '{name}' is bound to {len(distinct)} different patch targets; its calls were not checked")
            continue
        aliases[name] = bound[0]
    for site in sites:
        if site.status == "found" and site.signature is None:
            notes.append(f"{file}:{site.line}: '{site.target}' is not a function or class with a callable signature")

    for site in sites:
        if site.status == "missing":
            findings.append(
                Finding(
                    code="stale-target",
                    severity="error",
                    file=site.file,
                    line=site.line,
                    target=site.target,
                    message=f"patch target '{site.target}' does not resolve: {_missing_detail(site)}",
                    remedy="patch a name that exists, or update the target to the renamed symbol",
                )
            )

    checked = 0
    for node in _iter_scope(getattr(scope, "body", [])):
        if not isinstance(node, ast.Call):
            continue
        hit = _call_subject(node.func, aliases)
        if hit is None:
            continue
        kind, alias = hit
        if kind == "assert_has_calls":
            inner = _call_list(node)
            for call in inner:
                site_findings = _check(alias, call, node)
                findings.extend(site_findings)
                checked += 1
            continue
        findings.extend(_check(alias, node, node))
        checked += 1

    return sites, aliases, checked, findings, notes


def _patch_site(call: ast.AST, imports: dict[str, str], modules: dict[str, Module], file: str) -> Site | None:
    if not isinstance(call, ast.Call):
        return None
    label = _patch_kind(call.func)
    if label is None:
        return None
    if label == "patch.object":
        if len(call.args) < 2:
            return None
        base = _resolve_expr(call.args[0], imports)
        attribute = _constant_str(call.args[1])
        if not base or not attribute:
            return None
        target = f"{base}.{attribute}"
    else:
        argument = call.args[0] if call.args else _keyword(call, "target")
        target = _constant_str(argument)
        if target is None:
            return None
    status, symbol = resolve(modules, target)
    signature = symbol.signature if status == "found" and symbol is not None else None
    available = tuple(sorted(symbol.children)) if status == "missing" and symbol is not None else ()
    return Site(
        file=file,
        line=call.lineno,
        label=label,
        target=target,
        status=status,
        alias=None,
        signature=signature,
        available=available,
    )


def _check(alias: Site, call: ast.Call, report_node: ast.Call) -> list[Finding]:
    signature = alias.signature
    if signature is None:
        return []
    name = alias.target.rsplit(".", 1)[-1]
    rendered = signature.render(name)
    findings: list[Finding] = []
    source = _source(report_node)

    starred = any(isinstance(argument, ast.Starred) for argument in call.args)
    positional = len([argument for argument in call.args if not isinstance(argument, ast.Starred)])
    provided = {
        keyword.arg
        for keyword in call.keywords
        if keyword.arg is not None
    }
    has_double_star = any(keyword.arg is None for keyword in call.keywords)

    if not starred and not signature.varargs and positional > len(signature.positional):
        findings.append(
            Finding(
                code="too-many-arguments",
                severity="error",
                file=alias.file,
                line=report_node.lineno,
                target=alias.target,
                message=(
                    f"{source} passes {positional} positional argument(s), but {rendered} "
                    f"accepts {len(signature.positional)}"
                ),
            )
        )

    unknown = sorted(
        keyword
        for keyword in provided
        if keyword not in signature.positional and keyword not in signature.kwonly and not signature.varkw
    )
    if unknown:
        findings.append(
            Finding(
                code="unknown-keyword",
                severity="error",
                file=alias.file,
                line=report_node.lineno,
                target=alias.target,
                message=f"{source} passes unknown keyword(s) {', '.join(unknown)} to {rendered}",
            )
        )

    if not starred and not has_double_star:
        missing = [
            parameter
            for index, parameter in enumerate(signature.positional[: signature.required])
            if index >= positional and parameter not in provided
        ]
        missing.extend(parameter for parameter in signature.kwonly_required if parameter not in provided)
        if missing:
            findings.append(
                Finding(
                    code="missing-required-argument",
                    severity="warn",
                    file=alias.file,
                    line=report_node.lineno,
                    target=alias.target,
                    message=f"{source} omits required argument(s) {', '.join(missing)} from {rendered}",
                )
            )
    return findings


def _call_subject(func: ast.AST, aliases: dict[str, Site]) -> tuple[str, Site] | None:
    if isinstance(func, ast.Name) and func.id in aliases:
        return "call", aliases[func.id]
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id in aliases:
        if func.attr in ASSERT_METHODS:
            return func.attr, aliases[func.value.id]
    return None


def _call_list(node: ast.Call) -> list[ast.Call]:
    if not node.args:
        return []
    first = node.args[0]
    candidates: list[ast.AST] = []
    if isinstance(first, ast.List):
        candidates = list(first.elts)
    elif isinstance(first, ast.Tuple):
        candidates = list(first.elts)
    return [item for item in candidates if isinstance(item, ast.Call)]


def _patch_kind(func: ast.AST) -> str | None:
    if isinstance(func, ast.Name) and func.id == "patch":
        return "patch"
    if isinstance(func, ast.Attribute):
        if func.attr == "patch":
            return "patch"
        if func.attr == "object":
            base = func.value
            if (isinstance(base, ast.Name) and base.id == "patch") or (
                isinstance(base, ast.Attribute) and base.attr == "patch"
            ):
                return "patch.object"
    return None


def _patcher_call(value: ast.AST) -> ast.Call | None:
    if isinstance(value, ast.Call) and _patch_kind(value.func):
        return value
    if (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Attribute)
        and value.func.attr in ("start", "object")
        and isinstance(value.func.value, ast.Call)
        and _patch_kind(value.func.value.func)
    ):
        return value.func.value
    return None


def _has_replacement(decorator: ast.AST) -> bool:
    if not isinstance(decorator, ast.Call):
        return False
    return any(keyword.arg in ("new", "new_callable") for keyword in decorator.keywords)


def _first_parameter(scope: ast.AST) -> str | None:
    arguments = getattr(scope, "args", None)
    if arguments is None:
        return None
    names = [argument.arg for argument in (*arguments.posonlyargs, *arguments.args)]
    if not names:
        return None
    name = names[1] if names[0] in ("self", "cls") and len(names) > 1 else names[0]
    if name in ("self", "cls"):
        return None
    return name


def _resolve_expr(expr: ast.AST | None, imports: dict[str, str]) -> str | None:
    if isinstance(expr, ast.Name):
        return imports.get(expr.id, expr.id)
    if isinstance(expr, ast.Attribute):
        base = _resolve_expr(expr.value, imports)
        return f"{base}.{expr.attr}" if base else None
    return None


def _constant_str(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _keyword(call: ast.Call, name: str) -> ast.AST | None:
    for keyword in call.keywords:
        if keyword.arg == name:
            return keyword.value
    return None


def _imports(tree: ast.Module) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    mapping[alias.asname] = alias.name
                else:
                    head = alias.name.split(".")[0]
                    mapping[head] = head
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                continue
            for alias in node.names:
                local = alias.asname or alias.name
                mapping[local] = f"{node.module}.{alias.name}"
    return mapping


def _iter_scope(nodes: list[ast.AST]):
    for node in nodes:
        yield node
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue
        yield from _iter_scope(list(ast.iter_child_nodes(node)))


def _missing_detail(site: Site) -> str:
    if site.status != "missing":
        return "no internal module prefix"
    parent = site.target.rsplit(".", 1)[0]
    name = site.target.rsplit(".", 1)[-1]
    if site.available:
        return f"'{name}' is not defined in {parent}; available: {', '.join(site.available)}"
    return f"'{name}' is not defined in {parent}"


def _source(node: ast.AST) -> str:
    try:
        return ast.unparse(node)
    except Exception:  # pragma: no cover - unparse is stable in supported versions
        return "<call>"


def _dedupe(findings: list[Finding]) -> list[Finding]:
    seen: set[tuple[str, str, int, str]] = set()
    result: list[Finding] = []
    for finding in findings:
        key = (finding.code, finding.file, finding.line, finding.message)
        if key in seen:
            continue
        seen.add(key)
        result.append(finding)
    return result


def _relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()
