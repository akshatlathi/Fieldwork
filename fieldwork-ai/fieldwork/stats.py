"""Exact (Clopper-Pearson) binomial confidence interval, pure Python (no scipy needed)."""

from __future__ import annotations

import math


def _binom_cdf(k: int, n: int, p: float) -> float:
    """P(X <= k) for X ~ Binomial(n, p)."""
    if p <= 0:
        return 1.0
    if p >= 1:
        return 1.0 if k >= n else 0.0
    lp, lq = math.log(p), math.log1p(-p)
    return min(1.0, sum(math.exp(math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1) + i * lp + (n - i) * lq)
                        for i in range(0, k + 1)))


def _bisect(f, lo: float = 0.0, hi: float = 1.0) -> float:
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if f(mid) else (lo, mid)
    return (lo + hi) / 2


def cp_interval(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Clopper-Pearson 1-alpha interval for k successes in n trials. n == 0 -> (0, 1)."""
    if n <= 0:
        return 0.0, 1.0
    lo = 0.0 if k == 0 else _bisect(lambda p: 1 - _binom_cdf(k - 1, n, p) < alpha / 2)
    hi = 1.0 if k == n else _bisect(lambda p: _binom_cdf(k, n, p) > alpha / 2, 0.0, 1.0)
    return lo, hi


def rate(k: int, n: int) -> dict:
    lo, hi = cp_interval(k, n)
    return {"k": k, "n": n, "rate": (k / n) if n else None, "ci95": [round(lo, 3), round(hi, 3)]}


def fmt(r: dict) -> str:
    """'3/10 = 30% (95% CI 7-65%)'"""
    if not r["n"]:
        return "n/a (N=0)"
    return f"{r['k']}/{r['n']} = {r['rate']:.0%} (95% CI {r['ci95'][0]:.0%}-{r['ci95'][1]:.0%}, N={r['n']})"
