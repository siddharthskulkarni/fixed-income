import numpy as np
import scipy as sp

class Bond:
    def __init__(self, c, F, T, P, m=1):
        """
        Initialize a bond with its parameters.

        Parameters:
        c (float): Annual coupon rate as a decimal fraction of par value.
        F (float): Face (par) value of the bond.
        T (float): Years to maturity.
        P (float): Price of the bond.
        m (int): Coupon payments per year.
        """
        if float(T) <= 0:
            raise ValueError("T must be positive")
        if int(m) != m or m < 1:
            raise ValueError("m must be a positive integer")

        self.c = float(c)
        if self.c < 0.0 or self.c > 1.0:
            raise ValueError("c must be a decimal fraction between 0.0 and 1.0")

        self.F = float(F)
        self.T = float(T)
        self.P = float(P)
        self.m = int(m)
        self._cf = None
        self._t = None

        N = self.T * self.m
        if not np.isclose(N, round(N)):
            raise ValueError("T * m must be an integer number of periods")

        self._periods = int(round(N))

    def pv(self, t, s=0.0):
        """
        Present value of all future cashflows at an intermediate time.

        Parameters:
        t (int): Whole number of years elapsed (must satisfy 0 <= t < T).
        s (float): Fraction of the current coupon period remaining
            (must satisfy 0 <= s < 1).

        Returns:
        float: Present value at time (t + s) of all remaining cashflows, discounted
            using this bond's own yield-to-maturity.

        Notes:
        - `T` is in years; `m` is coupon payments per year.
        - `y` is annual yield to maturity.
        - The per-period discount rate is `y/m`.
        - `N = m * T` is the total number of coupon periods.
        - PV at time t+s is computed as: sum_{i: t_i > t+s} CF_i / (1 + y/m)^{n_i - (t+s)*m}.
        """
        if not isinstance(t, (int, np.integer)):
            raise TypeError("t must be an integer number of years elapsed")
        t_int = int(t)
        if t_int < 0 or t_int >= self.T:
            raise ValueError("t must satisfy 0 <= t < T")

        s_float = float(s)
        if not (0.0 <= s_float < 1.0):
            raise ValueError("s must satisfy 0 <= s < 1")

        current_time = float(t_int) + s_float
        y = self.ytm()

        t_vals, cf = self.cashflows()
        future_mask = t_vals > current_time
        if not np.any(future_mask):
            return 0.0

        remaining_times = t_vals[future_mask]
        time_deltas = remaining_times - current_time
        return float(np.sum(cf[future_mask] / (1.0 + y) ** time_deltas))

    def cashflows(self):
        """
        Return bond cashflows and their payment times (in years).

        Returns:
        (np.ndarray, np.ndarray): (t, cf) where t is coupon payment times in years
        and cf are cashflows at those times.

        Notes:
        - Annual coupon rate is c.
        - Face value is face.
        - Per-period coupon payment is C = c * face / m.
        - Total periods N = m * T.
        - Final cashflow at maturity includes principal: face + C.
        """
        if self.T <= 0:
            raise ValueError("T must be positive")

        C = self.c * self.F / self.m
        if abs(C) < 1e-15:
            cf = np.array([float(self.F)], dtype=float)
            t = np.array([self.T], dtype=float)
        else:
            if self._periods == 1:
                cf = np.array([float(self.F * (1 + self.c))], dtype=float)
                t = np.array([self.T], dtype=float)
            else:
                cf = np.array(
                    [C] * (self._periods - 1) + [float(self.F * (1 + self.c))],
                    dtype=float,
                )
                t = np.arange(1, self._periods + 1, dtype=float) / self.m

        self._cf = cf
        self._t = t
        return t, cf

    def f(self, r):
        """
        Auxiliary function to calculate present value of all cashflows for a given
        annual discount rate `r`.

        Parameters:
        r (float): Annual discount rate.

        Returns:
        float: The present value of the bond given r, using periodic compounding.

        Notes:
        - Let `y = r` be the annual discount rate.
        - If payment times are t_i years, annual compounding discounts each cashflow by
          (1 + y)^{t_i}.
        - f(r) = sum_{i=1}^N CF_i / (1 + y)^{t_i}.
        """
        t, cf = self.cashflows()
        return float(np.sum(cf / (1.0 + float(r)) ** t))
    
    def df(self, r):
        """
        Auxiliary function to calculate the derivative of the present value function f
        with respect to the annual discount rate `r`.

        Parameters:
        r (float): Annual discount rate.

        Returns:
        float: The derivative of the present value function given r.

        Notes:
        - d/dr [CF * (1 + r)^{-t_i}] = -CF * t_i * (1 + r)^{-t_i-1}.
        - Here t_i is the payment time in years.
        """
        t, cf = self.cashflows()
        return float(-np.sum(t * cf / (1.0 + float(r)) ** (t + 1)))

    def ytm(self):
        """
        Calculate the annual Yield to Maturity (YTM) of the bond.

        Returns:
        float: The annualized YTM of the bond.
        """
        if self.P is None or float(self.P) <= 0:
            raise ValueError("P must be a positive price")

        target = float(self.P)

        def g(r):
            return self.f(r) - target

        try:
            return float(sp.optimize.newton(g, x0=0.05, fprime=self.df, tol=1e-12, maxiter=100))
        except Exception:
            lo = -0.9999
            hi = 0.5
            flo = g(lo)
            fhi = g(hi)
            for _ in range(60):
                if flo == 0:
                    return lo
                if fhi == 0:
                    return hi
                if flo * fhi < 0:
                    return float(sp.optimize.brentq(g, lo, hi, maxiter=200, xtol=1e-12))
                hi *= 1.5
                fhi = g(hi)
            raise RuntimeError("Failed to bracket a root for YTM; check inputs.")

    def __repr__(self):
        return (
            f"Bond(c={self.c}, F={self.F}, T={self.T}, "
            f"P={self.P}, m={self.m})"
        )
