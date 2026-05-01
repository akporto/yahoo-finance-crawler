import pytest
from unittest.mock import MagicMock, patch
from requests.exceptions import RequestException, Timeout, HTTPError

from crawler.session import YahooSession


class TestYahooSession:

    def _make_session(self):
        with patch("crawler.session.requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            session = YahooSession()
            return session, mock_session

    def test_authenticates_lazily_on_first_crumb_access(self):
        session, _ = self._make_session()
        with patch.object(session, "authenticate") as mock_auth:
            mock_auth.side_effect = lambda: setattr(session, "_crumb", "test-crumb")
            crumb = session.crumb
            mock_auth.assert_called_once()
            assert crumb == "test-crumb"

    def test_does_not_reauthenticate_if_crumb_exists(self):
        session, _ = self._make_session()
        session._crumb = "existing-crumb"
        with patch.object(session, "authenticate") as mock_auth:
            assert session.crumb == "existing-crumb"
            mock_auth.assert_not_called()

    def test_accept_consent_posts_when_redirected_to_consent_url(self):
        session, mock_requests_session = self._make_session()
        mock_response = MagicMock()
        mock_response.url = "https://consent.yahoo.com/something"
        mock_requests_session.get.return_value = mock_response

        session._accept_consent()

        mock_requests_session.post.assert_called_once()

    def test_accept_consent_skips_post_when_not_redirected(self):
        session, mock_requests_session = self._make_session()
        mock_response = MagicMock()
        mock_response.url = "https://finance.yahoo.com/"
        mock_requests_session.get.return_value = mock_response

        session._accept_consent()

        mock_requests_session.post.assert_not_called()

    def test_accept_consent_is_non_fatal_on_network_error(self):
        session, mock_requests_session = self._make_session()
        mock_requests_session.get.side_effect = RequestException("timeout")

        session._accept_consent()

    def test_fetch_crumb_returns_crumb_text(self):
        session, mock_requests_session = self._make_session()
        mock_response = MagicMock()
        mock_response.text = "  abc123crumb  "
        mock_requests_session.get.return_value = mock_response

        crumb = session._fetch_crumb()

        assert crumb == "abc123crumb"

    def test_fetch_crumb_raises_on_empty_response(self):
        session, mock_requests_session = self._make_session()
        mock_response = MagicMock()
        mock_response.text = "   "
        mock_requests_session.get.return_value = mock_response

        with pytest.raises(ValueError, match="Empty crumb"):
            session._fetch_crumb()

    def test_fetch_crumb_propagates_timeout_error(self):
        session, mock_requests_session = self._make_session()
        mock_requests_session.get.side_effect = Timeout("request timed out")

        with pytest.raises(Timeout):
            session._fetch_crumb()

    def test_fetch_crumb_propagates_http_error_from_raise_for_status(self):
        session, mock_requests_session = self._make_session()
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = HTTPError("500 server error")
        mock_requests_session.get.return_value = mock_response

        with pytest.raises(HTTPError):
            session._fetch_crumb()

    def test_authenticate_calls_consent_and_sets_crumb(self):
        session, _ = self._make_session()
        with patch.object(session, "_accept_consent") as mock_accept, patch.object(
            session, "_fetch_crumb", return_value="crumb-123"
        ):
            session.authenticate()

        mock_accept.assert_called_once()
        assert session._crumb == "crumb-123"

    def test_authenticate_propagates_fetch_crumb_failure(self):
        session, _ = self._make_session()
        with patch.object(session, "_accept_consent") as mock_accept, patch.object(
            session, "_fetch_crumb", side_effect=Timeout("network failure")
        ):
            with pytest.raises(Timeout):
                session.authenticate()

        mock_accept.assert_called_once()
