from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class StockData:
    """Immutable representation of stock market data used across the pipeline."""
    symbol: str
    name: str
    price: float
    change: Optional[float] = None
    change_percent: Optional[float] = None

    def __post_init__(self):
        """Validates the data after initialization to ensure integrity."""
        if not self.symbol or not self.symbol.strip():
            raise ValueError("Symbol cannot be empty")
        
        if not self.name or not self.name.strip():
            raise ValueError("Name cannot be empty")
            
        if self.price is None or self.price < 0:
            raise ValueError("Price must be a non-negative number")