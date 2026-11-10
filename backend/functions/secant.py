"""Secant method: x_{k+1} = x_k - f(x_k) * (x_k - x_{k-1})
/ (f(x_k) - f(x_{k-1}))."""

from __future__ import annotations

from typing import Any

import math

from .common import SolverError, finite


def secant(f, x0: float, x1: float, tol: float, max_iter: int) -> dict[str, Any]:
    prev, cur = x0, x1
    fprev, fcur = finite(f(prev)), finite(f(cur))
    steps: list[dict[str, float | int]] = []
    for i in range(1, max_iter + 1):
        denom = fcur - fprev
        if denom == 0:
            raise SolverError("f(x) has the same value at both guesses, the secant cannot proceed")
        nxt = cur - fcur * (cur - prev) / denom
        if not math.isfinite(nxt) or abs(nxt) > 1e100:
            raise SolverError("The secant method diverged, the initial guesses may be unsuitable")
        err = abs(nxt - cur)
        fnxt = finite(f(nxt))
        steps.append({"i": i, "xnm1": prev, "xn": cur, "xnp1": nxt, "fxn": fcur, "error": err})
        prev, fprev, cur, fcur = cur, fcur, nxt, fnxt
        if err < tol or fnxt == 0:
            return {"root": nxt, "steps": steps, "iterations": i}
    raise SolverError("Tolerance was not reached within the maximum number of iterations")
