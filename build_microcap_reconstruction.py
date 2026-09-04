"""Build a transparent, local-first reconstruction of a 400-stock microcap rule.

The result is deliberately labelled as a research reconstruction. It is not the
Wind index and does not attempt to reproduce Wind's historical backfill.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Iterable


def build_nav(rows: Iterable[dict]) -> list[dict]:
    nav = 1.0
    result = []
    for row in rows:
        daily_return = float(row["return"])
        nav *= 1 + daily_return
        result.append({"date": row["date"], "return": daily_return, "nav": nav})
    return result


def build_underwater_periods(rows: Iterable[dict]) -> list[dict]:
    episodes = []
    peak_nav = None
    peak_date = None
    active = None
    for row in rows:
        date = row["date"]
        nav = float(row["nav"])
        if peak_nav is None or nav >= peak_nav:
            if active is not None:
                active["end_date"] = date
                episodes.append(active)
                active = None
            peak_nav = nav
            peak_date = date
            continue

        drawdown = nav / peak_nav - 1
        if active is None:
            active = {
                "start_date": date,
                "end_date": date,
                "peak_date": peak_date,
                "trading_days": 1,
                "max_drawdown": round(drawdown, 10),
            }
        else:
            active["end_date"] = date
            active["trading_days"] += 1
            active["max_drawdown"] = round(min(active["max_drawdown"], drawdown), 10)

    if active is not None:
        episodes.append(active)
    return episodes


def summarize_nav(rows: list[dict]) -> dict:
    episodes = build_underwater_periods(rows)
    max_drawdown = min((item["max_drawdown"] for item in episodes), default=0.0)
    longest = max(episodes, key=lambda item: item["trading_days"], default=None)
    return {
        "max_drawdown": max_drawdown,
        "longest_underwater_trading_days": longest["trading_days"] if longest else 0,
        "longest_underwater_start": longest["start_date"] if longest else None,
        "longest_underwater_end": longest["end_date"] if longest else None,
        "underwater_episode_count": len(episodes),
    }


def _write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def fetch_daily_returns(daily_glob: str, start_date: str, end_date: str) -> list[dict]:
    try:
        import duckdb
    except ImportError as exc:
        raise RuntimeError("需要安装 DuckDB，可运行 uv sync --extra duckdb") from exc

    query = f"""
        with raw as (
            select
                ts_code,
                trade_date,
                adj_close,
                total_mv,
                coalesce(is_st, false) as is_st,
                coalesce(is_suspended, false) as is_suspended
            from read_parquet('{daily_glob}', union_by_name=true)
            where trade_date between '{start_date}' and '{end_date}'
              and (ts_code like '%.SH' or ts_code like '%.SZ')
              and adj_close > 0
              and total_mv > 0
        ),
        dates as (
            select trade_date,
                   lead(trade_date) over (order by trade_date) as next_trade_date
            from (select distinct trade_date from raw)
        ),
        prices as (
            select *,
                   lead(trade_date) over (partition by ts_code order by trade_date) as next_stock_date,
                   lead(adj_close) over (partition by ts_code order by trade_date) as next_adj_close
            from raw
        ),
        ranked as (
            select *, row_number() over (partition by trade_date order by total_mv, ts_code) as rank
            from prices
            where not is_st and not is_suspended
        ),
        selected as (
            select ranked.trade_date, dates.next_trade_date,
                   ranked.ts_code, ranked.adj_close, ranked.next_adj_close,
                   ranked.next_stock_date
            from ranked
            join dates using (trade_date)
            where rank <= 400
        )
        select trade_date as date,
               avg(next_adj_close / adj_close - 1) as return,
               count(*) as selected_count,
               count(next_adj_close) as priced_count
        from selected
        where next_stock_date = next_trade_date
          and next_adj_close > 0
        group by trade_date
        having count(*) >= 100
        order by trade_date
    """
    rows = duckdb.sql(query).fetchall()
    return [
        {"date": str(date), "return": float(daily_return), "selected_count": count, "priced_count": priced}
        for date, daily_return, count, priced in rows
        if daily_return is not None
    ]


def build_dataset(args: argparse.Namespace) -> None:
    returns = fetch_daily_returns(args.daily_glob, args.start_date, args.end_date)
    nav_rows = build_nav(returns)
    episodes = build_underwater_periods(nav_rows)
    nav_path = Path(args.output_dir) / "reconstructed_daily_nav.csv"
    episodes_path = Path(args.output_dir) / "reconstructed_underwater_periods.csv"
    summary_path = Path(args.output_dir) / "reconstructed_summary.json"
    _write_csv(nav_path, nav_rows, ["date", "return", "nav"])
    _write_csv(
        episodes_path,
        episodes,
        ["start_date", "end_date", "peak_date", "trading_days", "max_drawdown"],
    )
    summary = {
        "source_label": "Tushare 规则重建（研究版）",
        "method": "上海、深圳 A 股中按总市值选取最小 400 只，等权持有至下一交易日",
        "coverage_start": nav_rows[0]["date"] if nav_rows else None,
        "coverage_end": nav_rows[-1]["date"] if nav_rows else None,
        "observations": len(nav_rows),
        **summarize_nav(nav_rows),
        "caveats": [
            "这是基于本地 Tushare 日线数据的规则重建，不是 Wind 8841431.WI 官方指数。",
            "使用复权收盘价计算，当前版本未模拟涨跌停无法成交、手续费、印花税、冲击成本和资金容量。",
            "调仓信号使用当日总市值，收益从下一交易日收盘价计算，保留了一天的持有滞后。",
        ],
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--daily-glob",
        default=os.environ.get(
            "INDEX_RESEARCH_DAILY_CLEAN_GLOB",
            str(Path.home() / "data/market-data-platform/assets/tushare/a_share/daily/a_share_all_20150101_20260904_daily_clean/data/**/*.parquet"),
        ),
    )
    parser.add_argument("--start-date", default="20150101")
    parser.add_argument("--end-date", default="20260904")
    parser.add_argument("--output-dir", default="outputs/microcap")
    return parser.parse_args()


if __name__ == "__main__":
    build_dataset(parse_args())
