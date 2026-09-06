"""Refresh the documented cash-flow index family from TuShare."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import tushare as ts

from analyze_cashflow import INDEXES, TOTAL_RETURN_CODES


def main() -> None:
    token = os.getenv("TUSHARE_TOKEN_2") or os.getenv("TUSHARE_TOKEN")
    if not token:
        raise SystemExit("TUSHARE_TOKEN_2 or TUSHARE_TOKEN is not configured")
    pro = ts.pro_api(token=token)
    api_url = os.getenv("TUSHARE_API_URL_2") or os.getenv("TUSHARE_API_URL")
    if api_url:
        pro._DataApi__http_url = api_url
    frames = []
    codes = [code for code, *_ in INDEXES] + list(TOTAL_RETURN_CODES.values())
    for code in codes:
        frame = pro.index_daily(ts_code=code, start_date="20100101", end_date="20260904")
        if not frame.empty:
            frame["api"] = "index_daily"
            frames.append(frame)
        print(f"{code}: {len(frame)} rows")
    if not frames:
        raise SystemExit("TuShare returned no cash-flow index data")
    out = Path("outputs/cashflow_indices")
    out.mkdir(parents=True, exist_ok=True)
    pd.concat(frames, ignore_index=True).to_parquet(out / "cashflow_index_daily.parquet", index=False)
    print(f"wrote {out / 'cashflow_index_daily.parquet'}")


if __name__ == "__main__":
    main()
