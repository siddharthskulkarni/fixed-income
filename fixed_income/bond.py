import numpy as np
import scipy as sp

class Bond():
    def __init__(self, C, F, T, P):
        """
        Initialize a bond with its parameters.
        
        Parameters:
        C (float): Coupon rate (per period).
        F (float): Face value of the bond.
        T (int): Time periods to maturity.
        P (float): Price of the bond.
        """
        self.C = C
        self.F = F
        self.T = T
        self.P = P
        self._cf = None
        self._t = None

    def f(self, r):
        """
        Auxiliary function to calculate present value of all cashflows for specified 
        interest rate r.
        
        Parameters:
        r (float): Discount rate.
        
        Returns:
        float: The present value of the bond given r.
        """
        self._cf = np.array([self.C * self.F] * self.T + [self.F])
        self._cf = self._cf[self._cf != 0]
        self._t = np.array(np.arange(1, len(self._cf)).tolist() + [self.T])
        fr = np.sum(self._cf / (1 + r) ** self._t)
        return fr
    
    def df(self, r):
        """
        Auxiliary function to calculate the derivative of present value function f.
        
        Parameters:
        r (float): Discount rate.
        
        Returns:
        float: The derivative of the present value function given r.
        """
        self._cf = np.array([self.C * self.F] * self.T + [self.F])
        self._cf = self._cf[self._cf != 0]
        self._t = np.array(np.arange(1, len(self._cf)).tolist() + [self.T])
        dfr = -np.sum(self._t * self._cf / (1 + r) ** (self._t + 1))
        return dfr

    def ytm(self):
        """
        Calculate the Yield to Maturity (YTM) of the bond.
        
        Returns:
        float: The YTM of the bond.
        """
        _ytm = sp.optimize.newton(lambda r: self.f(r) - self.P, 0)
        return _ytm

    def __repr__(self):
        return f"Bond(C={self.C}, F={self.F}, T={self.T}, P={self.P})"