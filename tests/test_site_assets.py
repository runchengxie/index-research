from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_public_site_assets_exist():
    assert (ROOT / "site" / "index.html").exists()
    assert (ROOT / "site" / "app.js").exists()
    assert (ROOT / "site" / "styles.css").exists()


def test_public_site_does_not_contain_local_identity_paths():
    public_files = [ROOT / "site" / "index.html", ROOT / "site" / "app.js", ROOT / "site" / "styles.css"]
    content = "\n".join(path.read_text() for path in public_files)
    assert "/home/" not in content
    assert "/Users/" not in content
    assert "TUSHARE_TOKEN=" not in content
    assert "fast.xiaodefa.cn" not in content


def test_public_site_uses_subpath_safe_data_urls():
    app = (ROOT / "site" / "app.js").read_text()
    assert "'outputs/linked_indices/" in app
    assert "'../outputs/" not in app
    assert "outputs/microcap/" in app


def test_public_site_exposes_detail_tables_for_research():
    html = (ROOT / "site" / "index.html").read_text()
    app = (ROOT / "site" / "app.js").read_text()
    assert 'id="price-table"' in html
    assert 'id="etf-table"' in html
    assert "data-table" in app
    assert "median_amount_60d" in app


def test_public_site_has_microcap_default_and_indices_tab():
    html = (ROOT / "site" / "index.html").read_text()
    app = (ROOT / "site" / "app.js").read_text()
    assert 'href="#microcap"' in html
    assert 'href="#indices"' in html
    assert 'id="microcap-panel"' in html
    assert 'id="indices-panel"' in html
    assert "setActiveTab" in app
    assert "outputs/microcap/summary.json" in app


def test_microcap_dashboard_exposes_requested_visuals():
    html = (ROOT / "site" / "index.html").read_text()
    for element_id in ("microcap-nav-chart", "microcap-annual-chart", "microcap-cagr-chart", "microcap-dd-chart"):
        assert f'id="{element_id}"' in html


def test_microcap_dashboard_has_editorial_research_sections():
    html = (ROOT / "site" / "index.html").read_text()
    for element_id in (
        "microcap-rules",
        "microcap-drivers-chart",
        "microcap-replication-chart",
        "microcap-comparison",
        "microcap-research-notes",
    ):
        assert f'id="{element_id}"' in html


def test_public_runtime_has_error_fallback_and_legacy_browser_safe_chart_code():
    app = (ROOT / "site" / "app.js").read_text()
    assert "renderLoadError" in app
    assert "rows.at(-1)" not in app
    assert "window.__INDEX_RESEARCH_READY__" in app
    assert "function setActiveTab" in app
