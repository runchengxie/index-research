import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "build_microcap_reconstruction.py"
spec = importlib.util.spec_from_file_location("microcap_reconstruction", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def test_build_nav_starts_at_one_and_compounds_daily_returns():
    rows = [
        {"date": "2026-01-02", "return": 0.10},
        {"date": "2026-01-05", "return": -0.05},
    ]

    result = module.build_nav(rows)

    assert result == [
        {"date": "2026-01-02", "return": 0.10, "nav": 1.10},
        {"date": "2026-01-05", "return": -0.05, "nav": 1.045},
    ]


def test_underwater_periods_measure_trading_days_until_new_high():
    rows = [
        {"date": "2026-01-02", "nav": 1.0},
        {"date": "2026-01-05", "nav": 0.8},
        {"date": "2026-01-06", "nav": 0.9},
        {"date": "2026-01-07", "nav": 1.1},
        {"date": "2026-01-08", "nav": 1.0},
    ]

    episodes = module.build_underwater_periods(rows)

    assert episodes == [
        {
            "start_date": "2026-01-05",
            "end_date": "2026-01-07",
            "peak_date": "2026-01-02",
            "trading_days": 2,
            "max_drawdown": -0.2,
        },
        {
            "start_date": "2026-01-08",
            "end_date": "2026-01-08",
            "peak_date": "2026-01-07",
            "trading_days": 1,
            "max_drawdown": -0.0909090909,
        },
    ]


def test_summary_exposes_max_drawdown_and_longest_underwater_period():
    rows = [
        {"date": "2026-01-02", "nav": 1.0},
        {"date": "2026-01-05", "nav": 0.8},
        {"date": "2026-01-06", "nav": 0.9},
        {"date": "2026-01-07", "nav": 1.1},
    ]

    summary = module.summarize_nav(rows)

    assert summary["max_drawdown"] == -0.2
    assert summary["longest_underwater_trading_days"] == 2
