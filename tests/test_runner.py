from __future__ import annotations

from nse_nifty50_scraper.runner import write_json


def test_write_json_creates_parent_directory(tmp_path):
    path = tmp_path / "SBIN" / "26-08-2026" / "response.json"

    write_json(path, [{"symbol": "SBIN"}])

    assert path.exists()
    assert '"symbol": "SBIN"' in path.read_text(encoding="utf-8")
