import ast

from mockdrift.signature import from_arguments


def signature(source: str, drop_self: bool = False):
    module = ast.parse(f"def fn{source}:\n    pass\n")
    return from_arguments(module.body[0].args, drop_self=drop_self)


def test_positional_and_defaults() -> None:
    sig = signature("(a, b, c=1)")
    assert sig.positional == ("a", "b", "c")
    assert sig.required == 2


def test_positional_only_parameters_are_positional() -> None:
    sig = signature("(a, /, b)")
    assert sig.positional == ("a", "b")
    assert sig.required == 2


def test_keyword_only_and_required_keyword_only() -> None:
    sig = signature("(a, *, b, c=1)")
    assert sig.kwonly == ("b", "c")
    assert sig.kwonly_required == ("b",)
    assert sig.required == 1


def test_varargs_and_varkw() -> None:
    sig = signature("(*args, **kwargs)")
    assert sig.positional == ()
    assert sig.varargs is True
    assert sig.varkw is True


def test_drop_self_removes_the_receiver() -> None:
    module = ast.parse("class C:\n    def m(self, a, b=1):\n        pass\n")
    sig = from_arguments(module.body[0].body[0].args, drop_self=True)
    assert sig.positional == ("a", "b")
    assert sig.required == 1


def test_render_shows_the_shape() -> None:
    sig = signature("(a, b, *, c, d=1)")
    assert sig.render("f") == "f(a, b, *, c, d=...)"


def test_render_varargs() -> None:
    sig = signature("(*args, **kwargs)")
    assert sig.render("f") == "f(*args, **kwargs)"


def test_as_dict_round_trips_the_fields() -> None:
    payload = signature("(a, *, b=1)").as_dict()
    assert payload["positional"] == ["a"]
    assert payload["kwonly"] == ["b"]
    assert payload["kwonly_required"] == []
