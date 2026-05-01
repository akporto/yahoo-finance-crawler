import logging
from typing import Optional

from crawler.models import StockData

logger = logging.getLogger(__name__)


class YahooFinanceParser:
    """Transforms raw JSON quote records from the Screener API into StockData objects."""

    @classmethod
    def parse(cls, record: dict) -> Optional[StockData]:
        """
        Returns a validated StockData or None if the record is incomplete or invalid.
        Returning None allows the pipeline to skip bad records without interruption.
        """
        if not record or not isinstance(record, dict):
            return None

        symbol = record.get("symbol", "").strip()
        if not symbol:
            logger.warning("Record missing 'symbol'. Skipping.")
            return None

        name = (record.get("shortName") or record.get("longName") or "").strip()
        if not name:
            logger.warning(f"[{symbol}] Missing name. Skipping.")
            return None

        raw_price = record.get("regularMarketPrice")
        if raw_price is None:
            logger.warning(f"[{symbol}] Missing price. Skipping.")
            return None

        try:
            price = float(raw_price)
            if price < 0:
                raise ValueError(f"Negative price: {price}")
        except (TypeError, ValueError) as e:
            logger.warning(f"[{symbol}] Invalid price '{raw_price}': {e}. Skipping.")
            return None

        try:
            return StockData(
                symbol=symbol.upper(),
                name=name,
                price=price,
            )
        except ValueError as e:
            logger.warning(f"[{symbol}] Validation failed: {e}. Skipping.")
            return None
