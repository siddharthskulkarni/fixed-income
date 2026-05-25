from __future__ import annotations

from datetime import date
from typing import Any, Iterable, Optional, Sequence

import numpy as np

from fixed_income.bond import Bond
from fixed_income.data import CurvePoint, DataSource, ParCurve, TreasuryParCurveSource
from fixed_income.rates import NelsonSiegel, NelsonSiegelSvensson


def _require_plotly() -> Any:
    try:
        import plotly.graph_objects as go
    except Exception as exc:
        raise ImportError(
            "Plotly is required for fixed_income.viz. Install fixed-income[viz] to use dashboards and figures."
        ) from exc
    return go


def _require_dash(use_jupyter: bool = False) -> tuple[Any, Any, Any, Any, Any]:
    try:
        if use_jupyter:
            from jupyter_dash import JupyterDash
            from dash import dcc, html, Input, Output
            return JupyterDash, dcc, html, Input, Output
        from dash import Dash, dcc, html, Input, Output
        return Dash, dcc, html, Input, Output
    except Exception as exc:
        extra = "jupyter-dash" if use_jupyter else "dash"
        raise ImportError(
            f"{extra} is required for fixed_income.viz dashboards. Install fixed-income[viz] to use this feature."
        ) from exc


def _sample_par_curve() -> ParCurve:
    return ParCurve(
        as_of=date.today(),
        points=(
            CurvePoint(maturity_years=0.5, par_yield=0.04),
            CurvePoint(maturity_years=1.0, par_yield=0.045),
            CurvePoint(maturity_years=2.0, par_yield=0.055),
            CurvePoint(maturity_years=5.0, par_yield=0.065),
            CurvePoint(maturity_years=10.0, par_yield=0.075),
            CurvePoint(maturity_years=30.0, par_yield=0.083),
        ),
    )


def _load_par_curve(source: Optional[DataSource] = None, as_of: Optional[date] = None) -> ParCurve:
    if source is None:
        return _sample_par_curve()
    if not isinstance(source, DataSource):
        raise TypeError("curve_source must be a DataSource or None")
    return source.fetch(as_of=as_of)


def _empty_figure(title: str) -> Any:
    go = _require_plotly()
    fig = go.Figure()
    fig.update_layout(
        title=title,
        annotations=[
            {
                "text": "No data available",
                "showarrow": False,
                "x": 0.5,
                "y": 0.5,
                "xref": "paper",
                "yref": "paper",
                "font": {"size": 16},
            }
        ],
    )
    return fig


def yield_curve_figure(
    par_curve: ParCurve,
    show_nelson_siegel: bool = True,
    show_nelson_siegel_svensson: bool = False,
    ns_tau: float = 1.0,
    ns_points: int = 200,
) -> Any:
    """Build a Plotly figure for a Treasury par yield curve."""
    go = _require_plotly()

    maturities = np.asarray([p.maturity_years for p in par_curve.points], dtype=float)
    yields = np.asarray([p.par_yield for p in par_curve.points], dtype=float)

    fig = go.Figure(
        data=[
            go.Scatter(
                x=maturities,
                y=yields,
                mode="markers+lines",
                name="Par yields",
                marker=dict(size=8),
                hovertemplate="%{x:.2f} yr: %{y:.2%}<extra></extra>",
            )
        ]
    )

    if show_nelson_siegel and maturities.size >= 2:
        model = NelsonSiegel(t=maturities, r=yields)
        model.fit(tau0=ns_tau)
        x_fit = np.linspace(np.min(maturities), np.max(maturities), ns_points)
        y_fit = model.f(x_fit)
        fig.add_trace(
            go.Scatter(
                x=x_fit,
                y=y_fit,
                mode="lines",
                name="Nelson-Siegel fit",
                line=dict(dash="dash"),
                hovertemplate="%{x:.2f} yr: %{y:.2%}<extra></extra>",
            )
        )

    if show_nelson_siegel_svensson and maturities.size >= 4:
        nss = NelsonSiegelSvensson(t=maturities, r=yields)
        nss.fit()
        x_fit = np.linspace(np.min(maturities), np.max(maturities), ns_points)
        y_nss = nss.f(x_fit)
        fig.add_trace(
            go.Scatter(
                x=x_fit,
                y=y_nss,
                mode="lines",
                name="Nelson-Siegel-Svensson fit",
                line=dict(dash="dot"),
                hovertemplate="%{x:.2f} yr: %{y:.2%}<extra></extra>",
            )
        )

    fig.update_layout(
        title=f"Treasury Par Yield Curve ({par_curve.as_of.isoformat()})",
        xaxis_title="Maturity (years)",
        yaxis_title="Par yield",
        yaxis_tickformat=".2%",
        template="plotly_white",
    )
    return fig


def bond_cashflow_figure(bond: Bond) -> Any:
    """Build a Plotly figure for a bond's future cashflows."""
    go = _require_plotly()
    t, cf = bond.cashflows()

    fig = go.Figure(
        data=[
            go.Bar(
                x=t,
                y=cf,
                name="Cashflows",
                marker_color="#2a9d8f",
                hovertemplate="%{x:.2f} yr: $%{y:.2f}<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        title=f"Cashflow Schedule for Bond (T={bond.T} yr)",
        xaxis_title="Time (years)",
        yaxis_title="Cashflow",
        template="plotly_white",
    )
    return fig


def bond_price_yield_figure(bond: Bond, yields: Optional[Sequence[float]] = None) -> Any:
    """Build a Plotly figure showing bond price sensitivity across yields."""
    go = _require_plotly()
    if yields is None:
        ytm = bond.ytm()
        lower = max(0.0, ytm - 0.05)
        upper = ytm + 0.05
        yields = np.linspace(lower, upper, 101)
    else:
        yields = np.asarray(list(yields), dtype=float)
        if yields.ndim != 1 or yields.size < 2:
            raise ValueError("yields must be a sequence of at least two values")

    prices = np.asarray([bond.f(y) for y in yields], dtype=float)
    fig = go.Figure(
        data=[
            go.Scatter(
                x=yields,
                y=prices,
                mode="lines",
                name="Price-yield",
                line=dict(color="#e76f51"),
                hovertemplate="%{x:.2%}: $%{y:.2f}<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        title="Bond Price / Yield Relationship",
        xaxis_title="Yield",
        yaxis_title="Price",
        xaxis_tickformat=".2%",
        template="plotly_white",
    )
    return fig


def create_dash_app(
    use_jupyter: bool = False,
    curve_source: Optional[DataSource] = None,
    as_of: Optional[date] = None,
) -> Any:
    """Create a Dash app for exploring yield curves and bond analytics."""
    DashClass, dcc, html, Input, Output = _require_dash(use_jupyter=use_jupyter)
    app = DashClass(__name__)
    app.title = "fixed-income Dashboard"

    app.layout = html.Div(
        [
            html.H1("Fixed Income Dashboard"),
            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Coupon rate (decimal):"),
                            dcc.Input(id="coupon-input", type="number", value=0.05, step=0.001),
                            html.Br(),
                            html.Label("Face value:"),
                            dcc.Input(id="face-value-input", type="number", value=100.0, step=1.0),
                            html.Br(),
                            html.Label("Maturity (years):"),
                            dcc.Input(id="maturity-input", type="number", value=10.0, step=0.5),
                            html.Br(),
                            html.Label("Price:"),
                            dcc.Input(id="price-input", type="number", value=95.0, step=0.1),
                            html.Br(),
                            html.Label("Coupon frequency:"),
                            dcc.Input(id="frequency-input", type="number", value=2, step=1),
                            html.Br(),
                            dcc.Checklist(
                                id="show-ns-fit",
                                options=[
                                    {"label": "Nelson-Siegel fit", "value": "ns"},
                                    {"label": "Nelson-Siegel-Svensson fit", "value": "nss"},
                                ],
                                value=["ns"],
                            ),
                            html.Div(id="dashboard-status", style={"marginTop": "1rem", "color": "#d62828"}),
                        ],
                        style={"width": "25%", "minWidth": "260px", "padding": "1rem", "borderRight": "1px solid #e0e0e0"},
                    ),
                    html.Div(
                        [
                            dcc.Graph(id="yield-curve-graph"),
                            dcc.Graph(id="cashflow-graph"),
                            dcc.Graph(id="price-yield-graph"),
                        ],
                        style={"width": "70%", "padding": "1rem"},
                    ),
                ],
                style={"display": "flex", "flexWrap": "wrap"},
            ),
        ]
    )

    @app.callback(
        [
            Output("yield-curve-graph", "figure"),
            Output("cashflow-graph", "figure"),
            Output("price-yield-graph", "figure"),
            Output("dashboard-status", "children"),
        ],
        [
            Input("coupon-input", "value"),
            Input("face-value-input", "value"),
            Input("maturity-input", "value"),
            Input("price-input", "value"),
            Input("frequency-input", "value"),
            Input("show-ns-fit", "value"),
        ],
    )
    def update_dashboard(
        coupon_value: float,
        face_value: float,
        maturity_value: float,
        price_value: float,
        frequency_value: float,
        show_ns_values: list[str],
    ) -> tuple[Any, Any, Any, str]:
        status_parts: list[str] = []
        curve_fig = _empty_figure("Yield curve")
        cashflow_fig = _empty_figure("Bond cashflows")
        price_fig = _empty_figure("Price / yield")

        try:
            curve = _load_par_curve(curve_source, as_of=as_of)
            curve_fig = yield_curve_figure(
                par_curve=curve,
                show_nelson_siegel="ns" in (show_ns_values or []),
                show_nelson_siegel_svensson="nss" in (show_ns_values or []),
            )
        except Exception as exc:
            status_parts.append(f"Curve load failed: {exc}")

        try:
            bond = Bond(
                c=float(coupon_value),
                F=float(face_value),
                T=float(maturity_value),
                P=float(price_value),
                m=int(round(float(frequency_value))),
            )
            cashflow_fig = bond_cashflow_figure(bond)
            price_fig = bond_price_yield_figure(bond)
        except Exception as exc:
            status_parts.append(f"Bond input failed: {exc}")

        return curve_fig, cashflow_fig, price_fig, " \n".join(status_parts)

    return app


def create_jupyter_dash_app(
    curve_source: Optional[DataSource] = None,
    as_of: Optional[date] = None,
) -> Any:
    """Create a JupyterDash app for notebook use."""
    return create_dash_app(use_jupyter=True, curve_source=curve_source, as_of=as_of)
