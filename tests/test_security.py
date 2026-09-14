from pathlib import Path


def test_no_wildcard_cors():
    headers = Path("site/_headers").read_text(encoding="utf-8")
    assert "Access-Control-Allow-Origin: *" not in headers
    assert "Content-Security-Policy" in headers


def test_no_inline_scripts():
    html = Path("site/index.html").read_text(encoding="utf-8")
    assert "<script>" not in html
    assert 'src="assets/app.js"' in html


def test_environment_example_has_no_values():
    content = Path(".env.example").read_text(encoding="utf-8")
    assert "SECRET=" in content
    assert "SECRET=значение" not in content
