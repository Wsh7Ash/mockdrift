"""Module discovery and the symbol table used to resolve patch targets."""

from __future__ import annotations

import ast
import os
from dataclasses import dataclass, field
from pathlib import Path

from .signature import Signature, from_arguments

SKIP_DIRS = {
    "__pycache__",
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "build",
    "dist",
    "node_modules",
    ".tox",
    ".pytest_cache",
    ".mypy_cache",
    "site-packages",
}


class DiscoveryError(ValueError):
    """Raised when the root cannot be scanned."""


@dataclass
class Symbol:
    qualname: str
    kind: str  # module | function | class | assignment
    signature: Signature | None = None
    children: dict[str, "Symbol"] = field(default_factory=dict)


@dataclass
class Module:
    name: str
    path: Path
    tree: ast.Module
    symbols: dict[str, Symbol]


def discover(root: Path) -> tuple[dict[str, Module], list[str]]:
    """Parse every Python module under `root`, keyed by dotted module name."""
    root = Path(root)
    if not root.is_dir():
        raise DiscoveryError(f"root directory not found: {root}")

    modules: dict[str, Module] = {}
    notes: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(name for name in dirnames if name not in SKIP_DIRS and not name.startswith("."))
        for filename in sorted(filenames):
            if not filename.endswith(".py"):
                continue
            path = Path(dirpath) / filename
            relative = path.relative_to(root).with_suffix("")
            parts = list(relative.parts)
            if parts and parts[-1] == "__init__":
                parts = parts[:-1]
            module_name = ".".join(parts) if parts else ""
            try:
                tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=str(path))
            except SyntaxError as exc:
                notes.append(f"{_display(path, root)}: could not be parsed ({exc.msg}); skipped")
                continue
            if module_name in modules:
                notes.append(
                    f"{_display(path, root)}: duplicate module name '{module_name}' (already defined by "
                    f"{_display(modules[module_name].path, root)}); skipped"
                )
                continue
            modules[module_name] = Module(
                name=module_name,
                path=path,
                tree=tree,
                symbols=_collect(tree.body, ""),
            )
    return modules, notes


def resolve(modules: dict[str, Module], dotted: str) -> tuple[str, Symbol | None]:
    """Resolve a dotted target.

    Returns (status, symbol) where status is:
    - `found`: an internal module prefix resolved and every attribute exists;
    - `missing`: an internal module prefix resolved but an attribute does not;
    - `external`: no module of this repository is a prefix, so the target cannot
      be checked (stdlib, third-party package, builtins).
    """
    parts = dotted.split(".")
    for index in range(len(parts), 0, -1):
        prefix = ".".join(parts[:index])
        module = modules.get(prefix)
        if module is None:
            continue
        symbol = Symbol(module.name, "module", children=module.symbols)
        for attribute in parts[index:]:
            child = symbol.children.get(attribute)
            if child is None:
                return "missing", symbol
            symbol = child
        return "found", symbol
    return "external", None


def _collect(body: list[ast.stmt], prefix: str) -> dict[str, Symbol]:
    symbols: dict[str, Symbol] = {}
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols[node.name] = Symbol(
                qualname=prefix + node.name,
                kind="function",
                signature=from_arguments(node.args),
            )
        elif isinstance(node, ast.ClassDef):
            children = _collect_class_body(node.body, prefix + node.name + ".")
            init = _find_init(node.body)
            symbols[node.name] = Symbol(
                qualname=prefix + node.name,
                kind="class",
                signature=from_arguments(init.args, drop_self=True) if init else None,
                children=children,
            )
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    symbols[target.id] = Symbol(qualname=prefix + target.id, kind="assignment")
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            symbols[node.target.id] = Symbol(qualname=prefix + node.target.id, kind="assignment")
    return symbols


def _collect_class_body(body: list[ast.stmt], prefix: str) -> dict[str, Symbol]:
    symbols: dict[str, Symbol] = {}
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols[node.name] = Symbol(
                qualname=prefix + node.name,
                kind="function",
                signature=from_arguments(node.args, drop_self=True),
            )
        elif isinstance(node, ast.ClassDef):
            symbols[node.name] = Symbol(
                qualname=prefix + node.name,
                kind="class",
                children=_collect_class_body(node.body, prefix + node.name + "."),
            )
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    symbols[target.id] = Symbol(qualname=prefix + target.id, kind="assignment")
    return symbols


def _find_init(body: list[ast.stmt]) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "__init__":
            return node
    return None


def _display(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)
