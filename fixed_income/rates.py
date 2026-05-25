import numpy as np
import scipy as sp

from fixed_income.data import ParCurve

class NelsonSiegel:
    def __init__(self, t, r):
        """
        Initialize the Nelson-Siegel model with its parameters.
        
        Parameters:
        t (np.array): Maturities (in years; any consistent unit is fine as long as `tau` matches).
        r (np.array): Yields corresponding to maturities (in decimal, e.g. 0.045 for 4.5%).
        """
        self.t = np.asarray(t, dtype=float)
        self.r = np.asarray(r, dtype=float)
        self.betas = None
        self.tau = None

    @staticmethod
    def _loadings(t, tau):
        t = np.asarray(t, dtype=float)
        tau = float(tau)
        if tau <= 0:
            raise ValueError("tau must be positive")

        x = t / tau
        with np.errstate(divide="ignore", invalid="ignore"):
            l1 = np.where(x == 0.0, 1.0, (1.0 - np.exp(-x)) / x)
        l2 = l1 - np.exp(-x)
        return l1, l2

    def f(self, t):
        """
        Predict the yield for a given maturity t using the Nelson-Siegel formula.
        
        Parameters:
        t (float or np.array): Maturity (in same units as used in fitting).
        
        Returns:
        float or np.array: Predicted yield.
        """
        if self.betas is None or self.tau is None:
            raise RuntimeError("Model is not fit yet; call fit() first.")
        l1, l2 = self._loadings(t, self.tau)
        beta0, beta1, beta2 = self.betas
        return beta0 + beta1 * l1 + beta2 * l2
    
    def fit(self, tau0=1.0):
        """
        Fit (beta0, beta1, beta2, tau) via non-linear least squares.

        Parameters:
        tau0 (float): Initial guess for tau (in same units as `t`).
        """
        x = self.t
        y = self.r
        if x.ndim != 1 or y.ndim != 1 or x.shape[0] != y.shape[0]:
            raise ValueError("t and r must be 1D arrays of the same length")
        if np.any(x < 0):
            raise ValueError("maturities must be non-negative")

        # Use log(tau) to enforce positivity.
        def residuals(params):
            beta0, beta1, beta2, log_tau = params
            tau = float(np.exp(log_tau))
            l1, l2 = self._loadings(x, tau)
            y_hat = beta0 + beta1 * l1 + beta2 * l2
            return y_hat - y

        beta0_0 = float(y[-1]) if y.size else 0.0
        x0 = np.array([beta0_0, -0.01, 0.01, np.log(float(tau0))], dtype=float)
        res = sp.optimize.least_squares(residuals, x0=x0, method="trf")
        beta0, beta1, beta2, log_tau = res.x
        self.betas = np.array([beta0, beta1, beta2], dtype=float)
        self.tau = float(np.exp(log_tau))


def _validate_frequency(frequency):
    if int(frequency) != frequency or frequency < 1:
        raise ValueError("frequency must be a positive integer")
    return int(frequency)


def bootstrap_spot_curve(par_curve, m=2, frequency=None):
    """
    Bootstrap spot zero rates from a Treasury par yield curve.

    Parameters:
    par_curve (ParCurve): Par yield curve with maturities and par yields.
    m (int): Coupon payments per year used when pricing the par bond.
    frequency (int): legacy alias for coupon payments per year.

    Returns:
    (np.ndarray, np.ndarray): (maturities, spot_rates) for the bootstrapped curve.

    Notes:
    - Let `m` be the coupon frequency and `N = m * T` the number of periods.
    - A par bond priced at par has value:
      1 = c * \sum_{i=1}^{N-1} DF_i + (1 + c) * DF_N,
      where c = par_yield / m is the per-period coupon.
    - Discount factors are solved sequentially, then converted to zero rates:
      DF_N = (1 + z/m)^{-N}.
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

            
