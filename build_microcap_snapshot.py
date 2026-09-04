"""Build compact, source-labelled microcap research outputs.

The input is a CSV with ``date`` and ``nav`` columns. Calculations use only
the supplied series, so a Wind reference series and a future Tushare-rebuilt
series can be processed separately without mixing their definitions.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Iterable
from pathlib import Path


WINDOWS = (3, 5, 10, 15, 20)


def _rows(nav: Iterable[dict[str, str]]) -> list[tuple[str, float]]:
    result = []
    for row in nav:
        if "date" not in row or "nav" not in row:
            raise ValueError("输入文件必须包含 date 和 nav 列")
        result.append((str(row["date"]), float(row["nav"])))
    result.sort()
    if not result:
        raise ValueError("输入文件没有有效净值记录")
    return result


def calculate_annual_returns(nav: Iterable[dict[str, str]]) -> list[dict[str, float | int]]:
    rows = _rows(nav)
    by_year: dict[int, list[float]] = {}
    for date, value in rows:
        by_year.setdefault(int(date[:4]), []).append(value)
    years = sorted(by_year)
    result = []
    previous = None
    for year in years:
        value = by_year[year][-1]
        annual_return = value / previous - 1 if previous is not None else value - 1
        result.append({"year": year, "return": annual_return, "nav": value})
        previous = value
    return result


def calculate_rolling_cagr(nav: Iterable[dict[str, str]], windows: tuple[int, ...] = WINDOWS) -> list[dict[str, float | int | str]]:
    annual = calculate_annual_returns(nav)
    result = []
    for window in windows:
        if len(annual) < window + 1:
            continue
        for end in range(window, len(annual)):
            start_nav = float(annual[end - window]["nav"])
            end_nav = float(annual[end]["nav"])
            result.append({
                "as_of": f"{annual[end]['year']}-12-31",
                "window_years": window,
                "cagr": (end_nav / start_nav) ** (1 / window) - 1,
            })
    return result


def calculate_rolling_drawdown(
    nav: Iterable[dict[str, str]], windows: tuple[int, ...] = WINDOWS, frequency: str = "annual_reference"
) -> list[dict[str, float | int | str]]:
    rows = _rows(nav)
    result = []
    for window in windows:
        if len(rows) < window:
            continue
        for end in range(window - 1, len(rows)):
            sample = [value for _, value in rows[end - window + 1 : end + 1]]
            peak = sample[0]
            max_drawdown = 0.0
            for value in sample:
                peak = max(peak, value)
                max_drawdown = min(max_drawdown, value / peak - 1)
            result.append({
                "as_of": rows[end][0],
                "window_years": window,
                "max_drawdown": max_drawdown,
                "frequency": frequency,
            })
    return result


def _write_csv(path: Path, fields: list[str], rows: Iterable[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build_snapshot(source: Path, out_dir: Path, source_label: str) -> None:
    with source.open(newline="", encoding="utf-8") as handle:
        nav = list(csv.DictReader(handle))
    rows = _rows(nav)
    annual = calculate_annual_returns(nav)
    cagr = calculate_rolling_cagr(nav)
    drawdown = calculate_rolling_drawdown(nav, frequency="annual_reference")
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(out_dir / "annual_returns.csv", ["year", "return", "nav"], annual)
    _write_csv(out_dir / "rolling_cagr.csv", ["as_of", "window_years", "cagr"], cagr)
    _write_csv(out_dir / "rolling_drawdown.csv", ["as_of", "window_years", "max_drawdown", "frequency"], drawdown)
    _write_csv(out_dir / "nav.csv", ["date", "nav", "source"], [{"date": d, "nav": v, "source": source_label} for d, v in rows])
    latest = annual[-1]
    latest_cagr = {int(row["window_years"]): row for row in cagr if row["as_of"] == f"{latest['year']}-12-31"}
    summary = {
        "as_of": f"{latest['year']}-12-31",
        "source_label": source_label,
        "coverage_start": str(annual[0]["year"]),
        "coverage_end": str(latest["year"]),
        "metrics": {"cumulative_nav": latest["nav"], "annual_return": latest["return"]},
        "rolling_cagr": {str(window): latest_cagr[window]["cagr"] for window in latest_cagr},
        "caveats": ["年度参考序列不等同于 Wind 原始日频序列。", "年度频率的回撤会低估日内和日间回撤。"],
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="生成微盘股研究公开快照")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=Path("outputs/microcap"))
    parser.add_argument("--source-label", default="公开资料参考口径")
    args = parser.parse_args()
    build_snapshot(args.source, args.out_dir, args.source_label)


if __name__ == "__main__":
    main()
