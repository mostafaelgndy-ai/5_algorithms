"""Helpers for linear systems Ax = b passed as an augmented matrix."""

from __future__ import annotations

from .common import SolverError


def parse_system(system: list[list[float]]) -> list[list[float]]:
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


def split_system(matrix: list[list[float]]) -> tuple[list[list[float]], list[float]]:
    """Split an augmented matrix into the coefficient matrix A and the right-hand side b."""
    n = len(matrix)
    return [row[:n] for row in matrix], [row[n] for row in matrix]
