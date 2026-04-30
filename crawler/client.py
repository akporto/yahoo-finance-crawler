import logging
import time
from typing import Iterator
from requests.exceptions import RequestException, HTTPError

from crawler.session import YahooSession

logger = logging.getLogger(__name__)

_SCREENER_URL = "https://query2.finance.yahoo.com/v1/finance/screener"
_PAGE_SIZE = 100
_MAX_RETRIES = 3

# Maps human-readable region names to Yahoo Finance region codes.
# Accepts both full names ("Argentina") and ISO codes ("ar") in the CLI.
REGION_MAP: dict[str, str] = {
    "argentina": "ar", "australia": "au", "austria": "at",
    "belgium": "be", "brazil": "br", "canada": "ca",
    "chile": "cl", "china": "cn", "czech republic": "cz",
    "denmark": "dk", "egypt": "eg", "finland": "fi",
    "france": "fr", "germany": "de", "greece": "gr",
    "hong kong": "hk", "hungary": "hu", "india": "in",
    "indonesia": "id", "ireland": "ie", "israel": "il",
    "italy": "it", "japan": "jp", "malaysia": "my",
    "mexico": "mx", "netherlands": "nl", "new zealand": "nz",
    "norway": "no", "pakistan": "pk", "peru": "pe",
    "philippines": "ph", "poland": "pl", "portugal": "pt",
    "qatar": "qa", "russia": "ru", "saudi arabia": "sa",
    "singapore": "sg", "south africa": "za", "south korea": "kr",
    "spain": "es", "sweden": "se", "switzerland": "ch",
    "taiwan": "tw", "thailand": "th", "turkey": "tr",
    "united kingdom": "gb", "united states": "us",
    "venezuela": "ve", "vietnam": "vn",
}


def resolve_region_code(region_name: str) -> str:
    """
    Resolves a region name or ISO code to a Yahoo Finance region code.

    Raises:
        ValueError: If the region cannot be resolved.
    """
    normalized = region_name.strip().lower()

    if normalized in REGION_MAP.values():
        return normalized

    code = REGION_MAP.get(normalized)
    if not code:
        available = ", ".join(sorted(REGION_MAP.keys()))
        raise ValueError(f"Unknown region: '{region_name}'.\nAvailable regions: {available}")
    return code


def _build_payload(region_code: str, offset: int, size: int) -> dict:
    return {
        "offset": offset,
        "size": size,
        "sortField": "intradaymarketcap",
        "sortType": "DESC",
        "quoteType": "EQUITY",
        "query": {
            "operator": "AND",
            "operands": [{"operator": "eq", "operands": ["region", region_code]}],
        },
        "userId": "",
        "userIdType": "guid",
    }


class YahooFinanceScreenerClient:
    """
    Client for the Yahoo Finance Screener API.

    Handles authentication, pagination, and resilient HTTP requests
    with exponential backoff. Yields raw JSON quote records lazily.
    """

    def __init__(self, session: YahooSession | None = None):
        self._session = session or YahooSession()

    def _post_with_retry(self, payload: dict) -> dict:
        """
        Raises:
            HTTPError: On 401/403 — stops immediately to avoid permanent block.
            RequestException: After all retries are exhausted.
        """
        crumb = self._session.crumb

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = self._session.post(
                    _SCREENER_URL,
                    params={"crumb": crumb, "lang": "en-US", "region": "US"},
                    json=payload,
                    timeout=20,
                )

                if response.status_code in (401, 403):
                    raise HTTPError(
                        f"Access denied: {response.status_code}", response=response
                    )

                response.raise_for_status()
                return response.json()

            except RequestException as e:
                logger.warning(f"Attempt {attempt}/{_MAX_RETRIES} failed: {e}")
                if attempt == _MAX_RETRIES:
                    raise
                time.sleep(2 ** (attempt - 1))

    def fetch_all(self, region_code: str) -> Iterator[dict]:
        """Lazily yields all equity records for a region, paginating automatically."""
        offset = 0
        total = None

        while True:
            payload = _build_payload(region_code, offset, _PAGE_SIZE)
            data = self._post_with_retry(payload)

            try:
                result = data["finance"]["result"][0]
                quotes = result.get("quotes", [])
                total = result.get("total", 0)
            except (KeyError, IndexError, TypeError) as e:
                logger.error(f"Unexpected API response structure: {e}")
                break

            if not quotes:
                break

            logger.info(f"Fetched {len(quotes)} records (offset={offset}, total={total})")
            yield from quotes

            offset += len(quotes)

            if total is not None and offset >= total:
                break

            time.sleep(0.5)
