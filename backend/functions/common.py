"""Shared helpers for the numerical-method functions."""

from __future__ import annotations

import math

from fastapi import HTTPException


class SolverError(HTTPException):
    """Signals a user-facing failure; rendered as a 400 with {"message": ...}."""

    def __init__(self, message: str):
        super().__init__(status_code=400, detail={"message": message})


def finite(value: float) -> float:
    """Reject NaN/inf results coming from f(x)."""
    if math.isnan(value) or math.isinf(value):
        raise SolverError("f(x) is undefined at some evaluated point, check the interval")
    return value
