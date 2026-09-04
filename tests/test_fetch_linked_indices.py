from fetch_linked_indices import api_for_index_code


def test_routes_index_code_to_provider_specific_api():
    assert api_for_index_code("801001.SI") == "sw_daily"
    assert api_for_index_code("CI005001.CI") == "ci_daily"
    assert api_for_index_code("865001.TI") == "ths_daily"
    assert api_for_index_code("000300.SH") == "index_daily"
