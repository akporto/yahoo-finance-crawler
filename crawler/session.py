import logging
import requests
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)

_CONSENT_URL = "https://consent.yahoo.com/v2/collectConsent"
_CRUMB_URL = "https://query2.finance.yahoo.com/v1/test/getcrumb"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


class YahooSession:
    """
    Manages authenticated session state for the Yahoo Finance API.

    Yahoo's unofficial API requires a crumb token paired with a session cookie.
    The crumb is obtained after a consent handshake and is lazily initialized
    on first use via the `crumb` property.
    """

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update(_HEADERS)
        self._crumb: str | None = None

    def _accept_consent(self) -> None:
        try:
            resp = self._session.get("https://finance.yahoo.com/", timeout=15, allow_redirects=True)
            if "consent.yahoo.com" in resp.url:
                self._session.post(
                    _CONSENT_URL,
                    data={"agree": "agree", "consentUUID": "default"},
                    timeout=15,
                )
        except RequestException as e:
            logger.warning(f"Consent step failed (non-fatal): {e}")

    def _fetch_crumb(self) -> str:
        resp = self._session.get(_CRUMB_URL, timeout=15)
        resp.raise_for_status()
        crumb = resp.text.strip()
        if not crumb:
            raise ValueError("Empty crumb received from Yahoo Finance.")
        return crumb

    def authenticate(self) -> None:
        logger.info("Authenticating with Yahoo Finance...")
        self._accept_consent()
        self._crumb = self._fetch_crumb()

    @property
    def crumb(self) -> str:
        if not self._crumb:
            self.authenticate()
        return self._crumb

    def post(self, url: str, **kwargs) -> requests.Response:
        return self._session.post(url, **kwargs)
