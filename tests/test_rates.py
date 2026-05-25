import numpy as np
from datetime import date, timedelta

from fixed_income.data import CurvePoint, ParCurve, RateObservation, RateSeries
from fixed_income.rates import (
    DiscountCurve,
    HullWhite,
    NelsonSiegel,
    NelsonSiegelSvensson,
    USTreasurySpotCurve,
    bootstrap_ois_from_sofr,
    bootstrap_spot_curve,
    convexity_adjustment_rate,
    forward_rate_from_discount,
    hull_white_B,
)


def test_nelson_siegel_fit_recovers_parameters_reasonably():
    true_betas = np.array([0.03, -0.02, 0.01], dtype=float)
    true_tau = 1.7
    t = np.array([0.25, 0.5, 1, 2, 3, 5, 7, 10], dtype=float)

    l1, l2 = NelsonSiegel._loadings(t, true_tau)
    r = true_betas[0] + true_betas[1] * l1 + true_betas[2] * l2

    model = NelsonSiegel(t=t, r=r)
    model.fit(tau0=true_tau)

    assert np.isclose(model.tau, true_tau, rtol=0, atol=1e-6)
    assert np.allclose(model.betas, true_betas, rtol=0, atol=1e-6)


def test_nelson_siegel_svensson_fit_recovers_parameters_reasonably():
    true_betas = np.array([0.03, -0.02, 0.01, 0.005], dtype=float)
    true_tau1, true_tau2 = 1.2, 3.5
    t = np.array([0.25, 0.5, 1, 2, 3, 5, 7, 10, 15, 20], dtype=float)

    l1, l2, l3 = NelsonSiegelSvensson._loadings(t, true_tau1, true_tau2)
    r = true_betas[0] + true_betas[1] * l1 + true_betas[2] * l2 + true_betas[3] * l3

    model = NelsonSiegelSvensson(t=t, r=r)
    model.fit(tau1_0=true_tau1, tau2_0=true_tau2)

    assert np.isclose(model.tau1, true_tau1, rtol=0, atol=1e-5)
    assert np.isclose(model.tau2, true_tau2, rtol=0, atol=1e-5)
    assert np.allclose(model.betas, true_betas, rtol=0, atol=1e-5)


def test_nss_beats_ns_on_rich_curve():
    t = np.array([0.25, 0.5, 1, 2, 3, 5, 7, 10, 20, 30], dtype=float)
    r = np.array([0.04, 0.042, 0.045, 0.048, 0.05, 0.052, 0.053, 0.054, 0.055, 0.056])

    ns = NelsonSiegel(t=t, r=r)
    ns.fit()
    nss = NelsonSiegelSvensson(t=t, r=r)
    nss.fit()

    sse_ns = np.sum((ns.f(t) - r) ** 2)
    sse_nss = np.sum((nss.f(t) - r) ** 2)
    assert sse_nss <= sse_ns


def test_bootstrap_spot_curve_from_par_curve():
    points = (
        CurvePoint(maturity_years=0.5, par_yield=0.04),
        CurvePoint(maturity_years=1.0, par_yield=0.045),
        CurvePoint(maturity_years=1.5, par_yield=0.047),
    )
    curve = ParCurve(as_of=date(2026, 4, 16), points=points)

    maturities, spot_rates = bootstrap_spot_curve(curve, frequency=2)

    assert np.allclose(maturities, np.array([0.5, 1.0, 1.5], dtype=float))
    assert np.isclose(spot_rates[0], 0.04, rtol=0, atol=1e-12)

    df_0_5 = 1.0 / (1.0 + 0.04 / 2.0)
    df_1_0 = (1.0 - 0.045 / 2.0 * df_0_5) / (1.0 + 0.045 / 2.0)

    expected_spot_0 = 2.0 * (df_0_5 ** -1.0 - 1.0)
    expected_spot_1 = 2.0 * (df_1_0 ** -0.5 - 1.0)
    assert np.isclose(spot_rates[0], expected_spot_0, rtol=0, atol=1e-12)
    assert np.isclose(spot_rates[1], expected_spot_1, rtol=0, atol=1e-12)
    assert spot_rates[2] > spot_rates[1] > spot_rates[0]


def test_ustreasury_spot_curve_matrix_from_par_curve():
    points = (
        CurvePoint(maturity_years=0.5, par_yield=0.04),
        CurvePoint(maturity_years=1.0, par_yield=0.045),
        CurvePoint(maturity_years=1.5, par_yield=0.047),
    )
    curve = ParCurve(as_of=date(2026, 4, 16), points=points)
    spot_curve = USTreasurySpotCurve.from_par_curves(curve, frequency=2)

    assert spot_curve.matrix().shape == (1, 3)
    assert spot_curve.maturities.tolist() == [0.5, 1.0, 1.5]
    assert spot_curve.as_of_dates.tolist() == [date(2026, 4, 16)]


def test_bootstrap_ois_from_sofr_flat_rate():
    as_of = date(2026, 5, 22)
    obs = tuple(
        RateObservation(date=as_of - timedelta(days=i), rate=0.04)
        for i in range(5, -1, -1)
    )
    series = RateSeries(series_id="SOFR", as_of=as_of, observations=obs)
    curve = bootstrap_ois_from_sofr(series, pillars=[0.25, 0.5])

    assert curve.as_of == as_of
    assert len(curve.pillars) == 2
    assert curve.discount_factors[0] > curve.discount_factors[1] > 0
    assert curve.discount(0.0) == 1.0


def test_forward_rate_from_discount():
    curve = DiscountCurve(as_of=date(2026, 1, 1), pillars=(0.5, 1.0), discount_factors=(0.99, 0.97))
    fwd = forward_rate_from_discount(curve, 0.5, 1.0)
    assert fwd > 0


def test_hull_white_B_limit():
    assert np.isclose(hull_white_B(0, 1.0, 0.5), (1 - np.exp(-0.5)) / 0.5)


def test_convexity_increases_with_sigma():
    ca_lo = convexity_adjustment_rate(0.1, 0.005, 1.0)
    ca_hi = convexity_adjustment_rate(0.1, 0.02, 1.0)
    assert ca_hi > ca_lo >= 0


def test_hull_white_futures_convexity_lowers_price_vs_naive():
    as_of = date(2026, 5, 22)
    curve = DiscountCurve(as_of=as_of, pillars=(0.25, 1.0, 2.0), discount_factors=(0.995, 0.98, 0.96))
    hw = HullWhite(curve, a=0.1, sigma=0.01)
    naive = 100.0 - forward_rate_from_discount(curve, 0.1, 1.0) * 100.0
    adjusted = hw.futures_settle_price(0.1, 1.0)
    assert adjusted < naive


def test_hull_white_calibration_roundtrip():
    from fixed_income.data.types import FuturesSettle, FuturesSettleCurve

    as_of = date(2026, 5, 22)
    curve = DiscountCurve(
        as_of=as_of,
        pillars=(0.25, 0.5, 1.0, 2.0),
        discount_factors=(0.998, 0.995, 0.99, 0.97),
    )
    true_a, true_sigma = 0.15, 0.012
    hw_true = HullWhite(curve, true_a, true_sigma)

    settles = []
    for month in ("JUN 26", "SEP 26", "DEC 26", "MAR 27"):
        stub = FuturesSettle(
            product="SR3",
            contract_month=month,
            settle=0.0,
            symbol="SR3X0",
            volume=1000,
        )
        price = hw_true.futures_settle_for_contract(stub)
        settles.append(
            FuturesSettle(
                product="SR3",
                contract_month=month,
                settle=price,
                symbol=f"SR3_{month.replace(' ', '')}",
                volume=1000,
            )
        )
    futures = FuturesSettleCurve(as_of=as_of, product="SR3", settles=tuple(settles))
    result = HullWhite.calibrate_to_futures(
        futures,
        curve,
        min_volume=0,
        sigma_bounds=(0.001, 0.05),
    )

    assert result.rmse < 0.01
    assert result.a > 0 and result.sigma > 0
