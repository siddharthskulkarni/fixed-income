# fixed-income

Python library for analysis of fixed income instruments.

## Install (editable)

```bash
python3 -m pip install -e .
```

With optional data dependencies (Treasury.gov + FRED):

```bash
python3 -m pip install -e '.[data]'
```

With dev tooling (pytest/ruff/build):

```bash
python3 -m pip install -e '.[dev]'
```

With visualization tooling for notebooks/examples (pandas/matplotlib/seaborn/ipykernel/plotly/dash/jupyter-dash):

```bash
python3 -m pip install -e '.[viz]'
```

Common “all-in” dev install:

```bash
python3 -m pip install -e '.[dev,data,viz]'
```

## Quickstart

```python
from fixed_income import Bond
from fixed_income.risk import macaulay, modified

b = Bond(c=0.05, F=100, T=10, P=95.0)
y = b.ytm()
d_mac = macaulay(b, ytm=y)
d_mod = modified(b, ytm=y)
```

## Dash dashboard support

Install visualization extras:

```bash
python3 -m pip install -e '.[viz]'
```

Run a standalone dashboard:

```python
from fixed_income.viz import create_dash_app

app = create_dash_app()
app.run_server(debug=True)
```

Run in a Jupyter notebook:

```python
from fixed_income.viz import create_jupyter_dash_app

app = create_jupyter_dash_app()
app.run_server(mode="inline", debug=True)
```

## Build / test scripts

- Test build: `./scripts/build_test.sh`
- Prod build: `./scripts/build_prod.sh`

## Data sources

See `docs/data_access.md` for Treasury par, NY Fed / FRED SOFR, and CME SOFR futures settlement CSVs.

Quick ingest (requires `.env` with `FRED_API_KEY` and `data/raw/cme_*_sofr_futures.csv`):

```bash
python3 -m pip install -e '.[data]'
python3 scripts/ingest_market_data.py --as-of 2026-05-22
```
