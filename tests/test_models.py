import pytest
from crawler.models import StockData


class TestStockData:

    def test_valid_creation(self):
        stock = StockData(symbol="AAPL", name="Apple Inc.", price=175.50)
        assert stock.symbol == "AAPL"
        assert stock.name == "Apple Inc."
        assert stock.price == 175.50

    def test_zero_price_is_valid(self):
        stock = StockData(symbol="XYZ", name="Some Corp", price=0.0)
        assert stock.price == 0.0

    def test_empty_symbol_raises(self):
        with pytest.raises(ValueError, match="Symbol cannot be empty"):
            StockData(symbol="", name="Apple Inc.", price=100.0)

    def test_whitespace_symbol_raises(self):
        with pytest.raises(ValueError, match="Symbol cannot be empty"):
            StockData(symbol="   ", name="Apple Inc.", price=100.0)

    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="Name cannot be empty"):
            StockData(symbol="AAPL", name="", price=100.0)

    def test_negative_price_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            StockData(symbol="AAPL", name="Apple Inc.", price=-1.0)

    def test_none_price_raises(self):
        with pytest.raises(ValueError):
            StockData(symbol="AAPL", name="Apple Inc.", price=None)

    def test_is_immutable(self):
        stock = StockData(symbol="AAPL", name="Apple Inc.", price=100.0)
        with pytest.raises(Exception):
            stock.price = 200.0
