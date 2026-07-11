"""Advisor exceptions."""

from __future__ import annotations


class AdvisorError(RuntimeError):
    """Base class for advisor failures."""


class AdvisorUnavailableError(AdvisorError):
    """Raised when a configured advisor cannot be reached or configured."""


class AdvisorResponseError(AdvisorError):
    """Raised when an advisor returns invalid JSON or invalid fields."""

    def __init__(self, message: str, raw_response: str | None = None) -> None:
        super().__init__(message)
        self.raw_response = raw_response
