import numpy as np
import scipy as sp


class NelsonSiegel:
    def __init__(self, t, r):
        """
        Initialize the Nelson-Siegel model with its parameters.

        Parameters:
        t (np.array): Maturities (in years).
        r (np.array): Yields in decimal (e.g. 0.045 for 4.5%).
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
        if self.betas is None or self.tau is None:
            raise RuntimeError("Model is not fit yet; call fit() first.")
        l1, l2 = self._loadings(t, self.tau)
        beta0, beta1, beta2 = self.betas
        return beta0 + beta1 * l1 + beta2 * l2

    def fit(self, tau0=1.0):
        x = self.t
        y = self.r
        if x.ndim != 1 or y.ndim != 1 or x.shape[0] != y.shape[0]:
            raise ValueError("t and r must be 1D arrays of the same length")
        if np.any(x < 0):
            raise ValueError("maturities must be non-negative")

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
