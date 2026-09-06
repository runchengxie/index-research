"""Build a comparable performance snapshot for the documented cash-flow indices.

The input is the shared linked-index daily cache. Returns are price returns
from index close, not total returns. Window endpoints use the latest available
trading day in the cache, so stale-data risk is visible in the output.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


INDEXES = [
    ("980092.SZ", "国证自由现金流", "Broad A-share / red-chip", "quarterly", "current rule; changed 2024-08-15"),
    ("932365.CSI", "中证全指自由现金流", "CSI All Share", "quarterly", "100 constituents"),
    ("932366.CSI", "300现金流", "CSI 300", "quarterly", "50 constituents"),
    ("932367.CSI", "500现金流", "CSI 500", "quarterly", "50 constituents"),
    ("932368.CSI", "800现金流", "CSI 800", "quarterly", "50 constituents"),
    ("932369.CSI", "1000现金流", "CSI 1000", "quarterly", "100 constituents"),
    ("931082.CSI", "A500现金流", "CSI A500", "quarterly", "50 constituents"),
    ("932457.CSI", "港股通现金流", "Hong Kong Connect", "semiannual", "50 constituents; HKD"),
]

# CSI uses CNY010 for gross total return (dividends reinvested) and CNY020
# for net total return. We use gross total return for the dividend-inclusive
# view. 980092 currently has no corresponding total-return code in the local
# index catalog, so it remains price-return unless an ETF proxy is supplied.
TOTAL_RETURN_CODES = {
    "932365.CSI": "932365CNY010.CSI",
    "932366.CSI": "932366CNY010.CSI",
    "932367.CSI": "932367CNY010.CSI",
    "932368.CSI": "932368CNY010.CSI",
    "932369.CSI": "932369CNY010.CSI",
    "931082.CSI": "931082CNY010.CSI",
    "932457.CSI": "932457HKD210.CSI",
}


def _date(value: str) -> pd.Timestamp:
    return pd.to_datetime(value, format="%Y%m%d")


def _window_bounds(label: str, end: pd.Timestamp) -> tuple[pd.Timestamp, pd.Timestamp]:
    if label == "last_week":
        return end - pd.Timedelta(days=7), end
    if label == "last_month":
        return end - pd.DateOffset(months=1), end
    if label == "last_6_months":
        return end - pd.DateOffset(months=6), end
    if label == "ytd":
        return pd.Timestamp(end.year, 1, 1), end
    if label == "rolling_1_year":
        return end - pd.DateOffset(years=1), end
    if label == "year_2025":
        return pd.Timestamp("2025-01-01"), pd.Timestamp("2025-12-31")
    if label == "since_20240924":
        return pd.Timestamp("2024-09-24"), end
    if label == "last_3_years":
        return end - pd.DateOffset(years=3), end
    if label == "last_5_years":
        return end - pd.DateOffset(years=5), end
    if label == "last_10_years":
        return end - pd.DateOffset(years=10), end
    if label == "last_15_years":
        return end - pd.DateOffset(years=15), end
    raise ValueError(label)


def build_snapshot(input_path: Path, out_dir: Path) -> None:
    raw = pd.read_parquet(input_path)
    raw["date"] = pd.to_datetime(raw["trade_date"].astype(str), format="%Y%m%d")
    raw["close"] = pd.to_numeric(raw["close"], errors="coerce")
    raw = raw.dropna(subset=["date", "close"])
    available_end = raw["date"].max()
    windows = [
        "last_week", "last_month", "last_6_months", "ytd", "rolling_1_year",
        "year_2025", "since_20240924", "last_3_years", "last_5_years",
        "last_10_years", "last_15_years",
    ]
    rows: list[dict[str, object]] = []
    status_rows: list[dict[str, object]] = []
    for code, name, universe, frequency, note in INDEXES:
        total_code = TOTAL_RETURN_CODES.get(code)
        total = raw[raw["ts_code"].eq(total_code)].sort_values("date") if total_code else pd.DataFrame()
        frame = total if not total.empty else raw[raw["ts_code"].eq(code)].sort_values("date")
        return_basis = "gross_total_return" if not total.empty else "price_return"
        if frame.empty:
            status_rows.append({"ts_code": code, "name": name, "source_code": total_code if return_basis == "gross_total_return" else code, "return_basis": return_basis, "status": "missing", "coverage_start": None, "coverage_end": None, "rows": 0})
            continue
        status_rows.append({"ts_code": code, "name": name, "source_code": total_code if return_basis == "gross_total_return" else code, "return_basis": return_basis, "status": "available", "coverage_start": frame.date.min().date().isoformat(), "coverage_end": frame.date.max().date().isoformat(), "rows": len(frame)})
        series = frame.set_index("date")["close"]
        for window in windows:
            start, requested_end = _window_bounds(window, available_end)
            before = series[series.index <= start]
            after = series[series.index <= requested_end]
            if before.empty or after.empty:
                rows.append({"ts_code": code, "name": name, "universe": universe, "rebalance_frequency": frequency, "return_basis": return_basis, "source_code": total_code if return_basis == "gross_total_return" else code, "note": note, "window": window, "status": "insufficient_history", "as_of": available_end.date().isoformat(), "start_date": None, "end_date": None, "start_close": None, "end_close": None, "return": None, "cagr": None})
                continue
            start_date, start_close = before.index[-1], float(before.iloc[-1])
            end_date, end_close = after.index[-1], float(after.iloc[-1])
            years = max((end_date - start_date).days / 365.25, 1 / 365.25)
            ret = end_close / start_close - 1
            rows.append({"ts_code": code, "name": name, "universe": universe, "rebalance_frequency": frequency, "return_basis": return_basis, "source_code": total_code if return_basis == "gross_total_return" else code, "note": note, "window": window, "status": "ok", "as_of": available_end.date().isoformat(), "start_date": start_date.date().isoformat(), "end_date": end_date.date().isoformat(), "start_close": start_close, "end_close": end_close, "return": ret, "cagr": (1 + ret) ** (1 / years) - 1})
    out_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out_dir / "cashflow_performance.csv", index=False)
    pd.DataFrame(status_rows).to_csv(out_dir / "cashflow_data_status.csv", index=False)
    pd.DataFrame(INDEXES, columns=["ts_code", "name", "universe", "rebalance_frequency", "note"]).to_csv(out_dir / "cashflow_rebalance_frequency.csv", index=False)
    print(f"cash-flow cache as of {available_end.date()}; wrote {out_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("outputs/linked_indices/linked_index_daily.parquet"))
    parser.add_argument("--out-dir", type=Path, default=Path("outputs/cashflow_indices"))
    args = parser.parse_args()
    build_snapshot(args.input, args.out_dir)
