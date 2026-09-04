"""Rank long-history index ETF proxies using local Tushare Parquet assets.

This is intentionally a small, inspectable DuckDB script. ETF adjusted prices
are used as a practical proxy for investor total return; the native index data
is reported separately because it is price return only.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb


DEFAULT_DATA = Path("/home/richard/data/market-data-platform/assets/tushare")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--start-date", type=int, default=20160902)
    parser.add_argument("--end-date", type=int, default=20260821)
    parser.add_argument("--out-dir", type=Path, default=Path("outputs"))
    args = parser.parse_args()

    etf = args.data_root / "etf/daily/etf_all_20150101_20260824_fund_daily/data/**/*.parquet"
    adj = args.data_root / "etf/adj_factor/etf_all_20150101_20260824_fund_adj/data/**/*.parquet"
    basic = args.data_root / "etf/reference/etf_fund_basic_20260825.csv"
    index = args.data_root / "a_share/index_daily/a_share_all_index_daily_e2_20150101_20260821/data/part.parquet"
    args.out_dir.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    etf_sql = f"""
    with basic as (
        select * from read_csv_auto('{basic}')
        where status = 'L' and fund_type = '股票型'
          and list_date is not null and list_date <= {args.start_date}
          and regexp_matches(name, 'ETF')
    ), daily as (
        select ts_code, cast(trade_date as integer) dt, close
        from read_parquet('{etf}')
    ), factors as (
        select ts_code, cast(trade_date as integer) dt, adj_factor
        from read_parquet('{adj}')
    ), endpoints as (
        select d.ts_code, d.dt, d.close, f.adj_factor,
               b.name, b.benchmark, b.list_date
        from daily d join factors f using (ts_code, dt)
        join basic b using (ts_code)
        where d.dt in ({args.start_date}, {args.end_date})
    ), returns as (
        select ts_code, name, benchmark, list_date,
               max(case when dt = {args.start_date} then close * adj_factor end) p0,
               max(case when dt = {args.end_date} then close * adj_factor end) p1
        from endpoints group by 1, 2, 3, 4
    )
    select *, p1 / p0 - 1 as total_return,
           power(p1 / p0, 1.0 / 10) - 1 as cagr
    from returns where p0 is not null and p1 is not null
    order by cagr desc
    """
    con.sql(etf_sql).write_csv(str(args.out_dir / "etf_proxy_returns.csv"))

    index_sql = f"""
    with x as (
        select ts_code, cast(trade_date as integer) dt, close
        from read_parquet('{index}')
    ), r as (
        select ts_code,
               max(case when dt = {args.start_date} then close end) p0,
               max(case when dt = {args.end_date} then close end) p1
        from x group by 1
    )
    select *, p1 / p0 - 1 as price_return,
           power(p1 / p0, 1.0 / 10) - 1 as cagr
    from r where p0 is not null and p1 is not null
    order by cagr desc
    """
    con.sql(index_sql).write_csv(str(args.out_dir / "a_share_index_price_returns.csv"))
    print(f"wrote {args.out_dir / 'etf_proxy_returns.csv'}")
    print(f"wrote {args.out_dir / 'a_share_index_price_returns.csv'}")


if __name__ == "__main__":
    main()
