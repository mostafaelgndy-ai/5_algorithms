"""Linear least-squares regression: fit y = a + b*x to a set of (x, y) points."""

from __future__ import annotations

import math
from typing import Any

from .common import SolverError


def linear_regression(points: list[list[float]]) -> dict[str, Any]:
    if len(points) < 2:
        raise SolverError("Linear regression requires at least 2 data points")

    pairs: list[tuple[float, float]] = []
    for row in points:
        if len(row) != 2:
            raise SolverError("Each data row must contain exactly 2 numbers: x and y")
        x, y = float(row[0]), float(row[1])
        if not (math.isfinite(x) and math.isfinite(y)):
            raise SolverError("Data points must contain finite numbers")
        pairs.append((x, y))

    n = len(pairs)
    x_mean = sum(x for x, _ in pairs) / n
    y_mean = sum(y for _, y in pairs) / n

    sxx = sum((x - x_mean) ** 2 for x, _ in pairs)
    if abs(sxx) < 1e-300:
        raise SolverError("Linear regression requires at least two different x values")
    sxy = sum((x - x_mean) * (y - y_mean) for x, y in pairs)

    slope = sxy / sxx
    intercept = y_mean - slope * x_mean

    steps: list[dict[str, Any]] = []
    sse = 0.0
    for i, (x, y) in enumerate(pairs, start=1):
        yhat = intercept + slope * x
        residual = y - yhat
        sse += residual * residual
        steps.append(
            {
                "i": i,
                "x": round(x, 8),
                "y": round(y, 8),
                "yhat": round(yhat, 8),
                "residual": round(residual, 8),
            }
        )

    sst = sum((y - y_mean) ** 2 for _, y in pairs)
    r2 = None if abs(sst) < 1e-300 else 1 - sse / sst

    return {
        "coefficients": [intercept, slope],
        "r2": r2,
        "n_points": n,
        "error": math.sqrt(sse / n),
        "steps": steps,
    }
