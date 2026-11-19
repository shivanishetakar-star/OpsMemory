"""Configuration validation and safe error translation for OpsMemory.

Every function in this module returns user-facing messages that never include
API keys, response bodies, headers, or other sensitive data.
"""

import os
from dataclasses import dataclass
from typing import Mapping, Optional
from urllib.parse import urlparse

import aiohttp
from hindsight_client_api.exceptions import (
    ApiException,
    ApiAttributeError,
    ApiValueError,
    BadRequestException,
    ForbiddenException,
    NotFoundException,
    ServiceException,
    UnauthorizedException,
)


@dataclass(frozen=True)
class HindsightConfig:
    """Validated Hindsight configuration."""

    api_key: str
    base_url: str
    bank_id: str


class ConfigurationError(Exception):
    """Raised when local configuration is missing or invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.user_message = message


class InvestigationError(Exception):
    """Raised when an investigation fails in a way that is safe to show."""

    def __init__(self, message: str, category: str = "unexpected") -> None:
        super().__init__(message)
        self.user_message = message
        self.category = category


REQUIRED_ENV_VARS = ("HINDSIGHT_API_KEY", "HINDSIGHT_BASE_URL", "HINDSIGHT_BANK_ID")


def load_config(env: Optional[Mapping[str, str]] = None) -> HindsightConfig:
    """Validate Hindsight configuration from environment variables.

    Raises:
        ConfigurationError: if any required value is missing or the base URL
            is not a valid ``http(s)`` URL.
    """
    if env is None:
        env = os.environ

    values = {
        name: (env.get(name) or "").strip()
        for name in REQUIRED_ENV_VARS
    }

    missing = [name for name, value in values.items() if not value]
    if missing:
        raise ConfigurationError(
            "Missing Hindsight configuration: "
            + ", ".join(missing)
            + ". Add the missing values to backend/.env."
        )

    base_url = values["HINDSIGHT_BASE_URL"]
    parsed = urlparse(base_url)

    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ConfigurationError(
            "HINDSIGHT_BASE_URL must be a full URL starting with http:// or https://."
        )

    if parsed.path.rstrip("/").endswith("/api-keys"):
        raise ConfigurationError(
            "HINDSIGHT_BASE_URL points to an API-keys dashboard page. "
            "Use the Hindsight API root instead (for example, "
            "https://api.hindsight.vectorize.io)."
        )

    return HindsightConfig(
        api_key=values["HINDSIGHT_API_KEY"],
        base_url=base_url.rstrip("/"),
        bank_id=values["HINDSIGHT_BANK_ID"],
    )


def translate_error(exc: BaseException) -> InvestigationError:
    """Convert an exception into a safe, user-facing :class:`InvestigationError`.

    The message never includes ``str(exc)`` or any response data, because the
    underlying exception can contain tokens, headers, or API response bodies.
    """
    if isinstance(exc, (UnauthorizedException, ForbiddenException)):
        return InvestigationError(
            "Hindsight authentication failed. Check that "
            "HINDSIGHT_API_KEY is valid and has access to the configured "
            "memory bank.",
            "authentication",
        )

    if isinstance(exc, NotFoundException):
        return InvestigationError(
            "Hindsight could not find the configured endpoint or memory bank. "
            "Check HINDSIGHT_BASE_URL (use the API root, not a dashboard "
            "page) and HINDSIGHT_BANK_ID.",
            "not_found",
        )

    if isinstance(exc, ServiceException):
        return InvestigationError(
            "Hindsight is temporarily unavailable. Please try again shortly.",
            "service_unavailable",
        )

    if isinstance(exc, BadRequestException):
        return InvestigationError(
            "Hindsight rejected the request. Check the incident inputs and "
            "configuration.",
            "bad_request",
        )

    if isinstance(exc, ApiException):
        status = exc.status
        if status == 429:
            return InvestigationError(
                "Hindsight is temporarily rate-limiting requests. "
                "Please try again shortly.",
                "rate_limited",
            )
        if status == 0:
            return InvestigationError(
                "Hindsight returned an unexpected response. Please try again.",
                "unexpected_response",
            )
        return InvestigationError(
            f"Hindsight returned an unexpected API error (HTTP {status}).",
            "api_error",
        )

    if isinstance(exc, TimeoutError):
        return InvestigationError(
            "The Hindsight request timed out. Please try again.",
            "timeout",
        )

    if isinstance(exc, aiohttp.ClientConnectionError):
        return InvestigationError(
            "Could not connect to Hindsight. Check your network connection "
            "and HINDSIGHT_BASE_URL.",
            "connection",
        )

    if isinstance(exc, (aiohttp.ClientPayloadError, aiohttp.ContentTypeError)):
        return InvestigationError(
            "Hindsight returned an unexpected response. Please try again.",
            "unexpected_response",
        )

    if isinstance(exc, aiohttp.ClientResponseError):
        return InvestigationError(
            f"Hindsight returned an unexpected response (HTTP {exc.status}).",
            "unexpected_response",
        )

    if isinstance(exc, aiohttp.ClientError):
        return InvestigationError(
            "Could not communicate with Hindsight. Check your network "
            "connection and HINDSIGHT_BASE_URL.",
            "connection",
        )

    if isinstance(exc, (ApiValueError, ApiAttributeError, ValueError, TypeError)):
        return InvestigationError(
            "Hindsight returned an unexpected response. Please try again.",
            "unexpected_response",
        )

    return InvestigationError(
        "The investigation failed unexpectedly. Please try again.",
        "unexpected",
    )
