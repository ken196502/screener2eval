import sys
from pathlib import Path

import requests

backend_root = str(Path(__file__).resolve().parents[1])
if backend_root not in sys.path:
    sys.path.append(backend_root)

from services import zhitong


def test_get_stock_news_falls_back_on_request(monkeypatch):
    def mock_get(*args, **kwargs):
        raise requests.exceptions.ConnectionError("network blocked")

    monkeypatch.setattr(zhitong.requests, "get", mock_get)

    result = zhitong.get_stock_news(page=2)

    assert result["status"] == "success"
    assert result.get("source") == "fallback-empty"
    data = result.get("data", {})
    assert data.get("list") == []
    assert result["page"] == 2


def test_get_stock_news_unknown_page_uses_first_page(monkeypatch):
    def mock_get(*args, **kwargs):
        raise requests.exceptions.RequestException("network blocked")

    monkeypatch.setattr(zhitong.requests, "get", mock_get)

    result = zhitong.get_stock_news(page=5)

    assert result["status"] == "success"
    assert result.get("source") == "fallback-empty"
    data = result.get("data", {})
    assert data.get("list") == []
