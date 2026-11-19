"""FastAPI application: POST /api/solve dispatches to backend/functions/."""

from __future__ import annotations

import math
from typing import Any, Literal, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from functions.common import SolverError
from functions.equation import InvalidEquation, make_function
from functions.gauss_jacobi import gauss_jacobi
from functions.linear_regression import linear_regression
from functions.matrix import parse_system
from functions.bisection import bisection
from functions.modified_secant import modified_secant
from functions.secant import secant

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
# Request / response models
# ---------------------------------------------------------------------------

Method = Literal["bisection", "gauss_jacobi", "linear_regression", "secant", "modified_secant"]


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
    data: Optional[list[list[float]]] = None
    params: Params


class GraphData(BaseModel):
    root: Optional[float] = None
    points: list[list[float]] = Field(default_factory=list)
    scatter: Optional[list[list[float]]] = None
    line: Optional[list[list[float]]] = None


class SolveResponse(BaseModel):
    method: Method
    equation: Optional[str] = None
    root: Optional[float] = None
    solution: Optional[list[float]] = None
    coefficients: Optional[list[float]] = None
    r2: Optional[float] = None
    n_points: Optional[int] = None
    iterations: int
    error: float
    converged: bool
    steps: list[dict[str, Any]]
    graph: Optional[GraphData] = None


# ---------------------------------------------------------------------------
# Plotting helper
# ---------------------------------------------------------------------------


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


def _regression_graph(points: list[list[float]], coefficients: list[float]) -> GraphData:
    """Scatter of the input points plus the fitted line y = a + b*x."""
    intercept, slope = coefficients
    xs = [float(row[0]) for row in points]
    x_min, x_max = min(xs), max(xs)
    if x_min == x_max:
        x_min -= 1.0
        x_max += 1.0

    scatter = [[round(float(x), 8), round(float(y), 8)] for x, y in points]
    line = [
        [round(x_min, 8), round(intercept + slope * x_min, 8)],
        [round(x_max, 8), round(intercept + slope * x_max, 8)],
    ]
    return GraphData(root=None, points=[], scatter=scatter, line=line)


# ---------------------------------------------------------------------------
# POST /api/solve
# ---------------------------------------------------------------------------


@app.post("/api/solve", response_model=SolveResponse)
def solve(req: SolveRequest) -> dict[str, Any]:
    p = req.params
    method = req.method
    numeric_methods = ("bisection", "secant", "modified_secant")

    if method == "linear_regression":
        if req.data is None:
            raise SolverError("Linear regression requires data points (x y on each row)")
        data = req.data
    elif method in numeric_methods:
        if not req.equation:
            raise SolverError("An equation f(x) is required for this method")
        try:
            f = make_function(req.equation)
        except InvalidEquation as exc:
            raise SolverError(f"Invalid equation: {exc}")
    else:
        if req.system is None:
            raise SolverError("This method requires the system matrix (n rows, each with n coefficients + 1 RHS)")
        system = parse_system(req.system)

    try:
        if method == "bisection":
            if p.a is None or p.b is None:
                raise SolverError("Bisection requires interval start (a) and end (b)")
            if p.a >= p.b:
                raise SolverError("Interval start a must be less than b")
            res = bisection(f, p.a, p.b, p.tolerance, p.max_iterations)
        elif method == "secant":
            if p.x0 is None or p.x1 is None:
                raise SolverError("The secant requires first (x0) and second (x1) guesses")
            res = secant(f, p.x0, p.x1, p.tolerance, p.max_iterations)
        elif method == "modified_secant":
            if p.x0 is None:
                raise SolverError("The modified secant requires an initial guess (x0)")
            res = modified_secant(f, p.x0, p.delta or 0.01, p.tolerance, p.max_iterations)
        elif method == "gauss_jacobi":
            res = gauss_jacobi(system, p.tolerance, p.max_iterations)
        else:  # linear_regression
            res = linear_regression(data)
    except OverflowError:
        raise SolverError("The calculation overflowed, check the inputs")

    if method in numeric_methods:
        graph = _graph_points(f, float(res["root"]), p.a, p.b)
    elif method == "linear_regression":
        graph = _regression_graph(data, res["coefficients"])
    else:
        graph = None

    error = res.get("error")
    if error is None:
        error = float(res["steps"][-1]["error"]) if res["steps"] and "error" in res["steps"][-1] else 0.0

    return {
        "method": method,
        "equation": req.equation,
        "root": float(res["root"]) if "root" in res else None,
        "solution": res.get("solution"),
        "coefficients": res.get("coefficients"),
        "r2": res.get("r2"),
        "n_points": res.get("n_points"),
        "iterations": int(res.get("iterations", 0)),
        "error": float(error),
        "converged": True,
        "steps": res["steps"],
        "graph": graph,
    }
