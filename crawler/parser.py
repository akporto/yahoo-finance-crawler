import logging
from bs4 import BeautifulSoup
from typing import Optional
from crawler.models import StockData

logger = logging.getLogger(__name__)


class YahooFinanceParser:
    """
    Parses HTML content from Yahoo Finance and converts it into a StockData model.
    """

    @staticmethod
    def parse(html_content: str, symbol: str) -> Optional[StockData]:
        """
        Extracts financial data from HTML and returns a validated StockData object.
        Returns None if parsing fails or if blocked by CAPTCHA.
        """
        if not html_content:
            logger.warning(f"Empty HTML content provided for symbol: {symbol}")
            return None

        # Detects possible scraping blocks (CAPTCHA / bot checkpoint)
        html_lower = html_content.lower()
        if "captcha" in html_lower or "bot checkpoint" in html_lower:
            logger.error(f"Blocked by CAPTCHA for symbol: {symbol}. Scraping interrupted.")
            return None

        soup = BeautifulSoup(html_content, "html.parser")

        try:
            name_tag = soup.find("h1")
            name = name_tag.text.strip() if name_tag else "Unknown"

            price_tag = soup.find("fin-streamer", {"data-field": "regularMarketPrice"})
            if not price_tag:
                raise ValueError("Price element not found in HTML")
            
            price_str = price_tag.text.strip().replace(",", "")
            price = float(price_str)

            change_tag = soup.find("fin-streamer", {"data-field": "regularMarketChange"})
            change = float(change_tag.text.strip().replace(",", "")) if change_tag else None

            change_pct_tag = soup.find("fin-streamer", {"data-field": "regularMarketChangePercent"})
            if change_pct_tag:
                pct_str = (
                    change_pct_tag.text
                    .replace("(", "")
                    .replace(")", "")
                    .replace("%", "")
                    .strip()
                )
                change_percent = float(pct_str)
            else:
                change_percent = None

            logger.info(f"Parsed {symbol} | Price: {price}")
            
            return StockData(
                symbol=symbol.upper(),
                name=name,
                price=price,
                change=change,
                change_percent=change_percent
            )

        except (AttributeError, ValueError):
            logger.exception(f"Failed to parse HTML for {symbol} | Possible layout change")
            return None