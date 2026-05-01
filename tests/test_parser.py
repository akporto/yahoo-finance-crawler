import pytest
from crawler.parser import YahooFinanceParser
from crawler.models import StockData


@pytest.fixture
def full_record():
    return {
        "symbol": "AMX.BA",
        "shortName": "América Móvil, S.A.B. de C.V.",
        "regularMarketPrice": 2089.00,
    }


class TestYahooFinanceParserSuccess:

    def test_parses_full_record(self, full_record):
        result = YahooFinanceParser.parse(full_record)
        assert isinstance(result, StockData)
        assert result.symbol == "AMX.BA"
        assert result.name == "América Móvil, S.A.B. de C.V."
        assert result.price == 2089.00

    def test_symbol_is_uppercased(self):
        record = {"symbol": "petr4.sa", "shortName": "Petrobras", "regularMarketPrice": 38.5}
        assert YahooFinanceParser.parse(record).symbol == "PETR4.SA"

    def test_falls_back_to_long_name(self):
        record = {"symbol": "TSLA", "longName": "Tesla, Inc.", "regularMarketPrice": 250.0}
        assert YahooFinanceParser.parse(record).name == "Tesla, Inc."

    def test_prefers_short_name_over_long_name(self):
        record = {"symbol": "TSLA", "shortName": "Tesla", "longName": "Tesla, Inc.", "regularMarketPrice": 250.0}
        assert YahooFinanceParser.parse(record).name == "Tesla"

    def test_zero_price_is_accepted(self):
        record = {"symbol": "XYZ", "shortName": "Corp", "regularMarketPrice": 0}
        assert YahooFinanceParser.parse(record).price == 0.0


class TestYahooFinanceParserFailures:

    def test_returns_none_for_empty_dict(self):
        assert YahooFinanceParser.parse({}) is None

    def test_returns_none_for_none_input(self):
        assert YahooFinanceParser.parse(None) is None

    def test_returns_none_when_symbol_missing(self):
        assert YahooFinanceParser.parse({"shortName": "Apple", "regularMarketPrice": 150.0}) is None

    def test_returns_none_when_price_missing(self):
        assert YahooFinanceParser.parse({"symbol": "AAPL", "shortName": "Apple"}) is None

    def test_returns_none_when_name_missing(self):
        assert YahooFinanceParser.parse({"symbol": "AAPL", "regularMarketPrice": 150.0}) is None

    def test_returns_none_for_negative_price(self):
        assert YahooFinanceParser.parse({"symbol": "AAPL", "shortName": "Apple", "regularMarketPrice": -10.0}) is None

    def test_returns_none_for_non_numeric_price(self):
        assert YahooFinanceParser.parse({"symbol": "AAPL", "shortName": "Apple", "regularMarketPrice": "N/A"}) is None
