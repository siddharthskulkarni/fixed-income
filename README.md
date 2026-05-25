# fixed-income

Python library for **interest-rate and fixed-income analytics**, developed as part of UMass work on interest-rate derivatives pricing: Treasury and SOFR curves, parametric yield fits, a one-factor Hull–White short-rate model with SOFR futures convexity, and classical bond risk metrics.

## Capabilities

| Capability | Status |
|------------|--------|
| Bond pricing, YTM, cashflows | Implemented |
| Macaulay/modified duration, convexity, DV01 | Implemented |
| Treasury par → spot bootstrap | Implemented |
| Nelson–Siegel yield-curve fit | Implemented |
| Nelson–Siegel–Svensson (`NelsonSiegelSvensson`) fit | Implemented |
| Market data: Treasury.gov, FRED/NY Fed SOFR, CME settle CSV | Implemented (`[data]` extra) |
| SOFR OIS discount bootstrap (overnight compounding) | Implemented |
| IR forwards from OIS discount curve | Implemented |
| Hull–White 1F: futures convexity + calibration to CME settles | Implemented |
| Full OIS swap / multi-curve basis engine | Not implemented |
| Monte Carlo / SOFR options vol surface | Not implemented |

## Install

```bash
python3 -m pip install -e .
```

Optional extras:

```bash
python3 -m pip install -e '.[data]'   # requests, pandas, python-dotenv
python3 -m pip install -e '.[viz]'    # plotly, dash, matplotlib, …
python3 -m pip install -e '.[dev]'    # pytest, ruff, build
python3 -m pip install -e '.[dev,data,viz]'
```

## Quickstart

### Bond risk

```python
from fixed_income import Bond
from fixed_income.risk import macaulay, modified

b = Bond(c=0.05, F=100, T=10, P=95.0)
y = b.ytm()
print(macaulay(b, ytm=y), modified(b, ytm=y))
```

### Nelson–Siegel and NSS on Treasury par

```python
from fixed_income.data import TreasuryParCurveSource
from fixed_income import NelsonSiegel, NelsonSiegelSvensson

par = TreasuryParCurveSource().fetch()
t = [p.maturity_years for p in par.points]
r = [p.par_yield for p in par.points]

ns = NelsonSiegel(t=t, r=r)
ns.fit()
print("NS tau:", ns.tau)

nss = NelsonSiegelSvensson(t=t, r=r)
nss.fit()
print("NSS tau1/tau2:", nss.tau1, nss.tau2)
```

### SOFR OIS curve, forwards, and Hull–White calibration

Requires `FRED_API_KEY` in `.env` (or environment) and CME settlement CSVs under `data/raw/`. See [docs/data_access.md](docs/data_access.md).

```python
from datetime import date
from fixed_income.data import NyFedSofrSource, CmeSofrSettleBundleSource
from fixed_income import bootstrap_ois_from_sofr, HullWhite, forward_rate_from_discount

as_of = date(2026, 5, 22)
sofr = NyFedSofrSource().fetch(as_of=as_of)
ois = bootstrap_ois_from_sofr(sofr, pillars=[0.25, 0.5, 1.0, 2.0, 5.0])

fwd = forward_rate_from_discount(ois, 0.25, 1.0)
print(f"1y forward (from OIS): {fwd:.4%}")

bundle = CmeSofrSettleBundleSource(trade_date=as_of).fetch(as_of=as_of)
cal = HullWhite.calibrate_to_futures(bundle.sr3, ois)
print(f"HW a={cal.a:.4f}, sigma={cal.sigma:.4f}, RMSE={cal.rmse:.4f}")
```

### Ingest market data

```bash
python3 scripts/ingest_market_data.py --as-of 2026-05-22
```

## Examples

- [`examples/rates_models.ipynb`](examples/rates_models.ipynb) — Treasury par, NS/NSS fits, spot bootstrap, SOFR OIS, Hull–White calibration
- [`examples/bonds.ipynb`](examples/bonds.ipynb) — Bond price/yield, duration, convexity

## Dash dashboard

```bash
python3 -m pip install -e '.[viz]'
python3 -c "from fixed_income.viz import create_dash_app; create_dash_app().run_server(debug=True)"
```

The yield-curve panel supports optional **Nelson–Siegel** and **NSS** overlays on live Treasury par data.

## Methodology notes

- **Treasury bootstrap** — Par bonds priced at par; sequential discount factors (see `bootstrap_spot_curve`).
- **OIS bootstrap** — Compounded overnight SOFR (ACT/360) from published fixings; flat forward after the last fixing. Simplified single-curve model, not a full CSA/OIS swap bootstrap.
- **CME futures** — Settlement strips are manual quote-board pastes (`data/raw/cme_*_sofr_futures.csv`); one trade date per file.
- **Hull–White** — One-factor Gaussian short-rate model; analytic convexity adjustment on futures vs a discount-curve forward; `(a, σ)` calibrated to liquid SR3 settles with SciPy.

## Project layout

- `fixed_income/bond.py` — Bond pricing and YTM
- `fixed_income/risk.py` — Duration and convexity
- `fixed_income/rates/` — NS, NSS, Treasury bootstrap, OIS bootstrap, Hull–White
- `fixed_income/data/` — DataSource adapters (Treasury, FRED, NY Fed, CME CSV)
- `fixed_income/viz.py` — Plotly/Dash helpers
- `scripts/ingest_market_data.py` — Fetch and cache market inputs

## Build / test

```bash
./scripts/build_test.sh
python3 -m pytest tests/test_data.py tests/test_rates.py -q
```

## Data sources

See [docs/data_access.md](docs/data_access.md).
