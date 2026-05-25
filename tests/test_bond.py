import numpy as np

from fixed_income.bond import Bond


def test_ytm_zero_coupon_recovers_rate():
    y = 0.05
    f = 100.0
    t = 2
    p = f / (1.0 + y) ** t
    b = Bond(c=0.0, F=f, T=t, P=p)
    assert np.isclose(b.ytm(), y, rtol=0, atol=1e-10)


def test_ytm_coupon_bond_recovers_rate():
    y = 0.04
    f = 100.0
    c = 0.05
    t = 3
    # PV of coupon bond with coupon each period and principal at maturity.
    coupon = c * f
    p = coupon / (1.0 + y) ** 1 + coupon / (1.0 + y) ** 2 + (coupon + f) / (1.0 + y) ** 3
    b = Bond(c=c, F=f, T=t, P=p)
    assert np.isclose(b.ytm(), y, rtol=0, atol=1e-10)


def test_pv_intermediate_time_zero_coupon_matches_discounting():
    y = 0.05
    f = 100.0
    t = 5
    p = f / (1.0 + y) ** t
    b = Bond(c=0.0, F=f, T=t, P=p)

    # At time 2.5, there are 2.5 years left to maturity.
    pv = b.pv(t=2, s=0.5)
    expected = f / (1.0 + y) ** (t - 2.5)
    assert np.isclose(pv, expected, rtol=0, atol=1e-12)


def test_pv_intermediate_time_coupon_bond_matches_direct_formula():
    y = 0.04
    f = 100.0
    c = 0.05
    t = 4
    coupon = c * f
    p = coupon / (1.0 + y) ** 1 + coupon / (1.0 + y) ** 2 + coupon / (1.0 + y) ** 3 + (coupon + f) / (1.0 + y) ** 4
    b = Bond(c=c, F=f, T=t, P=p)

    # PV at time 1.25: remaining cashflows at times 2,3,4 are discounted by (2-1.25),(3-1.25),(4-1.25)
    pv = b.pv(t=1, s=0.25)
    expected = (
        coupon / (1.0 + y) ** 0.75
        + coupon / (1.0 + y) ** 1.75
        + (coupon + f) / (1.0 + y) ** 2.75
    )
    assert np.isclose(pv, expected, rtol=0, atol=1e-10)


def test_ytm_semiannual_coupon_bond_recovers_rate():
    y = 0.04
    f = 100.0
    c = 0.05
    t = 3
    freq = 2
    coupon = c * f / freq
    periods = int(t * freq)
    p = sum(coupon / (1.0 + y / freq) ** i for i in range(1, periods))
    p += (coupon + f) / (1.0 + y / freq) ** periods

    b = Bond(c=c, F=f, T=t, P=p, m=freq)
    assert np.isclose(b.ytm(), y, rtol=0, atol=1e-10)


def test_ytm_quarterly_coupon_bond_recovers_rate():
    y = 0.03
    f = 100.0
    c = 0.06
    t = 2
    freq = 4
    coupon = c * f / freq
    periods = int(t * freq)
    p = sum(coupon / (1.0 + y / freq) ** i for i in range(1, periods))
    p += (coupon + f) / (1.0 + y / freq) ** periods

    b = Bond(c=c, F=f, T=t, P=p, m=freq)
    assert np.isclose(b.ytm(), y, rtol=0, atol=1e-10)


def test_cashflows_are_generated_for_years_to_maturity():
    b = Bond(c=0.05, F=100.0, T=1.5, P=0.0, m=2)
    t, cf = b.cashflows()

    assert np.allclose(t, np.array([0.5, 1.0, 1.5], dtype=float))
    assert np.allclose(cf, np.array([2.5, 2.5, 102.5], dtype=float))


def test_pv_intermediate_time_semiannual_coupon_matches_direct_formula():
    y = 0.04
    f = 100.0
    c = 0.05
    t = 3
    freq = 2
    coupon = c * f / freq
    periods = int(t * freq)
    p = sum(coupon / (1.0 + y / freq) ** i for i in range(1, periods))
    p += (coupon + f) / (1.0 + y / freq) ** periods

    b = Bond(c=c, F=f, T=t, P=p, m=freq)
    pv = b.pv(t=1, s=0.25)

    expected = (
        coupon / (1.0 + y / freq) ** 0.5
        + coupon / (1.0 + y / freq) ** 1.5
        + coupon / (1.0 + y / freq) ** 2.5
        + (coupon + f) / (1.0 + y / freq) ** 3.5
    )
    assert np.isclose(pv, expected, rtol=0, atol=1e-10)
