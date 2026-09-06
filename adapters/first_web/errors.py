"""Error types for the FIRST web provider adapter."""


class FirstWebError(Exception):
    """Base error for FIRST web provider failures."""


class FirstWebTimeoutError(FirstWebError):
    """The FIRST provider request timed out."""


class FirstWebRequestError(FirstWebError):
    """The FIRST provider request failed."""
