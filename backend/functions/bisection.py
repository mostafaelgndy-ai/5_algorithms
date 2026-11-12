"""Bisection method: halve [a, b] and keep the half where f changes sign."""

from __future__ import annotations

from typing import Any

from .common import SolverError, finite


def bisection(f, a: float, b: float, tol: float, max_iter: int) -> dict[str, Any]:
    fa, fb = finite(f(a)), finite(f(b))
    if fa == 0:
        return {"root": a, "steps": [], "iterations": 0}
    if fb == 0:
        return {"root": b, "steps": [], "iterations": 0}
    if fa * fb > 0:
        raise SolverError("No root exists in the given interval (f(a) and f(b) have the same sign)")

    steps = []
    for i in range(1, max_iter + 1):
        c = (a + b) / 2
        fc = finite(f(c))
        err = abs(b - a) / 2
        steps.append({"i": i, "a": a, "b": b, "c": c, "fc": fc, "error": err})
        if err < tol or fc == 0:
            return {"root": c, "steps": steps, "iterations": i}
        if fa * fc < 0:
            b, fb = c, fc
        else:
            a, fa = c, fc
    raise SolverError("Tolerance was not reached within the maximum number of iterations")
