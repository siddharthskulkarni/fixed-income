# Data access

Install optional dependencies:

```bash
python3 -m pip install -e '.[data]'
```

## Environment (FRED)

1. Create a FRED API key at [fred.stlouisfed.org](https://fred.stlouisfed.org) (Account → API Keys).
2. Copy [`.env.example`](../.env.example) to `.env` and set `FRED_API_KEY`.
3. The library loads `fixed-income/.env` automatically (via `python-dotenv` when installed) without overriding existing shell variables.

```bash
export FRED_API_KEY='your_key_here'  # optional if .env is set
```

## Treasury par curve (Treasury.gov)

```python
from fixed_income.data import TreasuryParCurveSource

src = TreasuryParCurveSource()
curve = src.fetch()          # latest available in current year
points = curve.as_dict()     # {maturity_years: par_yield_decimal}
```

## SOFR fixings (NY Fed + FRED)

**NY Fed** (authoritative overnight SOFR, decimal rates):

```python
from datetime import date
from fixed_income.data import NyFedSofrSource

series = NyFedSofrSource().fetch(as_of=date(2026, 5, 22))
print(series.as_of_value())  # e.g. 0.0351
```

**FRED** (history; `FredSofrSource` converts percent → decimal):

```python
from fixed_income.data import FredSofrSource, FredSofrIndexSource

hist = FredSofrSource().fetch_history(as_of=date(2026, 5, 22), lookback_days=90)
index_pt = FredSofrIndexSource().fetch(as_of=date(2026, 5, 22))
```

## CME SOFR futures settlements (manual CSV)

Paste the CME quote board for a single trade date into:

- `data/raw/cme_1m_sofr_futures.csv` (SR1 / 1-month)
- `data/raw/cme_3m_sofr_futures.csv` (SR3 / 3-month)

Expected header:

```text
Month,Open,High,Low,Last,Change,Settle,Est. Volume,Prior day OI
```

The **`Settle`** column is used for pricing (IMM index ~96.xx). **`Prior day OI`** is ignored for valuation. Prices with suffix letters (`95.9900B`) are parsed correctly.

**Trade date is not in the file** — pass it when loading:

```python
from datetime import date
from fixed_income.data import CmeSofrSettleBundleSource

bundle = CmeSofrSettleBundleSource(trade_date=date(2026, 5, 22)).fetch(as_of=date(2026, 5, 22))
print(bundle.sr1.settles[0])  # front contract SR1 strip
print(bundle.sr3.settles[0])  # front contract SR3 strip
```

To add another date, paste new strips and use a matching `trade_date` / `as_of`.

## SOFR OIS bootstrap and Hull–White

After loading SOFR history, build an OIS discount curve and calibrate Hull–White to futures:

```python
from datetime import date
from fixed_income.data import NyFedSofrSource, CmeSofrSettleBundleSource
from fixed_income.rates import bootstrap_ois_from_sofr, HullWhite

as_of = date(2026, 5, 22)
sofr = NyFedSofrSource().fetch(as_of=as_of)
ois = bootstrap_ois_from_sofr(sofr, pillars=[0.25, 0.5, 1.0, 2.0])
bundle = CmeSofrSettleBundleSource(trade_date=as_of).fetch(as_of=as_of)
cal = HullWhite.calibrate_to_futures(bundle.sr3, ois)
```

## Ingest script

```bash
cd fixed-income
python3 scripts/ingest_market_data.py --as-of 2026-05-22
```

Options: `--cme-1m`, `--cme-3m`, `--no-cache`, `--skip-network` (CME files only).

Cache directory: `FIXED_INCOME_DATA_DIR` or `~/.cache/fixed-income/`.

## Corporate spreads (FRED)

```python
from fixed_income.data import FredCorporateSpreadsSource

src = FredCorporateSpreadsSource()
spread = src.fetch_spread_bps()
```

Alternative series: `FredCorporateSpreadsSource(series_id="BAMLH0A0HYM2")`.
