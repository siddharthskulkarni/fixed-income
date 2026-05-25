import numpy as np

from fixed_income.bond import Bond
from fixed_income.risk import convexity, macaulay, modified, money


def test_zero_coupon_duration_and_convexity():
    y = 0.03
    f = 100.0
    t = 5
    p = f / (1.0 + y) ** t
    b = Bond(c=0.0, F=f, T=t, P=p)

    assert np.isclose(macaulay(b, ytm=y), float(t), atol=1e-12)
    assert np.isclose(modified(b, ytm=y), float(t) / (1.0 + y), atol=1e-12)
    assert np.isclose(money(b, ytm=y), modified(b, ytm=y) * p, atol=1e-10)

    expected_conv = float(t) * (float(t) + 1.0) / (1.0 + y) ** 2
    assert np.isclose(convexity(b, ytm=y), expected_conv, atol=1e-12)

