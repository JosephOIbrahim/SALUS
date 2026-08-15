"""Order-fixed numeric helpers. Determinism doctrine: every reduction
iterates in explicit, stable order; Kahan compensation throughout."""

from __future__ import annotations

from collections.abc import Sequence


def kahan_sum(values: Sequence[float]) -> float:
    """Kahan-Babuska-Neumaier compensated sum: survives cancellation
    (e.g. [1e16, 1.0, -1e16] -> 1.0), still order-fixed and deterministic."""
    total = 0.0
    comp = 0.0
    for v in values:
        t = total + v
        if abs(total) >= abs(v):
            comp += (total - t) + v
        else:
            comp += (v - t) + total
        total = t
    return total + comp


def mean(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return kahan_sum(values) / len(values)


def variance(values: Sequence[float]) -> float:
    """Population variance, two Kahan passes."""
    n = len(values)
    if n == 0:
        return 0.0
    m = mean(values)
    return kahan_sum([(v - m) * (v - m) for v in values]) / n


def slope(values: Sequence[float]) -> float:
    """Least-squares slope over x = 0..n-1. Zero for degenerate input."""
    n = len(values)
    if n < 2:
        return 0.0
    sx = n * (n - 1) / 2.0
    sxx = (n - 1) * n * (2 * n - 1) / 6.0
    sy = kahan_sum(values)
    sxy = kahan_sum([i * v for i, v in enumerate(values)])
    denom = n * sxx - sx * sx
    if denom == 0.0:
        return 0.0
    return (n * sxy - sx * sy) / denom
