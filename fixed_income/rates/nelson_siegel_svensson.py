import numpy as np
import scipy as sp


class NelsonSiegelSvensson:
    """Nelson-Siegel-Svensson parametric yield curve (six parameters)."""

    def __init__(self, t, r):
        self.t = np.asarray(t, dtype=float)
        self.r = np.asarray(r, dtype=float)
        self.betas = None
        self.tau1 = None
        self.tau2 = None

    @staticmethod
    def _loadings(t, tau1, tau2):
        t = np.asarray(t, dtype=float)
        tau1 = float(tau1)
        tau2 = float(tau2)
        if tau1 <= 0 or tau2 <= 0:
            raise ValueError("tau1 and tau2 must be positive")

        x1 = t / tau1
        x2 = t / tau2
        with np.errstate(divide="ignore", invalid="ignore"):
            l1 = np.where(x1 == 0.0, 1.0, (1.0 - np.exp(-x1)) / x1)
        l2 = l1 - np.exp(-x1)
        l3 = np.where(x2 == 0.0, 0.0, (1.0 - np.exp(-x2)) / x2 - np.exp(-x2))
        return l1, l2, l3

    def f(self, t):
        if self.betas is None or self.tau1 is None or self.tau2 is None:
            raise RuntimeError("Model is not fit yet; call fit() first.")
        l1, l2, l3 = self._loadings(t, self.tau1, self.tau2)
        b0, b1, b2, b3 = self.betas
        return b0 + b1 * l1 + b2 * l2 + b3 * l3

    def fit(self, tau1_0=1.0, tau2_0=3.0):
        x = self.t
        y = self.r
        if x.ndim != 1 or y.ndim != 1 or x.shape[0] != y.shape[0]:
            raise ValueError("t and r must be 1D arrays of the same length")
        if x.size < 4:
            raise ValueError("NSS fit requires at least four maturity points")
        if np.any(x < 0):
            raise ValueError("maturities must be non-negative")

        def residuals(params):
            b0, b1, b2, b3, log_t1, log_t2 = params
            l1, l2, l3 = self._loadings(x, float(np.exp(log_t1)), float(np.exp(log_t2)))
            y_hat = b0 + b1 * l1 + b2 * l2 + b3 * l3
            return y_hat - y

        b0_0 = float(y[-1]) if y.size else 0.0
        x0 = np.array([b0_0, -0.01, 0.01, 0.01, np.log(float(tau1_0)), np.log(float(tau2_0))], dtype=float)
        res = sp.optimize.least_squares(residuals, x0=x0, method="trf")
        b0, b1, b2, b3, log_t1, log_t2 = res.x
        self.betas = np.array([b0, b1, b2, b3], dtype=float)
        self.tau1 = float(np.exp(log_t1))
        self.tau2 = float(np.exp(log_t2))
