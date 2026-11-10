"""Modified secant method: x_{k+1} = x_k - delta * x_k * f(x_k)
/ (f(x_k + delta * x_k) - f(x_k))."""

from __future__ import annotations

from typing import Any

import math

from .common import SolverError, finite


def modified_secant(f, x0: float, delta: float, tol: float, max_iter: int) -> dict[str, Any]:
    x = x0
    steps: list[dict[str, float | int]] = []
    for i in range(1, max_iter + 1):
        fx = finite(f(x))
        xpert = x + delta * x
        fxp = finite(f(xpert))
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
