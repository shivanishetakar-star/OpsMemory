"""Tests for configuration validation and safe error translation."""

from pathlib import Path

import pytest
from hindsight_client_api.exceptions import (
    ApiException,
    ApiValueError,
    BadRequestException,
    ForbiddenException,
    NotFoundException,
    ServiceException,
    UnauthorizedException,
)

from error_handling import (
    ConfigurationError,
    InvestigationError,
    load_config,
    translate_error,
)

SECRET_SENTINEL = "SENTINEL_SECRET_DO_NOT_LEAK"


def valid_env(**overrides):
    env = {
        "HINDSIGHT_API_KEY": SECRET_SENTINEL,
        "HINDSIGHT_BASE_URL": "https://api.hindsight.vectorize.io",
        "HINDSIGHT_BANK_ID": "OpsMemory",
    }
    env.update(overrides)
    return env


# --- Configuration validation -------------------------------------------


def test_missing_api_key():
    env = valid_env()
    del env["HINDSIGHT_API_KEY"]
    with pytest.raises(ConfigurationError) as exc_info:
        load_config(env)
    assert "HINDSIGHT_API_KEY" in str(exc_info.value)
    assert SECRET_SENTINEL not in str(exc_info.value)


def test_missing_base_url():
    env = valid_env()
    del env["HINDSIGHT_BASE_URL"]
    with pytest.raises(ConfigurationError) as exc_info:
        load_config(env)
    assert "HINDSIGHT_BASE_URL" in str(exc_info.value)


def test_missing_bank_id():
    env = valid_env()
    del env["HINDSIGHT_BANK_ID"]
    with pytest.raises(ConfigurationError) as exc_info:
        load_config(env)
    assert "HINDSIGHT_BANK_ID" in str(exc_info.value)


def test_blank_values_are_treated_as_missing():
    env = valid_env(HINDSIGHT_API_KEY="   ", HINDSIGHT_BANK_ID="")
    with pytest.raises(ConfigurationError) as exc_info:
        load_config(env)
    assert "HINDSIGHT_API_KEY" in str(exc_info.value)
    assert "HINDSIGHT_BANK_ID" in str(exc_info.value)
    assert "HINDSIGHT_BASE_URL" not in str(exc_info.value)


def test_invalid_base_url_scheme():
    env = valid_env(HINDSIGHT_BASE_URL="not-a-url")
    with pytest.raises(ConfigurationError) as exc_info:
        load_config(env)
    assert "http" in str(exc_info.value)


def test_api_keys_dashboard_url_rejected():
    env = valid_env(
        HINDSIGHT_BASE_URL="https://api.hindsight.vectorize.io/api-keys"
    )
    with pytest.raises(ConfigurationError) as exc_info:
        load_config(env)
    assert "dashboard" in str(exc_info.value).lower()
    assert "api root" in str(exc_info.value).lower()


def test_valid_config_is_returned():
    config = load_config(valid_env())
    assert config.api_key == SECRET_SENTINEL
    assert config.base_url == "https://api.hindsight.vectorize.io"
    assert config.bank_id == "OpsMemory"


def test_trailing_slash_is_stripped():
    config = load_config(
        valid_env(HINDSIGHT_BASE_URL="https://api.example.com/")
    )
    assert config.base_url == "https://api.example.com"


# --- Error translation ---------------------------------------------------


def test_translate_unauthorized():
    exc = UnauthorizedException(status=401, reason="Unauthorized", body=SECRET_SENTINEL)
    error = translate_error(exc)
    assert isinstance(error, InvestigationError)
    assert error.category == "authentication"
    assert "HINDSIGHT_API_KEY" in error.user_message
    assert SECRET_SENTINEL not in error.user_message


def test_translate_forbidden():
    error = translate_error(ForbiddenException(status=403, reason="Forbidden"))
    assert error.category == "authentication"


def test_translate_not_found_includes_base_url_hint():
    body = '{"detail":"Not Found"}'
    error = translate_error(
        NotFoundException(status=404, reason="Not Found", body=body)
    )
    assert error.category == "not_found"
    assert "HINDSIGHT_BASE_URL" in error.user_message
    assert "HINDSIGHT_BANK_ID" in error.user_message
    assert body not in error.user_message


def test_translate_service_unavailable():
    error = translate_error(ServiceException(status=503, reason="Service Unavailable"))
    assert error.category == "service_unavailable"
    assert "unavailable" in error.user_message.lower()


def test_translate_bad_request():
    error = translate_error(
        BadRequestException(status=400, reason="Bad Request", body=SECRET_SENTINEL)
    )
    assert error.category == "bad_request"
    assert SECRET_SENTINEL not in error.user_message


def test_translate_rate_limited():
    error = translate_error(ApiException(status=429, reason="Too Many Requests"))
    assert error.category == "rate_limited"


def test_translate_connection_error():
    import aiohttp

    error = translate_error(aiohttp.ClientConnectionError("connection refused"))
    assert error.category == "connection"
    assert "network" in error.user_message.lower()


def test_translate_timeout():
    error = translate_error(TimeoutError("timed out"))
    assert error.category == "timeout"
    assert "timed out" in error.user_message.lower()


def test_translate_unexpected_api_response():
    error = translate_error(ApiValueError(f"bad payload {SECRET_SENTINEL}"))
    assert error.category == "unexpected_response"
    assert SECRET_SENTINEL not in error.user_message


def test_translate_unexpected_python_exception_is_generic():
    error = translate_error(RuntimeError(f"boom {SECRET_SENTINEL}"))
    assert error.category == "unexpected"
    assert SECRET_SENTINEL not in error.user_message


def test_error_messages_never_contain_exception_text():
    """No translation should include str(exc) or response data."""
    exceptions = [
        UnauthorizedException(status=401, reason="Unauthorized", body=SECRET_SENTINEL),
        NotFoundException(status=404, reason="Not Found", body=SECRET_SENTINEL),
        ApiValueError(f"parse failed: {SECRET_SENTINEL}"),
        TimeoutError(f"timeout after {SECRET_SENTINEL}"),
        RuntimeError(f"crash {SECRET_SENTINEL}"),
    ]
    for exc in exceptions:
        message = translate_error(exc).user_message
        assert SECRET_SENTINEL not in message
