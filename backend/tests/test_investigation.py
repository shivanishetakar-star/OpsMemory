"""Tests for the investigation workflow with mocked Hindsight client."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from hindsight_client_api.exceptions import UnauthorizedException

from error_handling import HindsightConfig, InvestigationError
from investigation import (
    deduplicate_memories,
    extract_cited_ids,
    run_investigation,
)

CONFIG = HindsightConfig(
    api_key="test-key",
    base_url="https://api.example.com",
    bank_id="test-bank",
)


def make_client(recall_results, reflect_text="Report citing Memory 1"):
    client = Mock()
    client.recall.return_value = SimpleNamespace(results=recall_results)
    client.reflect.return_value = SimpleNamespace(text=reflect_text)
    return client


def test_successful_investigation_flow():
    memories = [
        SimpleNamespace(text="Service: Payment API Error: HTTP 502 Deployment: v2.6"),
        SimpleNamespace(text="service: payment api error: http 502 deployment: v2.6"),  # duplicate
        SimpleNamespace(text="Service: Payment API Error: HTTP 500 Deployment: v2.7"),
        SimpleNamespace(text="Service: Payment API Root Cause: Timeout Resolution: Fixed"),
    ]
    client = make_client(
        memories,
        reflect_text="Report. See Memory 1 and Memory 3.",
    )

    result = run_investigation(
        client, CONFIG, "Payment API", "HTTP 502", "v2.6",
    )

    assert result.empty is False
    assert result.has_evidence is True
    assert len(result.memories) == 4
    assert len(result.unique_results) == 3
    assert result.duplicates_removed == 1
    assert [i for i, _ in result.exact_matches] == [1]
    assert [i for i, _ in result.related_patterns] == [2]
    assert [i for i, _ in result.resolution_evidence] == [3]
    assert result.cited_ids == [1, 3]
    assert result.analysis_text.startswith("Report.")
    client.recall.assert_called_once()
    client.reflect.assert_called_once()


def test_empty_recall_results_still_generate_report():
    """Empty recall is handled gracefully; the report is still generated."""
    client = make_client([], reflect_text="No historical evidence was available.")

    result = run_investigation(
        client, CONFIG, "Payment API", "HTTP 502", "v2.6",
    )

    assert result.empty is True
    assert result.has_evidence is False
    assert result.unique_results == []
    assert result.exact_matches == []
    assert result.analysis_text == "No historical evidence was available."
    client.reflect.assert_called_once()


def test_memories_but_no_matching_evidence():
    """Memories for a different service set has_evidence=False."""
    memories = [
        SimpleNamespace(text="Service: User API Error: HTTP 503 Deployment: v1.8"),
    ]
    client = make_client(memories, reflect_text="No matching evidence found.")

    result = run_investigation(
        client, CONFIG, "Payment API", "HTTP 502", "v2.6",
    )

    assert result.empty is False
    assert result.has_evidence is False
    assert len(result.unique_results) == 1
    assert result.exact_matches == []
    assert result.related_patterns == []
    assert result.resolution_evidence == []


def test_recall_missing_results_attribute():
    client = Mock()
    client.recall.return_value = SimpleNamespace()

    with pytest.raises(InvestigationError) as exc_info:
        run_investigation(client, CONFIG, "Payment API", "HTTP 502", "v2.6")
    assert exc_info.value.category == "unexpected_response"


def test_recall_results_is_none():
    client = Mock()
    client.recall.return_value = SimpleNamespace(results=None)

    with pytest.raises(InvestigationError) as exc_info:
        run_investigation(client, CONFIG, "Payment API", "HTTP 502", "v2.6")
    assert exc_info.value.category == "unexpected_response"


def test_recall_results_not_iterable():
    client = Mock()
    client.recall.return_value = SimpleNamespace(results=42)

    with pytest.raises(InvestigationError) as exc_info:
        run_investigation(client, CONFIG, "Payment API", "HTTP 502", "v2.6")
    assert exc_info.value.category == "unexpected_response"


def test_memory_without_text_attribute():
    client = Mock()
    client.recall.return_value = SimpleNamespace(
        results=[SimpleNamespace()],
    )

    with pytest.raises(InvestigationError) as exc_info:
        run_investigation(client, CONFIG, "Payment API", "HTTP 502", "v2.6")
    assert exc_info.value.category == "unexpected_response"


def test_recall_error_is_translated():
    client = Mock()
    client.recall.side_effect = UnauthorizedException(
        status=401, reason="Unauthorized", body="secret"
    )

    with pytest.raises(InvestigationError) as exc_info:
        run_investigation(client, CONFIG, "Payment API", "HTTP 502", "v2.6")
    assert exc_info.value.category == "authentication"
    assert "HINDSIGHT_API_KEY" in exc_info.value.user_message
    assert "secret" not in exc_info.value.user_message


def test_reflect_error_is_translated():
    from hindsight_client_api.exceptions import ServiceException

    memories = [
        SimpleNamespace(text="Service: Payment API Error: HTTP 502 Deployment: v2.6"),
    ]
    client = make_client(memories)
    client.reflect.side_effect = ServiceException(status=503, reason="Unavailable")

    with pytest.raises(InvestigationError) as exc_info:
        run_investigation(client, CONFIG, "Payment API", "HTTP 502", "v2.6")
    assert exc_info.value.category == "service_unavailable"


def test_reflect_missing_text_attribute():
    memories = [
        SimpleNamespace(text="Service: Payment API Error: HTTP 502 Deployment: v2.6"),
    ]
    client = make_client(memories)
    client.reflect.return_value = SimpleNamespace()

    with pytest.raises(InvestigationError) as exc_info:
        run_investigation(client, CONFIG, "Payment API", "HTTP 502", "v2.6")
    assert exc_info.value.category == "unexpected_response"


def test_reflect_empty_text():
    memories = [
        SimpleNamespace(text="Service: Payment API Error: HTTP 502 Deployment: v2.6"),
    ]
    client = make_client(memories)
    client.reflect.return_value = SimpleNamespace(text="   ")

    with pytest.raises(InvestigationError) as exc_info:
        run_investigation(client, CONFIG, "Payment API", "HTTP 502", "v2.6")
    assert exc_info.value.category == "unexpected_response"


def test_deduplicate_memories():
    memories = [
        SimpleNamespace(text="Payment API HTTP 502"),
        SimpleNamespace(text="payment   api   HTTP 502"),
        SimpleNamespace(text="Order API HTTP 502"),
    ]
    unique, removed = deduplicate_memories(memories)
    assert len(unique) == 2
    assert removed == 1


def test_extract_cited_ids():
    text = "See Memory 3, memory 1, and Memory 12."
    assert extract_cited_ids(text) == [1, 3, 12]
