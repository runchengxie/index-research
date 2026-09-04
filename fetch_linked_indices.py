"""Fetch historical daily data for index codes listed by Tushare's etf_index."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pandas as pd
import tushare as ts


SUPPORTED_APIS = {
    ".SH": "index_daily",
    ".SZ": "index_daily",
    ".CSI": "index_daily",
    ".CNI": "index_daily",
    ".SI": "sw_daily",
    ".CI": "ci_daily",
    ".TI": "ths_daily",
}


def api_for_index_code(ts_code: str) -> str | None:
    """Return the correct historical endpoint for a Tushare index code."""
    upper = str(ts_code).upper()
    for suffix, api in SUPPORTED_APIS.items():
        if upper.endswith(suffix):
            return api
    return None


def _client():
    token = os.getenv("TUSHARE_TOKEN_2") or os.getenv("TUSHARE_TOKEN")
    if not token:
        raise SystemExit("TUSHARE_TOKEN_2 or TUSHARE_TOKEN is not configured")
    client = ts.pro_api(token=token)
    api_url = os.getenv("TUSHARE_API_URL_2") or os.getenv("TUSHARE_API_URL")
    if api_url:
        client._DataApi__http_url = api_url
    return client


def _fetch(pro, api: str, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    method = getattr(pro, api)
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            return method(ts_code=ts_code, start_date=start_date, end_date=end_date)
        except Exception as exc:  # provider errors need a bounded retry
            last_error = exc
            if attempt < 2:
                time.sleep(1.0 + attempt)
    assert last_error is not None
    raise last_error


def fetch_linked_indices(
    *,
    mapping_csv: Path,
    out_dir: Path,
    start_date: str = "20150101",
    end_date: str = "20260821",
    sleep_seconds: float = 0.15,
) -> None:
    mapping = pd.read_csv(mapping_csv, dtype={"ts_code": str})
    mapping = mapping.drop_duplicates("ts_code").copy()
    mapping["api"] = mapping["ts_code"].map(api_for_index_code)
    out_dir.mkdir(parents=True, exist_ok=True)
    mapping.to_csv(out_dir / "linked_index_catalog.csv", index=False)

    pro = _client()
    frames: list[pd.DataFrame] = []
    status: list[dict[str, object]] = []

    def checkpoint() -> None:
        pd.DataFrame(status).to_csv(out_dir / "linked_index_fetch_status.csv", index=False)
        if frames:
            pd.concat(frames, ignore_index=True).to_parquet(out_dir / "linked_index_daily.parquet", index=False)

    for row in mapping.itertuples(index=False):
        code = str(row.ts_code)
        api = row.api
        if not api:
            status.append({"ts_code": code, "api": None, "status": "unsupported_code_suffix", "rows": 0})
            continue
        try:
            frame = _fetch(pro, api, code, start_date, end_date)
            if frame.empty:
                status.append({"ts_code": code, "api": api, "status": "empty", "rows": 0})
            else:
                frame = frame.copy()
                frame["api"] = api
                frames.append(frame)
                status.append({"ts_code": code, "api": api, "status": "ok", "rows": len(frame)})
        except Exception as exc:  # retain failure reason and continue the batch
            status.append({"ts_code": code, "api": api, "status": "error", "rows": 0, "error": str(exc)[:300]})
        time.sleep(sleep_seconds)
        if len(status) % 50 == 0:
            checkpoint()
            print(f"processed {len(status)}/{len(mapping)}")

    checkpoint()
    print(f"completed {len(status)} codes; successful={sum(s['status'] == 'ok' for s in status)}")


if __name__ == "__main__":
    fetch_linked_indices(
        mapping_csv=Path("outputs/probe_etf_index.csv"),
        out_dir=Path("outputs/linked_indices"),
    )
