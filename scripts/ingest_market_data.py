#!/usr/bin/env python3
"""Fetch and cache market data for fixed-income / IR derivatives workflows."""

from __future__ import annotations

import argparse
from datetime import date

from fixed_income.data import (
    CachedDataSource,
    CmeSofrSettleBundleSource,
    FredSofrIndexSource,
    FredSofrSource,
    NyFedSofrSource,
    TreasuryParCurveSource,
    default_cme_1m_path,
    default_cme_3m_path,
    load_project_dotenv,
)


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest SOFR, Treasury, and CME settlement data.")
    parser.add_argument("--as-of", type=_parse_date, default=date(2026, 5, 22), help="Valuation date")
    parser.add_argument("--cme-1m", type=str, default=str(default_cme_1m_path()), help="SR1 settle CSV path")
    parser.add_argument("--cme-3m", type=str, default=str(default_cme_3m_path()), help="SR3 settle CSV path")
    parser.add_argument("--no-cache", action="store_true", help="Skip disk cache")
    parser.add_argument("--skip-network", action="store_true", help="Skip Treasury/FRED/NY Fed (CME only)")
    args = parser.parse_args()

    load_project_dotenv()
    as_of = args.as_of

    print(f"Valuation date: {as_of.isoformat()}\n")

    if not args.skip_network:
        treasury = TreasuryParCurveSource()
        if not args.no_cache:
            treasury = CachedDataSource(treasury)
        par = treasury.fetch(as_of=as_of)
        print(f"Treasury par ({par.as_of}): {len(par.points)} points")

        nyfed = NyFedSofrSource()
        if not args.no_cache:
            nyfed = CachedDataSource(nyfed)
        sofr = nyfed.fetch(as_of=as_of)
        print(f"NY Fed SOFR ({sofr.as_of}): {len(sofr.observations)} obs, latest={sofr.as_of_value():.4%}")

        fred = FredSofrSource()
        if not args.no_cache:
            fred = CachedDataSource(fred)
        fred_pt = fred.fetch(as_of=as_of)
        print(
            f"FRED SOFR ({fred_pt['as_of']}): {fred_pt['value']:.4f} (percent in FRED payload)"
        )

        try:
            idx = FredSofrIndexSource()
            if not args.no_cache:
                idx = CachedDataSource(idx)
            idx_pt = idx.fetch(as_of=as_of)
            print(f"FRED SOFR Index ({idx_pt['as_of']}): {idx_pt['value']:.6f}")
        except Exception as exc:
            print(f"FRED SOFR Index: skipped ({exc})")

    bundle_src = CmeSofrSettleBundleSource(
        trade_date=as_of,
        path_1m=args.cme_1m,
        path_3m=args.cme_3m,
    )
    if not args.no_cache:
        bundle_src = CachedDataSource(bundle_src)
    bundle = bundle_src.fetch(as_of=as_of)
    print(f"\nCME SR1 settle strip: {len(bundle.sr1.settles)} contracts")
    if bundle.sr1.settles:
        front = bundle.sr1.settles[0]
        print(f"  front {front.contract_month} ({front.symbol}): settle={front.settle}")
    print(f"CME SR3 settle strip: {len(bundle.sr3.settles)} contracts")
    if bundle.sr3.settles:
        front = bundle.sr3.settles[0]
        print(f"  front {front.contract_month} ({front.symbol}): settle={front.settle}")

    print("\nDone.")


if __name__ == "__main__":
    main()
