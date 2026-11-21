"""Signature shapes derived from the AST."""

from __future__ import annotations

import ast
from dataclasses import dataclass


@dataclass(frozen=True)
class Signature:
    """The call shape of a function: names only, no default values."""

    positional: tuple[str, ...]
    required: int
    kwonly_required: tuple[str, ...]
    kwonly: tuple[str, ...]
    varargs: bool
    varkw: bool

    def render(self, name: str = "fn") -> str:
        parts = list(self.positional)
        if self.varargs:
            parts.append("*args")
        elif self.kwonly:
            parts.append("*")
        for param in self.kwonly:
            parts.append(param if param in self.kwonly_required else f"{param}=...")
        if self.varkw:
            parts.append("**kwargs")
        return f"{name}({', '.join(parts)})"

    def as_dict(self) -> dict[str, object]:
        return {
            "positional": list(self.positional),
            "required": self.required,
            "kwonly_required": list(self.kwonly_required),
            "kwonly": list(self.kwonly),
            "varargs": self.varargs,
            "varkw": self.varkw,
        }


def from_arguments(arguments: ast.arguments, drop_self: bool = False) -> Signature:
    positional = [argument.arg for argument in (*arguments.posonlyargs, *arguments.args)]
    required = max(0, len(positional) - len(arguments.defaults))
    if drop_self and positional and positional[0] in ("self", "cls"):
        positional = positional[1:]
        required = max(0, required - 1)
    kwonly = [argument.arg for argument in arguments.kwonlyargs]
    kwonly_required = [
        argument.arg
        for argument, default in zip(arguments.kwonlyargs, arguments.kw_defaults)
        if default is None
    ]
    return Signature(
        positional=tuple(positional),
        required=required,
        kwonly_required=tuple(kwonly_required),
        kwonly=tuple(kwonly),
        varargs=arguments.vararg is not None,
        varkw=arguments.kwarg is not None,
    )
