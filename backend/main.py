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


@app.get("/health")
def health():
    return {"status": "ok"}


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

Method = Literal["bisection", "gauss_elimination", "gauss_seidel", "secant", "modified_secant"]


class Params(BaseModel):
    a: Optional[float] = None
    b: Optional[float] = None
    x0: Optional[float] = None
    x1: Optional[float] = None
    delta: Optional[float] = None
    tolerance: float = Field(default=1e-4, gt=0)
    max_iterations: int = Field(default=50, ge=1, le=10000)


class SolveRequest(BaseModel):
    method: Method
    equation: Optional[str] = None
    system: Optional[list[list[float]]] = None
    params: Params


class GraphData(BaseModel):
    root: float
    points: list[list[float]]


class SolveResponse(BaseModel):
    method: Method
    equation: Optional[str] = None
    root: Optional[float] = None
    solution: Optional[list[float]] = None
    iterations: int
    error: float
    converged: bool
    steps: list[dict[str, Any]]
    graph: Optional[GraphData] = None


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


# ---------------------------------------------------------------------------
# Linear-system solvers (Ax = b)
# ---------------------------------------------------------------------------


def _parse_system(system: list[list[float]]) -> list[list[float]]:
    """Validate the augmented matrix; each row must have n coefficients + 1 RHS."""
    rows = len(system)
    if rows == 0:
        raise SolverError("The system is empty")
    for row in system:
        if len(row) != rows + 1:
            raise SolverError(
                "Each system row needs n coefficients plus 1 right-hand-side value "
                "(an n x (n+1) augmented matrix)"
            )
    return [row[:] for row in system]


def _gauss_elimination(matrix: list[list[float]]):
    """Gauss Elimination with partial pivoting. Rows are appended to the steps
    after every row operation, as operation descriptions of the form
    `R{k+1} -> R{k+1} - factor * R{i+1}`."""
    aug = matrix
    n = len(aug)
    steps: list[dict[str, Any]] = []

    def snapshot(op: str, row_index: int):
        entry: dict[str, Any] = {"i": len(steps) + 1, "op": op}
        for j in range(n + 1):
            entry[f"v{j}"] = round(aug[row_index][j], 8)
        steps.append(entry)

    for i in range(n):
        # Partial pivoting: move the largest coefficient in column i to the pivot.
        pivot_row = max(range(i, n), key=lambda r: abs(aug[r][i]))
        if abs(aug[pivot_row][i]) < 1e-300:
            raise SolverError("The matrix is singular, Gauss Elimination cannot solve this system")
        if pivot_row != i:
            aug[i], aug[pivot_row] = aug[pivot_row], aug[i]
            snapshot(f"R{i + 1} <-> R{pivot_row + 1}", i)
        for k in range(i + 1, n):
            factor = aug[k][i] / aug[i][i]
            if factor == 0:
                continue
            for j in range(i, n + 1):
                aug[k][j] -= factor * aug[i][j]
            snapshot(f"R{k + 1} -> R{k + 1} - {factor:.6g}R{i + 1}", k)

    # Back substitution
    solution = [0.0] * n
    for i in range(n - 1, -1, -1):
        rhs = aug[i][n] - sum(aug[i][j] * solution[j] for j in range(i + 1, n))
        solution[i] = rhs / aug[i][i]

    return {"solution": solution, "steps": steps, "iterations": len(steps)}


def _gauss_seidel(matrix: list[list[float]], tol: float, max_iter: int):
    """Gauss-Seidel: iterate x_i <- (b_i - sum_{j != i} A[i][j] * x_j) / A[i][i],
    using updated values as soon as they are available."""
    n = len(matrix)
    A = [row[:n] for row in matrix]
    b = [row[n] for row in matrix]
    if any(abs(A[i][i]) < 1e-300 for i in range(n)):
        raise SolverError(
            "A zero element on the diagonal, Gauss-Seidel cannot solve this system"
        )
    x = [0.0] * n
    steps: list[dict[str, Any]] = []
    for it in range(1, max_iter + 1):
        x_old = x[:]
        for i in range(n):
            s = b[i] - sum(A[i][j] * x[j] for j in range(n) if j != i)
            x[i] = s / A[i][i]
        err = max(abs(x[i] - x_old[i]) for i in range(n))
        entry: dict[str, Any] = {"i": it}
        for k in range(n):
            entry[f"v{k}"] = round(x[k], 8)
        entry["error"] = err
        steps.append(entry)
        if err < tol:
            return {"solution": x, "steps": steps, "iterations": it}
    raise SolverError("Tolerance was not reached within the maximum number of iterations")


def _modified_secant(f, x0: float, delta: float, tol: float, max_iter: int):
    """Modified secant: x_{k+1} = x_k - delta * x_k * f(x_k)
    / (f(x_k + delta * x_k) - f(x_k))."""
    x = x0
    steps: list[dict[str, float | int]] = []
    for i in range(1, max_iter + 1):
        fx = _finite(f(x))
        xpert = x + delta * x
        fxp = _finite(f(xpert))
        denom = fxp - fx
        if denom == 0:
            raise SolverError("The modified secant reached a zero denominator (two equal function values)")
        nx = x - delta * x * fx / denom
        if not math.isfinite(nx) or abs(nx) > 1e100:
            raise SolverError("The modified secant diverged, the initial guess or delta may be unsuitable")
        err = abs(nx - x)
        steps.append({"i": i, "xn": x, "fxn": fx, "f2": fxp, "error": err})
        x = nx
        if err < tol or fx == 0:
            return {"root": x, "steps": steps, "iterations": i}
    raise SolverError("Tolerance was not reached within the maximum number of iterations")


# ---------------------------------------------------------------------------
# POST /api/solve
# ---------------------------------------------------------------------------


@app.post("/api/solve", response_model=SolveResponse)
def solve(req: SolveRequest) -> dict[str, Any]:
    p = req.params
    method = req.method
    numeric_methods = ("bisection", "secant", "modified_secant")

    if method in numeric_methods:
        if not req.equation:
            raise SolverError("An equation f(x) is required for this method")
        try:
            f = make_function(req.equation)
        except InvalidEquation as exc:
            raise SolverError(f"Invalid equation: {exc}")
    else:
        if req.system is None:
            raise SolverError("This method requires the system matrix (n rows, each with n coefficients + 1 RHS)")
        system = _parse_system(req.system)

    try:
        if method == "bisection":
            if p.a is None or p.b is None:
                raise SolverError("Bisection requires interval start (a) and end (b)")
            if p.a >= p.b:
                raise SolverError("Interval start a must be less than b")
            res = _bisection(f, p.a, p.b, p.tolerance, p.max_iterations)
        elif method == "secant":
            if p.x0 is None or p.x1 is None:
                raise SolverError("The secant requires first (x0) and second (x1) guesses")
            res = _secant(f, p.x0, p.x1, p.tolerance, p.max_iterations)
        elif method == "modified_secant":
            if p.x0 is None:
                raise SolverError("The modified secant requires an initial guess (x0)")
            res = _modified_secant(f, p.x0, p.delta or 0.01, p.tolerance, p.max_iterations)
        elif method == "gauss_elimination":
            res = _gauss_elimination(system)
        else:  # gauss_seidel
            res = _gauss_seidel(system, p.tolerance, p.max_iterations)
    except OverflowError:
        raise SolverError("The calculation overflowed, check the inputs")

    graph = _graph_points(f, float(res["root"]), p.a, p.b) if method in numeric_methods else None

    return {
        "method": method,
        "equation": req.equation,
        "root": float(res["root"]) if "root" in res else None,
        "solution": res.get("solution"),
        "iterations": int(res["iterations"]),
        "error": float(res["steps"][-1]["error"]) if res["steps"] and "error" in res["steps"][-1] else 0.0,
        "converged": True,
        "steps": res["steps"],
        "graph": graph,
    }
