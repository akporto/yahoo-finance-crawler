import logging
import time
import requests
from requests.exceptions import RequestException, HTTPError

logger = logging.getLogger(__name__)


class YahooFinanceClient:
    """
    Client responsible for executing resilient HTTP requests to Yahoo Finance.
    """
    
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    TIMEOUT = 15
    MAX_RETRIES = 3

    @staticmethod
    def fetch_html(url: str) -> str:
        """
        Fetches the HTML content of a given URL with retry mechanisms.
        Interrupts completely if receiving specific blocking status codes.

        Raises:
            RequestException: If all retries fail or a blocking status is encountered.
        """
        for attempt in range(1, YahooFinanceClient.MAX_RETRIES + 1):
            try:
                logger.info(f"Fetching URL (Attempt {attempt}/{YahooFinanceClient.MAX_RETRIES}): {url}")
                response = requests.get(
                    url, 
                    headers=YahooFinanceClient.HEADERS, 
                    timeout=YahooFinanceClient.TIMEOUT
                )
                
                if response.status_code in (401, 403):
                    logger.error(f"Access denied (HTTP {response.status_code}). Stopping attempts to prevent permanent block.")
                    raise HTTPError(f"Access denied: {response.status_code}", response=response)
                    
                response.raise_for_status()
                return response.text if response.text else ""
                
            except RequestException as e:
                status = getattr(e.response, "status_code", None)
                logger.warning(f"Attempt {attempt} failed (status={status}): {e}")
                
                if attempt == YahooFinanceClient.MAX_RETRIES:
                    logger.error("Max retries reached. Failing process.")
                    raise
                
                time.sleep(2 ** (attempt - 1))