"""Automated tests for the rule-based memory classification logic.

These tests exercise ``classify_memories`` directly with in-memory objects,
so no Hindsight API key, network connection, or Streamlit UI is required.
"""

from types import SimpleNamespace

import pytest

from classification import classify_memories


@pytest.fixture
def memory():
    """Create a minimal memory object exposing a ``text`` attribute."""

    def factory(text):
        return SimpleNamespace(text=text)

    return factory


def indices(group):
    """Return the sorted memory indices from a classification group."""
    return sorted(index for index, _ in group)


def test_exact_incident_match(memory):
    """A memory matching service, error and deployment is an exact match."""
    memories = [
        memory("Service: Payment API Error: HTTP 502 Deployment: v2.6")
    ]
    exact, related, resolution = classify_memories(
        memories, "Payment API", "HTTP 502", "v2.6"
    )
    assert indices(exact) == [1]
    assert indices(related) == []
    assert indices(resolution) == []


def test_related_historical_incident(memory):
    """Same service with different error and deployment is a related pattern."""
    memories = [
        memory("Service: Payment API Error: HTTP 500 Deployment: v2.7")
    ]
    exact, related, resolution = classify_memories(
        memories, "Payment API", "HTTP 502", "v2.6"
    )
    assert indices(exact) == []
    assert indices(related) == [1]
    assert indices(resolution) == []


def test_different_service_is_not_classified(memory):
    """Memories for another service are ignored entirely."""
    memories = [
        memory("Service: User API Error: HTTP 502 Deployment: v2.6")
    ]
    exact, related, resolution = classify_memories(
        memories, "Payment API", "HTTP 502", "v2.6"
    )
    assert indices(exact) == []
    assert indices(related) == []
    assert indices(resolution) == []


def test_matching_service_with_different_http_error_is_related(memory):
    """Matching service but different HTTP error is related, not exact."""
    memories = [
        memory("Service: Payment API Error: HTTP 500 Deployment: v2.6")
    ]
    exact, related, resolution = classify_memories(
        memories, "Payment API", "HTTP 502", "v2.6"
    )
    assert indices(exact) == []
    assert indices(related) == [1]
    assert indices(resolution) == []


def test_matching_service_with_different_deployment_is_related(memory):
    """Matching service but different deployment version is related."""
    memories = [
        memory("Service: Payment API Error: HTTP 502 Deployment: v2.7")
    ]
    exact, related, resolution = classify_memories(
        memories, "Payment API", "HTTP 502", "v2.6"
    )
    assert indices(exact) == []
    assert indices(related) == [1]
    assert indices(resolution) == []


def test_historical_resolution_evidence(memory):
    """A memory naming the service with resolution wording is resolution evidence."""
    memories = [
        memory("Service: Payment API Root Cause: Database timeout Resolution: Rolled back deployment")
    ]
    exact, related, resolution = classify_memories(
        memories, "Payment API", "HTTP 502", "v2.6"
    )
    assert indices(exact) == []
    assert indices(related) == []
    assert indices(resolution) == [1]


def test_empty_memory_list(memory):
    """An empty memory list returns three empty groups."""
    exact, related, resolution = classify_memories(
        [], "Payment API", "HTTP 502", "v2.6"
    )
    assert exact == []
    assert related == []
    assert resolution == []


def test_memory_without_matching_service_is_not_classified(memory):
    """Matching error/deployment and resolution keywords alone are insufficient."""
    memories = [
        memory("Service: User API Error: HTTP 502 Deployment: v2.6 Resolution: Restarted redis")
    ]
    exact, related, resolution = classify_memories(
        memories, "Payment API", "HTTP 502", "v2.6"
    )
    assert indices(exact) == []
    assert indices(related) == []
    assert indices(resolution) == []


@pytest.mark.parametrize(
    "word",
    ["resolved", "resolution", "fixed", "restarted", "reducing", "reduced"],
)
def test_resolution_keywords_are_detected(memory, word):
    """Each recognized resolution keyword classifies a memory as resolution evidence."""
    memories = [memory(f"Service: Payment API {word} the issue")]
    exact, related, resolution = classify_memories(
        memories, "Payment API", "HTTP 502", "v2.6"
    )
    assert indices(exact) == []
    assert indices(related) == []
    assert indices(resolution) == [1]


def test_multiple_memories_have_independent_classifications(memory):
    """Each memory is classified independently; overlap between groups is allowed."""
    memories = [
        memory("Service: Payment API Error: HTTP 502 Deployment: v2.6"),           # exact
        memory("Service: Payment API Error: HTTP 500 Deployment: v2.7"),           # related
        memory("Service: Order API Error: HTTP 502 Deployment: v3.1"),             # unrelated
        memory("Service: Payment API Error: HTTP 502 Deployment: v2.6 Resolved"),  # exact + resolution
        memory("Service: Payment API Root Cause: Timeout Resolution: Fixed"),      # resolution only
    ]
    exact, related, resolution = classify_memories(
        memories, "Payment API", "HTTP 502", "v2.6"
    )
    assert indices(exact) == [1, 4]
    assert indices(related) == [2]
    assert indices(resolution) == [4, 5]


def test_matching_is_case_insensitive_and_normalizes_error_whitespace(memory):
    """Inputs are matched case-insensitively; HTTP error whitespace is normalized."""
    memories = [
        memory("Service: payment api error: http 502 deployment: v2.6")
    ]
    exact, related, resolution = classify_memories(
        memories, "PAYMENT API", "HTTP   502", "V2.6"
    )
    assert indices(exact) == [1]
    assert indices(related) == []
    assert indices(resolution) == []


def test_exact_match_takes_precedence_over_related_pattern(memory):
    """A memory containing the target error is exact even when another error is present."""
    memories = [
        memory("Service: Payment API Error: HTTP 502 Deployment: v2.6 Error: HTTP 500")
    ]
    exact, related, resolution = classify_memories(
        memories, "Payment API", "HTTP 502", "v2.6"
    )
    assert indices(exact) == [1]
    assert indices(related) == []


def test_earlier_incident_suffix_does_not_create_exact_match(memory):
    """An exact incident appearing only after '(earlier:' is related, not exact."""
    memories = [
        memory(
            "Service: Payment API Error: HTTP 500 Deployment: v2.7 "
            "(earlier: Service: Payment API Error: HTTP 502 Deployment: v2.6)"
        )
    ]
    exact, related, resolution = classify_memories(
        memories, "Payment API", "HTTP 502", "v2.6"
    )
    assert indices(exact) == []
    assert indices(related) == [1]
    assert indices(resolution) == []


def test_resolution_evidence_scans_full_text_across_categories(memory):
    """Resolution evidence uses the full text, so related memories can also be resolution evidence."""
    memories = [
        memory(
            "Service: Payment API Error: HTTP 500 Deployment: v2.7 "
            "(earlier: Service: Payment API Error: HTTP 502 Deployment: v2.6 Resolution: Fixed the issue)"
        )
    ]
    exact, related, resolution = classify_memories(
        memories, "Payment API", "HTTP 502", "v2.6"
    )
    assert indices(exact) == []
    assert indices(related) == [1]
    assert indices(resolution) == [1]
