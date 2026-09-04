"""Pair linked indices with live ETFs and compare return, drawdown, and liquidity."""

from __future__ import annotations

import re
from pathlib import Path

import duckdb
import pandas as pd


START_DATE = 20160902
END_DATE = 20260821
MIN_MEDIAN_AMOUNT = 10_000  # Tushare ETF amount is in thousand RMB: 10m RMB.


def match_index_name(benchmark: str, index_names: list[str]) -> str | None:
    """Match the longest known index name embedded in an ETF benchmark."""
    text = re.sub(r"\s+", "", str(benchmark))
    candidates = [name for name in index_names if name and name in text]
    return max(candidates, key=len) if candidates else None


def main() -> None:
    root = Path(__file__).parent
    output = root / "outputs"
    linked = output / "linked_indices"
    catalog = pd.read_csv(linked / "linked_index_catalog.csv", dtype={"ts_code": str})
    etf_basic = pd.read_csv(output / "index_catalog.csv", dtype={"ts_code": str})
    # The ETF reference file is not part of the index catalog; use the local asset directly.
    etf_basic = pd.read_csv(
        "/home/richard/data/market-data-platform/assets/tushare/etf/reference/etf_fund_basic_20260825.csv",
        dtype={"ts_code": str},
    )
    index_names = catalog["indx_name"].dropna().astype(str).unique().tolist()
    eligible = etf_basic[
        etf_basic["status"].eq("L")
        & etf_basic["fund_type"].eq("股票型")
        & etf_basic["name"].fillna("").str.contains("ETF", regex=False)
        & etf_basic["list_date"].notna()
        & etf_basic["list_date"].le(START_DATE)
        & etf_basic["benchmark"].notna()
    ].copy()
    eligible["matched_index_name"] = eligible["benchmark"].map(
        lambda x: match_index_name(x, index_names)
    )
    name_to_code = catalog.drop_duplicates("indx_name").set_index("indx_name")["ts_code"].to_dict()
    eligible["index_ts_code"] = eligible["matched_index_name"].map(name_to_code)
    matched = eligible[eligible["index_ts_code"].notna()].copy()
    matched[["ts_code", "name", "benchmark", "list_date", "index_ts_code", "matched_index_name"]].to_csv(
        linked / "etf_index_pairing.csv", index=False
    )

    con = duckdb.connect()
    etf_daily = "/home/richard/data/market-data-platform/assets/tushare/etf/daily/etf_all_20150101_20260824_fund_daily/data/**/*.parquet"
    etf_adj = "/home/richard/data/market-data-platform/assets/tushare/etf/adj_factor/etf_all_20150101_20260824_fund_adj/data/**/*.parquet"
    pair_csv = str(linked / "etf_index_pairing.csv")
    etf_metrics = con.sql(f"""
        with pairs as (select * from read_csv_auto('{pair_csv}')),
        daily as (
            select ts_code, cast(trade_date as integer) dt, close, amount
            from read_parquet('{etf_daily}')
            where ts_code in (select ts_code from pairs)
        ), factors as (
            select ts_code, cast(trade_date as integer) dt, adj_factor
            from read_parquet('{etf_adj}')
            where ts_code in (select ts_code from pairs)
        ), x as (
            select d.ts_code, d.dt, d.amount, d.close * f.adj_factor adj_close
            from daily d join factors f using (ts_code, dt)
        ), windowed as (
            select * from x where dt between {START_DATE} and {END_DATE}
        ), dd as (
            select *, max(adj_close) over (
                partition by ts_code order by dt rows between unbounded preceding and current row
            ) peak
            from windowed
        ), recent as (
            select *, row_number() over (partition by ts_code order by dt desc) rn
            from x where dt <= {END_DATE}
        )
        select ts_code,
            max(case when dd.dt={START_DATE} then dd.adj_close end) p0,
            max(case when dd.dt={END_DATE} then dd.adj_close end) p1,
            min(case when dd.dt between {START_DATE} and {END_DATE}
                then dd.adj_close / dd.peak - 1 end) max_drawdown,
            median(case when recent.rn <= 60 then recent.amount end) median_amount_60d
        from dd left join recent using (ts_code, dt)
        group by dd.ts_code
    """).df()

    index_daily = str(linked / "linked_index_daily.parquet")
    index_metrics = con.sql(f"""
        with x as (
            select ts_code, cast(trade_date as integer) dt, close
            from read_parquet('{index_daily}')
        ), windowed as (
            select * from x where dt between {START_DATE} and {END_DATE}
        ), dd as (
            select *, max(close) over (
                partition by ts_code order by dt rows between unbounded preceding and current row
            ) peak
            from windowed
        )
        select ts_code,
            max(case when dt={START_DATE} then close end) index_p0,
            max(case when dt={END_DATE} then close end) index_p1,
            min(close / peak - 1) index_max_drawdown
        from dd group by ts_code
    """).df()

    result = matched.merge(etf_metrics, on="ts_code", how="left").merge(
        index_metrics, left_on="index_ts_code", right_on="ts_code", suffixes=("", "_index")
    )
    result["etf_total_return"] = result["p1"] / result["p0"] - 1
    result["etf_cagr"] = (result["p1"] / result["p0"]) ** 0.1 - 1
    result["index_price_return"] = result["index_p1"] / result["index_p0"] - 1
    result["index_cagr"] = (result["index_p1"] / result["index_p0"]) ** 0.1 - 1
    result["liquid_10m"] = result["median_amount_60d"] >= MIN_MEDIAN_AMOUNT
    result = result[result["p0"].notna() & result["p1"].notna() & result["index_p0"].notna() & result["index_p1"].notna()]
    result = result.rename(columns={"max_drawdown": "etf_max_drawdown"})
    result.to_csv(linked / "paired_index_etf_returns_all.csv", index=False)

    liquid = result[result["liquid_10m"]].copy()
    liquid = liquid.sort_values(["index_ts_code", "median_amount_60d", "etf_cagr"], ascending=[True, False, False])
    representative = liquid.drop_duplicates("index_ts_code")
    representative = representative.sort_values("etf_cagr", ascending=False)
    representative.to_csv(linked / "paired_index_etf_representatives.csv", index=False)
    print(f"matched ETFs={len(matched)}, comparable pairs={len(result)}, liquid representatives={len(representative)}")


if __name__ == "__main__":
    main()
