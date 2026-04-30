from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class StockData:
    """Immutable equity record. `price` maps to Yahoo's `regularMarketPrice` (intraday)."""

    symbol: str
    name: str
    price: float
    change: Optional[float] = None
    change_percent: Optional[float] = None

    def __post_init__(self):
        if not self.symbol or not self.symbol.strip():
            raise ValueError("Symbol cannot be empty.")
        if not self.name or not self.name.strip():
            raise ValueError("Name cannot be empty.")
        if self.price is None or self.price < 0:
            raise ValueError(f"Price must be a non-negative number, got: {self.price}")
