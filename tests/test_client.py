import pytest
from unittest.mock import MagicMock, patch
from requests.exceptions import HTTPError, ConnectionError

from crawler.client import (
    YahooFinanceScreenerClient,
    resolve_region_code,
    _build_payload,
    REGION_MAP,
)


class TestResolveRegionCode:

    def test_resolves_full_name_case_insensitive(self):
        assert resolve_region_code("Argentina") == "ar"
        assert resolve_region_code("ARGENTINA") == "ar"

    def test_accepts_iso_code_directly(self):
        assert resolve_region_code("ar") == "ar"
        assert resolve_region_code("us") == "us"

    def test_resolves_multi_word_region(self):
        assert resolve_region_code("United States") == "us"
        assert resolve_region_code("Saudi Arabia") == "sa"

    def test_raises_on_unknown_region(self):
        with pytest.raises(ValueError, match="Unknown region"):
            resolve_region_code("Narnia")

    def test_all_regions_in_map_resolve(self):
        for name, code in REGION_MAP.items():
            assert resolve_region_code(name) == code
            assert resolve_region_code(code) == code


class TestBuildPayload:

    def test_structure(self):
        payload = _build_payload("ar", offset=0, size=100)
        assert payload["offset"] == 0
        assert payload["size"] == 100
        assert payload["quoteType"] == "EQUITY"

    def test_region_operand(self):
        payload = _build_payload("br", offset=0, size=50)
        operands = payload["query"]["operands"]
        region_filter = next(o for o in operands if "region" in o.get("operands", []))
        assert region_filter["operands"][1] == "br"

    def test_pagination_offset(self):
        assert _build_payload("us", offset=100, size=100)["offset"] == 100


def _api_response(quotes: list, total: int) -> dict:
    return {"finance": {"result": [{"quotes": quotes, "total": total}], "error": None}}


class TestYahooFinanceScreenerClient:

    def _make_client(self):
        mock_session = MagicMock()
        mock_session.crumb = "test-crumb"
        return YahooFinanceScreenerClient(session=mock_session), mock_session

    def _mock_response(self, quotes, total):
        resp = MagicMock(status_code=200)
        resp.json.return_value = _api_response(quotes, total)
        return resp

    def test_fetch_all_single_page(self):
        client, mock_session = self._make_client()
        quotes = [{"symbol": "AMX.BA", "shortName": "América Móvil", "regularMarketPrice": 2089.0}]
        mock_session.post.return_value = self._mock_response(quotes, total=1)

        results = list(client.fetch_all("ar"))

        assert len(results) == 1
        assert results[0]["symbol"] == "AMX.BA"

    def test_fetch_all_paginates_until_total_reached(self):
        client, mock_session = self._make_client()
        page1 = [{"symbol": f"S{i}", "shortName": f"Co{i}", "regularMarketPrice": float(i)} for i in range(3)]
        page2 = [{"symbol": f"S{i}", "shortName": f"Co{i}", "regularMarketPrice": float(i)} for i in range(3, 5)]

        mock_session.post.side_effect = [
            self._mock_response(page1, total=5),
            self._mock_response(page2, total=5),
        ]

        with patch("crawler.client._PAGE_SIZE", 3):
            results = list(client.fetch_all("ar"))

        assert len(results) == 5
        assert mock_session.post.call_count == 2

    def test_fetch_all_stops_on_empty_quotes(self):
        client, mock_session = self._make_client()
        mock_session.post.return_value = self._mock_response([], total=0)

        assert list(client.fetch_all("ar")) == []
        assert mock_session.post.call_count == 1

    def test_raises_immediately_on_403(self):
        client, mock_session = self._make_client()
        mock_response = MagicMock(status_code=403)
        mock_response.raise_for_status.side_effect = HTTPError(response=mock_response)
        mock_session.post.return_value = mock_response

        with pytest.raises(HTTPError):
            list(client.fetch_all("ar"))

    def test_retries_on_transient_error_then_succeeds(self):
        client, mock_session = self._make_client()
        good_response = self._mock_response(
            [{"symbol": "A", "shortName": "Alpha", "regularMarketPrice": 10.0}], total=1
        )
        mock_session.post.side_effect = [ConnectionError(), ConnectionError(), good_response]

        with patch("crawler.client.time.sleep"):
            results = list(client.fetch_all("ar"))

        assert len(results) == 1
        assert mock_session.post.call_count == 3

    def test_raises_after_max_retries_exhausted(self):
        client, mock_session = self._make_client()
        mock_session.post.side_effect = ConnectionError("always fails")

        with patch("crawler.client.time.sleep"):
            with pytest.raises(ConnectionError):
                list(client.fetch_all("ar"))
