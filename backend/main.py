from __future__ import annotations

import ast
import math
from typing import Any, Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="5_algorithms API")

# The Next.js dev server runs on http://localhost:3000 and calls this API directly.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Welcome to the 5_algorithms backend"}


# ---------------------------------------------------------------------------
# Equation parsing (safe evaluation of f(x))
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

Method = Literal["bisection", "false_position", "newton", "secant", "fixed_point"]


class Params(BaseModel):
    a: Optional[float] = None
    b: Optional[float] = None
    x0: Optional[float] = None
    x1: Optional[float] = None
    tolerance: float = Field(default=1e-4, gt=0)
    max_iterations: int = Field(default=50, ge=1, le=10000)


class SolveRequest(BaseModel):
    method: Method
    equation: str
    params: Params


class GraphData(BaseModel):
    root: float
    points: list[list[float]]


class SolveResponse(BaseModel):
    method: Method
    equation: str
    root: float
    iterations: int
    error: float
    converged: bool
    steps: list[dict[str, float | int]]
    graph: GraphData


# ---------------------------------------------------------------------------
# Solver helpers
# ---------------------------------------------------------------------------


class SolverError(HTTPException):
    def __init__(self, message: str):
        super().__init__(status_code=400, detail={"message": message})


def _finite(value: float) -> float:
    if math.isnan(value) or math.isinf(value):
        raise SolverError("f(x) is undefined at some evaluated point, check the interval")
    return value


def _derivative(f, x: float) -> float:
    """Central finite-difference derivative of f at x."""
    h = 1e-7 * max(1.0, abs(x))
    return (f(x + h) - f(x - h)) / (2.0 * h)


def _graph_points(f, root: float, a: Optional[float], b: Optional[float]) -> GraphData:
    """Sample f(x) for plotting; uses [a, b] when given, else a window around the root."""
    if a is not None and b is not None and a < b:
        x_min, x_max = a, b
    else:
        span = max(abs(root) * 0.5, 2.0, 1e-2)
        x_min, x_max = root - span, root + span
    n = 200
    points: list[list[float]] = []
    for i in range(n + 1):
        x = x_min + (x_max - x_min) * i / n
        try:
            y = f(x)
        except Exception:
            continue
        if not (math.isnan(y) or math.isinf(y)):
            points.append([round(x, 8), round(y, 8)])
    return GraphData(root=round(root, 8), points=points)


# ---------------------------------------------------------------------------
# Methods
# ---------------------------------------------------------------------------


def _bisection(f, a: float, b: float, tol: float, max_iter: int):
    fa, fb = _finite(f(a)), _finite(f(b))
    if fa == 0:
        return {"root": a, "steps": [], "iterations": 0}
    if fb == 0:
        return {"root": b, "steps": [], "iterations": 0}
    if fa * fb > 0:
        raise SolverError("No root exists in the given interval (f(a) and f(b) have the same sign)")

    steps: list[dict[str, float | int]] = []
    for i in range(1, max_iter + 1):
        c = (a + b) / 2
        fc = _finite(f(c))
        err = abs(b - a) / 2
        steps.append({"i": i, "a": a, "b": b, "c": c, "fc": fc, "error": err})
        if err < tol or fc == 0:
            return {"root": c, "steps": steps, "iterations": i}
        if fa * fc < 0:
            b, fb = c, fc
        else:
            a, fa = c, fc
    raise SolverError("Tolerance was not reached within the maximum number of iterations")


def _false_position(f, a: float, b: float, tol: float, max_iter: int):
    fa, fb = _finite(f(a)), _finite(f(b))
    if fa == 0:
        return {"root": a, "steps": [], "iterations": 0}
    if fb == 0:
        return {"root": b, "steps": [], "iterations": 0}
    if fa * fb > 0:
        raise SolverError("No root exists in the given interval (f(a) and f(b) have the same sign)")

    steps: list[dict[str, float | int]] = []
    c_prev: Optional[float] = None
    for i in range(1, max_iter + 1):
        if fb - fa == 0:
            raise SolverError("Division by zero in the interpolation formula")
        c = (a * fb - b * fa) / (fb - fa)
        fc = _finite(f(c))
        err = abs(c - c_prev) if c_prev is not None else abs(b - a)
        steps.append({"i": i, "a": a, "b": b, "c": c, "fc": fc, "error": err})
        c_prev = c
        if abs(fc) < tol or err < tol or fc == 0:
            return {"root": c, "steps": steps, "iterations": i}
        if fa * fc < 0:
            b, fb = c, fc
        else:
            a, fa = c, fc
    raise SolverError("Tolerance was not reached within the maximum number of iterations")


def _newton(f, x0: float, tol: float, max_iter: int):
    x = x0
    steps: list[dict[str, float | int]] = []
    for i in range(1, max_iter + 1):
        fx = _finite(f(x))
        dfx = _finite(_derivative(f, x))
        if dfx == 0:
            raise SolverError("The derivative equals zero")
        if abs(dfx) < 1e-14 * max(1.0, abs(fx)):
            raise SolverError("The derivative is too small to continue (near a horizontal tangent)")
        nx = x - fx / dfx
        err = abs(nx - x)
        steps.append({"i": i, "xn": x, "fxn": fx, "dfxn": dfx, "error": err})
        x = nx
        if not math.isfinite(x) or abs(x) > 1e100:
            raise SolverError("Newton-Raphson diverged, the initial guess may be unsuitable")
        if err < tol or fx == 0:
            return {"root": x, "steps": steps, "iterations": i}
    raise SolverError("Tolerance was not reached within the maximum number of iterations")


def _secant(f, x0: float, x1: float, tol: float, max_iter: int):
    prev, cur = x0, x1
    fprev, fcur = _finite(f(prev)), _finite(f(cur))
    steps: list[dict[str, float | int]] = []
    for i in range(1, max_iter + 1):
        denom = fcur - fprev
        if denom == 0:
            raise SolverError("f(x) has the same value at both guesses, the secant cannot proceed")
        nxt = cur - fcur * (cur - prev) / denom
        if not math.isfinite(nxt) or abs(nxt) > 1e100:
            raise SolverError("The secant method diverged, the initial guesses may be unsuitable")
        err = abs(nxt - cur)
        fnxt = _finite(f(nxt))
        steps.append({"i": i, "xnm1": prev, "xn": cur, "xnp1": nxt, "fxn": fcur, "error": err})
        prev, fprev, cur, fcur = cur, fcur, nxt, fnxt
        if err < tol or fnxt == 0:
            return {"root": nxt, "steps": steps, "iterations": i}
    raise SolverError("Tolerance was not reached within the maximum number of iterations")


def _fixed_point(f, x0: float, tol: float, max_iter: int):
    """Fixed-point iteration using g(x) = x - f(x), i.e. x_next = x - f(x)."""
    x = x0
    steps: list[dict[str, float | int]] = []
    for i in range(1, max_iter + 1):
        fx = _finite(f(x))
        err = abs(fx)
        nxt = x - fx
        if not math.isfinite(nxt) or abs(nxt) > 1e100:
            raise SolverError("Fixed Point iteration diverged, try another initial guess")
        steps.append({"i": i, "xn": x, "xnext": nxt, "fxn": fx, "error": err})
        x = nxt
        if err < tol:
            return {"root": x, "steps": steps, "iterations": i}
    raise SolverError("Tolerance was not reached within the maximum number of iterations")


# ---------------------------------------------------------------------------
# POST /api/solve
# ---------------------------------------------------------------------------


@app.post("/api/solve", response_model=SolveResponse)
def solve(req: SolveRequest) -> dict[str, Any]:
    p = req.params
    try:
        f = make_function(req.equation)
    except InvalidEquation as exc:
        raise SolverError(f"Invalid equation: {exc}")

    method = req.method
    try:
        if method == "bisection":
            if p.a is None or p.b is None:
                raise SolverError("Bisection requires interval start (a) and end (b)")
            if p.a >= p.b:
                raise SolverError("Interval start a must be less than b")
            res = _bisection(f, p.a, p.b, p.tolerance, p.max_iterations)
        elif method == "false_position":
            if p.a is None or p.b is None:
                raise SolverError("False Position requires interval start (a) and end (b)")
            if p.a >= p.b:
                raise SolverError("Interval start a must be less than b")
            res = _false_position(f, p.a, p.b, p.tolerance, p.max_iterations)
        elif method == "newton":
            if p.x0 is None:
                raise SolverError("Newton-Raphson requires an initial guess (x0)")
            res = _newton(f, p.x0, p.tolerance, p.max_iterations)
        elif method == "secant":
            if p.x0 is None or p.x1 is None:
                raise SolverError("Secant requires first (x0) and second (x1) guesses")
            res = _secant(f, p.x0, p.x1, p.tolerance, p.max_iterations)
        else:  # fixed_point
            if p.x0 is None:
                raise SolverError("Fixed Point requires an initial guess (x0)")
            res = _fixed_point(f, p.x0, p.tolerance, p.max_iterations)
    except OverflowError:
        raise SolverError("The calculation overflowed, check the equation and inputs")

    graph = _graph_points(f, float(res["root"]), p.a, p.b)

    return {
        "method": method,
        "equation": req.equation,
        "root": float(res["root"]),
        "iterations": int(res["iterations"]),
        "error": float(res["steps"][-1]["error"]) if res["steps"] else 0.0,
        "converged": True,
        "steps": res["steps"],
        "graph": graph,
    }
