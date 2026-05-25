import pytest
from datetime import date

from fixed_income.bond import Bond
from fixed_income.data import CurvePoint, ParCurve
from fixed_income.viz import (
    bond_cashflow_figure,
    bond_price_yield_figure,
    create_dash_app,
    create_jupyter_dash_app,
    yield_curve_figure,
)


def test_yield_curve_figure_returns_plotly_figure():
    pytest.importorskip("plotly")
    points = (
        CurvePoint(maturity_years=0.5, par_yield=0.04),
        CurvePoint(maturity_years=1.0, par_yield=0.045),
        CurvePoint(maturity_years=2.0, par_yield=0.055),
    )
    curve = ParCurve(as_of=date(2026, 4, 17), points=points)
    fig = yield_curve_figure(curve)

    assert hasattr(fig, "data")
    assert len(fig.data) >= 1
    assert fig.layout.title.text is not None


def test_bond_cashflow_figure_returns_plotly_figure():
    pytest.importorskip("plotly")
    bond = Bond(c=0.05, F=100, T=5, P=96.0, m=2)
    fig = bond_cashflow_figure(bond)

    assert hasattr(fig, "data")
    assert len(fig.data) == 1
    assert fig.layout.title.text is not None


def test_bond_price_yield_figure_returns_plotly_figure():
    pytest.importorskip("plotly")
    bond = Bond(c=0.05, F=100, T=5, P=96.0, m=2)
    fig = bond_price_yield_figure(bond, yields=[0.01, 0.02, 0.03])

    assert hasattr(fig, "data")
    assert len(fig.data) == 1
    assert fig.layout.title.text is not None


def test_create_dash_app_returns_dash_app_instance():
    pytest.importorskip("dash")
    app = create_dash_app()

    assert app is not None
    assert hasattr(app, "layout")


def test_create_jupyter_dash_app_returns_jupyter_dash_app_instance():
    pytest.importorskip("dash")
    pytest.importorskip("jupyter_dash")
    app = create_jupyter_dash_app()

    assert app is not None
    assert hasattr(app, "layout")
