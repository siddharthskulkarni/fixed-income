from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import scipy.optimize as opt

from fixed_income.data.types import FuturesSettle, FuturesSettleCurve
from fixed_income.rates.ois import DiscountCurve, forward_rate_from_discount

_MONTH_NUM = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}


def _third_wednesday(year: int, month: int) -> date:
    """Third Wednesday of ``month`` in ``year``."""
    d = date(year, month, 1)
    wednesdays = 0
    while True:
        if d.weekday() == 2:
            wednesdays += 1
            if wednesdays == 3:
                return d
        d += timedelta(days=1)


def accrual_window_years(
    contract_month: str,
    as_of: date,
    product: str,
) -> tuple[float, float]:
    """
    Approximate accrual window as year fractions from ``as_of``.

    SR3: CME reference quarter (3rd Wed to 3rd Wed).
    SR1: prior calendar month to delivery month (simplified).
    """
    parts = contract_month.strip().upper().split()
    if len(parts) != 2:
        raise ValueError(f"Unrecognized contract month: {contract_month!r}")
    mon, yy = parts[0], parts[1]
    month_num = _MONTH_NUM[mon]
    year = 2000 + int(yy)

    if product == "SR3":
        accrual_end = _third_wednesday(year, month_num)
        start_month = month_num - 3
        start_year = year
        while start_month <= 0:
            start_month += 12
            start_year -= 1
        accrual_start = _third_wednesday(start_year, start_month)
    else:
        accrual_end = date(year, month_num, 15)
        start_month = month_num - 1
        start_year = year
        if start_month <= 0:
            start_month = 12
            start_year -= 1
        accrual_start = date(start_year, start_month, 15)

    t0 = (accrual_start - as_of).days / 365.25
    t1 = (accrual_end - as_of).days / 365.25
    return float(t0), float(max(t1, t0 + 1e-6))


def hull_white_B(t: float, T: float, a: float) -> float:
    dt = T - t
    if dt <= 0:
        return 0.0
    if abs(a) < 1e-10:
        return dt
    return (1.0 - np.exp(-a * dt)) / a


def convexity_adjustment_rate(a: float, sigma: float, t_end: float) -> float:
    """
    Hull-White 1F convexity adjustment (decimal rate) added to simple forward.

    See Brigo/Mercurio-style Gaussian short-rate futures adjustment.
    """
    if t_end <= 0:
        return 0.0
    B = hull_white_B(0.0, t_end, a)
    if abs(a) < 1e-10:
        return 0.5 * sigma**2 * t_end**2
    return (sigma**2) * (B**2) * (1.0 - np.exp(-2.0 * a * t_end)) / (4.0 * a * a)


@dataclass(frozen=True)
class HullWhiteCalibrationResult:
    a: float
    sigma: float
    rmse: float
    residuals: tuple[tuple[str, float, float, float], ...]  # symbol, market, model, t1


class HullWhite:
    """
    One-factor Hull-White short-rate model with initial curve from ``DiscountCurve``.

    Futures are quoted CME-style: price = 100 - R (R in percent).
    """

    def __init__(
        self,
        discount_curve: DiscountCurve,
        a: float,
        sigma: float,
        r0: float | None = None,
    ):
        if a <= 0 or sigma <= 0:
            raise ValueError("a and sigma must be positive")
        self.discount_curve = discount_curve
        self.a = float(a)
        self.sigma = float(sigma)
        if r0 is None:
            r0 = forward_rate_from_discount(discount_curve, 0.0, 1.0 / 365.25)
        self.r0 = float(r0)

    def bond_price(self, t: float, T: float, r: float | None = None) -> float:
        """Risk-neutral zero-coupon bond price P(t, T)."""
        if T <= t:
            raise ValueError("T must be greater than t")
        r = self.r0 if r is None else float(r)
        B = hull_white_B(t, T, self.a)
        p_market = self.discount_curve.discount(T) / self.discount_curve.discount(t)
        ln_p = np.log(max(p_market, 1e-12))
        ln_a = ln_p + B * r - convexity_adjustment_rate(self.a, self.sigma, T) * B
        return float(np.exp(ln_a - B * r))

    def futures_settle_price(self, t_start: float, t_end: float) -> float:
        """Model SOFR futures settlement (100 - compounded rate in percent)."""
        t_start = max(float(t_start), 0.0)
        t_end = float(t_end)
        fwd = forward_rate_from_discount(self.discount_curve, t_start, t_end)
        ca = convexity_adjustment_rate(self.a, self.sigma, t_end)
        rate_pct = (fwd + ca) * 100.0
        return 100.0 - rate_pct

    def futures_settle_for_contract(self, settle: FuturesSettle) -> float:
        t0, t1 = accrual_window_years(
            settle.contract_month, self.discount_curve.as_of, settle.product
        )
        return self.futures_settle_price(t0, t1)

    @classmethod
    def calibrate_to_futures(
        cls,
        futures: FuturesSettleCurve,
        discount: DiscountCurve,
        *,
        min_volume: int = 1,
        a_bounds: tuple[float, float] = (0.01, 2.0),
        sigma_bounds: tuple[float, float] = (0.0001, 0.05),
    ) -> HullWhiteCalibrationResult:
        """
        Calibrate ``(a, sigma)`` to liquid futures settlements via least squares.
        """
        contracts = [
            s
            for s in futures.settles
            if s.volume is None or s.volume >= min_volume
        ]
        if not contracts:
            raise ValueError("No futures contracts passed the volume filter")

        def objective(x: np.ndarray) -> float:
            a, sigma = float(x[0]), float(x[1])
            if a <= 0 or sigma <= 0:
                return 1e12
            try:
                hw = cls(discount, a, sigma)
            except ValueError:
                return 1e12
            err = 0.0
            for s in contracts:
                model = hw.futures_settle_for_contract(s)
                err += (model - s.settle) ** 2
            return err

        x0 = np.array([0.1, 0.01], dtype=float)
        bounds = [a_bounds, sigma_bounds]
        res = opt.minimize(objective, x0, method="L-BFGS-B", bounds=bounds)
        a_hat, sigma_hat = float(res.x[0]), float(res.x[1])
        hw = cls(discount, a_hat, sigma_hat)

        residuals: list[tuple[str, float, float, float]] = []
        sq_err = 0.0
        for s in contracts:
            t0, t1 = accrual_window_years(s.contract_month, discount.as_of, s.product)
            model = hw.futures_settle_price(t0, t1)
            residuals.append((s.symbol, s.settle, model, t1))
            sq_err += (model - s.settle) ** 2
        rmse = float(np.sqrt(sq_err / len(contracts)))
        return HullWhiteCalibrationResult(
            a=a_hat,
            sigma=sigma_hat,
            rmse=rmse,
            residuals=tuple(residuals),
        )
