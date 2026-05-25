import numpy as np

from fixed_income.data import ParCurve


def _validate_frequency(frequency):
    if int(frequency) != frequency or frequency < 1:
        raise ValueError("frequency must be a positive integer")
    return int(frequency)


def bootstrap_spot_curve(par_curve, m=2, frequency=None):
    """
    Bootstrap spot zero rates from a Treasury par yield curve.

    Returns:
        (maturities, spot_rates) as 1D numpy arrays.
    """
    m = _validate_frequency(frequency if frequency is not None else m)

    maturities = np.asarray([p.maturity_years for p in par_curve.points], dtype=float)
    par_yields = np.asarray([p.par_yield for p in par_curve.points], dtype=float)
    if maturities.ndim != 1 or par_yields.ndim != 1 or maturities.shape != par_yields.shape:
        raise ValueError("ParCurve points must provide matching maturities and yields")

    sort_idx = np.argsort(maturities)
    maturities = maturities[sort_idx]
    par_yields = par_yields[sort_idx]

    discount_factors = {}
    spot_rates = []

    for maturity, par_yield in zip(maturities, par_yields):
        if maturity <= 0:
            raise ValueError("Maturities must be positive")

        total_periods = int(round(maturity * m))
        if not np.isclose(maturity * m, total_periods):
            raise ValueError("Maturity must be a multiple of 1/m")

        coupon_per_period = par_yield / m
        if total_periods == 1:
            df_last = 1.0 / (1.0 + coupon_per_period)
        else:
            required_periods = range(1, total_periods)
            if not all(period in discount_factors for period in required_periods):
                raise ValueError(
                    "ParCurve maturities must include all earlier coupon dates for bootstrap"
                )
            sum_prev = coupon_per_period * sum(discount_factors[period] for period in required_periods)
            df_last = (1.0 - sum_prev) / (1.0 + coupon_per_period)

        if df_last <= 0:
            raise RuntimeError("Bootstrapped discount factor is non-positive")

        discount_factors[total_periods] = df_last
        spot_rates.append(float(m * (df_last ** (-1.0 / total_periods) - 1.0)))

    return maturities, np.asarray(spot_rates, dtype=float)


class USTreasurySpotCurve:
    def __init__(self, as_of_dates, maturities, spot_rates):
        self.as_of_dates = np.atleast_1d(np.asarray(as_of_dates, dtype=object))
        self.maturities = np.asarray(maturities, dtype=float)
        spot_rates = np.asarray(spot_rates, dtype=float)

        if spot_rates.ndim == 1:
            spot_rates = spot_rates.reshape(1, -1)
        if spot_rates.ndim != 2:
            raise ValueError("spot_rates must be 1D or 2D array")
        if spot_rates.shape[1] != len(self.maturities):
            raise ValueError("spot_rates must have one column per maturity")
        if spot_rates.shape[0] != len(self.as_of_dates):
            raise ValueError("spot_rates must have one row per valuation date")

        self.spot_rates = spot_rates

    @classmethod
    def from_par_curves(cls, par_curves, m=2, frequency=None):
        if isinstance(par_curves, ParCurve):
            par_curves = [par_curves]
        par_curves = list(par_curves)
        if len(par_curves) == 0:
            raise ValueError("At least one ParCurve is required")

        all_maturities = np.unique(
            np.concatenate(
                [np.asarray([p.maturity_years for p in curve.points], dtype=float) for curve in par_curves]
            )
        )
        all_maturities.sort()

        rows = []
        dates = []
        for curve in par_curves:
            maturities, spot_rates = bootstrap_spot_curve(curve, m=m, frequency=frequency)
            row = np.full(len(all_maturities), np.nan, dtype=float)
            for maturity, spot_rate in zip(maturities, spot_rates):
                index = int(np.where(all_maturities == maturity)[0][0])
                row[index] = spot_rate
            rows.append(row)
            dates.append(curve.as_of)

        return cls(dates, all_maturities, np.vstack(rows))

    def matrix(self):
        return self.spot_rates.copy()

    def __repr__(self):
        return (
            f"USTreasurySpotCurve(dates={self.as_of_dates.tolist()}, "
            f"maturities={self.maturities.tolist()})"
        )
