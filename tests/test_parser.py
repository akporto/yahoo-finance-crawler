import pytest
from crawler.parser import YahooFinanceParser
from crawler.models import StockData


@pytest.fixture
def full_record():
    return {
        "symbol": "AMX.BA",
        "shortName": "América Móvil, S.A.B. de C.V.",
        "regularMarketPrice": 2089.00,
        "regularMarketChange": 15.50,
        "regularMarketChangePercent": 0.75,
    }


@pytest.fixture
def minimal_record():
    return {"symbol": "NOKA.BA", "shortName": "Nokia Corporation", "regularMarketPrice": 557.50}


class TestYahooFinanceParserSuccess:

    def test_parses_full_record(self, full_record):
        result = YahooFinanceParser.parse(full_record)
        assert isinstance(result, StockData)
        assert result.symbol == "AMX.BA"
        assert result.name == "América Móvil, S.A.B. de C.V."
        assert result.price == 2089.00
        assert result.change == 15.50
        assert result.change_percent == 0.75

    def test_symbol_is_uppercased(self):
        record = {"symbol": "petr4.sa", "shortName": "Petrobras", "regularMarketPrice": 38.5}
        assert YahooFinanceParser.parse(record).symbol == "PETR4.SA"

    def test_optional_fields_are_none_when_absent(self, minimal_record):
        result = YahooFinanceParser.parse(minimal_record)
        assert result.change is None
        assert result.change_percent is None

    def test_falls_back_to_long_name(self):
        record = {"symbol": "TSLA", "longName": "Tesla, Inc.", "regularMarketPrice": 250.0}
        assert YahooFinanceParser.parse(record).name == "Tesla, Inc."

    def test_prefers_short_name_over_long_name(self):
        record = {"symbol": "TSLA", "shortName": "Tesla", "longName": "Tesla, Inc.", "regularMarketPrice": 250.0}
        assert YahooFinanceParser.parse(record).name == "Tesla"

    def test_zero_price_is_accepted(self):
        record = {"symbol": "XYZ", "shortName": "Corp", "regularMarketPrice": 0}
        assert YahooFinanceParser.parse(record).price == 0.0

    def test_negative_change_is_accepted(self):
        record = {"symbol": "VALE3.SA", "shortName": "Vale", "regularMarketPrice": 60.0, "regularMarketChange": -1.20}
        assert YahooFinanceParser.parse(record).change == -1.20


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

    def test_non_numeric_change_results_in_none(self):
        """Bad optional fields should not invalidate an otherwise valid record."""
        record = {"symbol": "AAPL", "shortName": "Apple", "regularMarketPrice": 150.0, "regularMarketChange": "unknown"}
        result = YahooFinanceParser.parse(record)
        assert result is not None
        assert result.change is None
