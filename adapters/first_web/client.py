"""HTTP client for the FIRST grant opportunity page."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

import requests

from adapters.first_web.errors import (
    FirstWebRequestError,
    FirstWebTimeoutError,
)


@dataclass(frozen=True, slots=True)
class FirstWebFetchResult:
    """Successful FIRST provider fetch result."""

    html: str
    latency_seconds: float


class FirstWebClient:
    """Fetch grant opportunity HTML from FIRST."""

    def __init__(
        self,
        url: str,
        *,
        timeout: float = 10.0,
        session: requests.Session | None = None,
    ) -> None:
        self._url = url
        self._timeout = timeout
        self._session = session or requests.Session()

    def fetch(self) -> FirstWebFetchResult:
        """Fetch the provider page and return HTML with measured latency."""

        started_at = perf_counter()

        try:
            response = self._session.get(
                self._url,
                timeout=self._timeout,
            )

            response.raise_for_status()

        except requests.Timeout as error:
            raise FirstWebTimeoutError("FIRST provider request timed out") from error

        except requests.RequestException as error:
            raise FirstWebRequestError("FIRST provider request failed") from error

        latency_seconds = perf_counter() - started_at

        return FirstWebFetchResult(
            html=response.text,
            latency_seconds=latency_seconds,
        )
