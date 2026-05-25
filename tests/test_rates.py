import numpy as np
from datetime import date

from fixed_income.data import CurvePoint, ParCurve
from fixed_income.rates import NelsonSiegel, USTreasurySpotCurve, bootstrap_spot_curve


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
    df_1_5 = (1.0 - 0.047 / 2.0 * (df_0_5 + df_1_0)) / (1.0 + 0.047 / 2.0)

    expected_spot = np.array([
        2.0 * (df_0_5 ** -1.0 - 1.0),
        2.0 * (df_1_0 ** -0.5 - 1.0),
        2.0 * (df_1_5 ** -1.0 / 3.0 - 1.0),
    ], dtype=float)
    assert np.allclose(spot_rates, expected_spot, rtol=1e-12)


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

