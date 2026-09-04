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
