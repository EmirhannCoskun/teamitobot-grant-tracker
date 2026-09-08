from unittest.mock import patch

import pytest
import requests

from adapters.first_web.client import (
    FirstWebClient,
    FirstWebFetchResult,
)
from adapters.first_web.errors import (
    FirstWebRequestError,
    FirstWebTimeoutError,
)


class FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        pass


class FakeSession:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.requested_url = None
        self.requested_timeout = None

    def get(self, url: str, timeout: float):
        self.requested_url = url
        self.requested_timeout = timeout
        return self.response


def test_fetch_returns_typed_result_with_latency():
    response = FakeResponse("<html>FIRST grants</html>")
    session = FakeSession(response)

    client = FirstWebClient(
        "https://example.com/grants",
        timeout=5.0,
        session=session,
    )

    with patch(
        "adapters.first_web.client.perf_counter",
        side_effect=[100.0, 100.25],
    ):
        result = client.fetch()

    assert isinstance(result, FirstWebFetchResult)
    assert result.html == "<html>FIRST grants</html>"
    assert result.latency_seconds == 0.25


def test_fetch_uses_configured_url_and_timeout():
    response = FakeResponse("<html></html>")
    session = FakeSession(response)

    client = FirstWebClient(
        "https://example.com/grants",
        timeout=7.5,
        session=session,
    )

    client.fetch()

    assert session.requested_url == "https://example.com/grants"
    assert session.requested_timeout == 7.5


def test_fetch_converts_http_error_to_provider_request_error():
    class ErrorResponse(FakeResponse):
        def raise_for_status(self) -> None:
            raise requests.HTTPError("Server error")

    response = ErrorResponse("")
    session = FakeSession(response)

    client = FirstWebClient(
        "https://example.com/grants",
        session=session,
    )

    with pytest.raises(FirstWebRequestError):
        client.fetch()


def test_fetch_converts_timeout_to_provider_timeout_error():
    class TimeoutSession:
        def get(self, url: str, timeout: float):
            raise requests.Timeout("Request timed out")

    client = FirstWebClient(
        "https://example.com/grants",
        session=TimeoutSession(),
    )

    with pytest.raises(FirstWebTimeoutError):
        client.fetch()


def test_fetch_converts_request_error_to_provider_request_error():
    class FailingSession:
        def get(self, url: str, timeout: float):
            raise requests.ConnectionError("Connection failed")

    client = FirstWebClient(
        "https://example.com/grants",
        session=FailingSession(),
    )

    with pytest.raises(FirstWebRequestError):
        client.fetch()
