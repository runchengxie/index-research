import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from build_microcap_snapshot import (
    calculate_annual_returns,
    calculate_rolling_cagr,
    calculate_rolling_drawdown,
)


MICROCAP = ROOT / "outputs" / "microcap"


def read_csv(name: str) -> list[dict[str, str]]:
    with (MICROCAP / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_microcap_files_have_stable_columns() -> None:
    assert list(read_csv("annual_returns.csv")[0]) == ["year", "return", "nav"]
    assert list(read_csv("rolling_cagr.csv")[0]) == ["as_of", "window_years", "cagr"]
    assert list(read_csv("rolling_drawdown.csv")[0]) == [
        "as_of",
        "window_years",
        "max_drawdown",
        "frequency",
    ]
    assert list(read_csv("nav.csv")[0]) == ["date", "nav", "source"]


def test_microcap_snapshot_covers_the_published_reference_period() -> None:
    annual = read_csv("annual_returns.csv")
    rolling = read_csv("rolling_cagr.csv")
    drawdown = read_csv("rolling_drawdown.csv")
    summary = json.loads((MICROCAP / "summary.json").read_text(encoding="utf-8"))

    assert annual[0]["year"] == "2000"
    assert annual[-1]["year"] == "2025"
    assert len(annual) == 26
    assert {int(row["window_years"]) for row in rolling} == {3, 5, 10, 15, 20}
    assert {row["frequency"] for row in drawdown} <= {"monthly", "daily_reference"}
    assert summary["coverage_start"] == "2000"
    assert summary["coverage_end"] == "2025"
    assert summary["source_label"] == "公开资料参考口径"


def test_calculations_use_the_supplied_nav_series() -> None:
    nav = [{"date": f"{year}-12-31", "nav": str(value)} for year, value in zip(range(2020, 2026), [1, 2, 1, 3, 2, 4])]

    annual = calculate_annual_returns(nav)
    cagr = calculate_rolling_cagr(nav, windows=(2,))
    drawdown = calculate_rolling_drawdown(nav, windows=(3,), frequency="annual_reference")

    assert annual[0] == {"year": 2020, "return": 0.0, "nav": 1.0}
    assert annual[1]["return"] == 1.0
    assert cagr[-1]["as_of"] == "2025-12-31"
    assert round(float(cagr[-1]["cagr"]), 6) == round((4 / 3) ** 0.5 - 1, 6)
    assert round(float(drawdown[-1]["max_drawdown"]), 6) == round(-1 / 3, 6)
