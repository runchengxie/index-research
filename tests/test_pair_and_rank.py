from pair_and_rank import match_index_name


def test_matches_longest_index_name_inside_etf_benchmark():
    names = ["中证500指数", "中证500信息技术指数"]
    assert match_index_name("中证500信息技术指数×100%", names) == "中证500信息技术指数"


def test_returns_no_match_for_unrelated_benchmark():
    assert match_index_name("银行活期存款利率", ["沪深300指数"]) is None
