"""Safe parsing/evaluation of a user equation f(x), no eval() involved."""

from __future__ import annotations

import ast
import math

_ALLOWED_FUNCS = {
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "sinh": math.sinh,
    "cosh": math.cosh,
    "tanh": math.tanh,
    "exp": math.exp,
    "log": math.log,
    "ln": math.log,
    "sqrt": math.sqrt,
    "abs": abs,
    "pow": pow,
}

_ALLOWED_NAMES = {
    "x": None,  # bound per evaluation
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
}

_ALLOWED_BINOPS = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.Pow: lambda a, b: a ** b,
    ast.Mod: lambda a, b: a % b,
}

_ALLOWED_UNARYOPS = {
    ast.UAdd: lambda a: +a,
    ast.USub: lambda a: -a,
}

# Common Unicode lookalikes pasted from documents/browsers.
_CHAR_MAP = {
    ord("\u2212"): "-",  # minus sign
    ord("\u2012"): "-",  # figure dash
    ord("\u2013"): "-",  # en dash
    ord("\u2014"): "-",  # em dash
    ord("\u2015"): "-",  # horizontal bar
    ord("\u00d7"): "*",  # multiplication sign
    ord("\u22c5"): "*",  # dot operator
    ord("\u00b7"): "*",  # middle dot
    ord("\u00f7"): "/",  # division sign
    ord("\uff0b"): "+",  # fullwidth plus
    ord("\uff0d"): "-",  # fullwidth minus
    ord("\u00b2"): "^2",  # superscript two
    ord("\u00b3"): "^3",  # superscript three
    ord("\u2070"): "^0",
    ord("\u2074"): "^4",
    ord("\u2075"): "^5",
    ord("\u2076"): "^6",
    ord("\u2077"): "^7",
    ord("\u2078"): "^8",
    ord("\u2079"): "^9",
}


class InvalidEquation(Exception):
    pass


def _validate(node: ast.expr) -> None:
    if isinstance(node, ast.BinOp):
        if type(node.op) not in _ALLOWED_BINOPS:
            raise InvalidEquation("unsupported operator")
        _validate(node.left)
        _validate(node.right)
    elif isinstance(node, ast.UnaryOp):
        if type(node.op) not in _ALLOWED_UNARYOPS:
            raise InvalidEquation("unsupported unary operator")
        _validate(node.operand)
    elif isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise InvalidEquation("only numeric constants are allowed")
    elif isinstance(node, ast.Name):
        if node.id not in _ALLOWED_NAMES:
            raise InvalidEquation(f"unknown symbol: {node.id}")
    elif isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _ALLOWED_FUNCS:
            raise InvalidEquation("unknown function")
        if node.keywords:
            raise InvalidEquation("keyword arguments are not allowed")
        for arg in node.args:
            _validate(arg)
    else:
        raise InvalidEquation("unsupported syntax")


def _eval_node(node: ast.expr, x: float) -> float:
    """Evaluate a validated AST node for a given x (no eval() involved)."""
    if isinstance(node, ast.BinOp):
        left = _eval_node(node.left, x)
        right = _eval_node(node.right, x)
        return _ALLOWED_BINOPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp):
        return _ALLOWED_UNARYOPS[type(node.op)](_eval_node(node.operand, x))
    if isinstance(node, ast.Constant):
        return float(node.value)
    if isinstance(node, ast.Name):
        return x if node.id == "x" else _ALLOWED_NAMES[node.id]
    if isinstance(node, ast.Call):
        func = _ALLOWED_FUNCS[node.func.id]
        args = [_eval_node(a, x) for a in node.args]
        return func(*args)
    raise InvalidEquation("unsupported syntax")


def make_function(equation: str):
    """Compile the user equation into a Python function of x.

    Accepts `^` for powers (treated as `**`) and raises InvalidEquation for
    anything that is not a plain numeric f(x) expression.
    """
    text = equation.strip().lower()
    # Normalize lookalike Unicode characters (a pasted minus sign, etc.).
    text = text.translate(_CHAR_MAP)
    text = text.replace("^", "**").replace("=", "")
    if not text:
        raise InvalidEquation("the equation is empty")
    try:
        tree = ast.parse(text, mode="eval")
    except SyntaxError as exc:
        raise InvalidEquation("check the syntax (e.g. x^3 - x - 2)") from exc
    _validate(tree.body)

    def f(x: float) -> float:
        try:
            value = _eval_node(tree.body, x)
        except ZeroDivisionError:
            return math.nan
        except ValueError:
            return math.nan  # e.g. sqrt(-2), log(-1) outside the function's domain
        except OverflowError:
            return math.nan  # e.g. exp(1000)
        if isinstance(value, complex):
            return math.nan  # e.g. (-2) ** 0.5
        return float(value)

    return f
