"""Gauss-Seidel: iterate x_i <- (b_i - sum_{j != i} A[i][j] * x_j) / A[i][i],
using updated values as soon as they are available."""

from __future__ import annotations

from typing import Any

from .common import SolverError
from .matrix import split_system


def gauss_seidel(matrix: list[list[float]], tol: float, max_iter: int) -> dict[str, Any]:
    A, b = split_system(matrix)
    n = len(A)
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
