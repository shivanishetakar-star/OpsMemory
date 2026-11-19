"""Testable investigation workflow for OpsMemory.

This module contains the core recall/reflect flow and its data structures so
that they can be unit-tested without launching Streamlit or contacting
Hindsight.
"""

import re
from dataclasses import dataclass
from typing import Any, List, Tuple

from classification import classify_memories
from error_handling import (
    HindsightConfig,
    InvestigationError,
    translate_error,
)

#: Category used for structurally invalid Hindsight responses.
UNEXPECTED_RESPONSE_CATEGORY = "unexpected_response"


@dataclass
class InvestigationResult:
    """Outcome of a completed investigation."""

    memories: List[Any]
    unique_results: List[Any]
    duplicates_removed: int
    exact_matches: List[Tuple[int, Any]]
    related_patterns: List[Tuple[int, Any]]
    resolution_evidence: List[Tuple[int, Any]]
    analysis_text: str
    cited_ids: List[int]
    empty: bool
    has_evidence: bool


def deduplicate_memories(memories: List[Any]) -> Tuple[List[Any], int]:
    """Remove exact duplicate memories by normalized text.

    Returns:
        ``(unique_memories, duplicates_removed)``.
    """
    unique: List[Any] = []
    seen: set = set()

    for memory in memories:
        normalized_text = " ".join(memory.text.split()).casefold()
        if normalized_text and normalized_text not in seen:
            seen.add(normalized_text)
            unique.append(memory)

    duplicates_removed = len(memories) - len(unique)
    return unique, duplicates_removed


def extract_cited_ids(text: str) -> List[int]:
    """Return the sorted ``Memory N`` IDs cited in ``text``."""
    return sorted({
        int(match)
        for match in re.findall(r"\bMemory\s+(\d+)\b", text, re.IGNORECASE)
    })


def format_evidence_group(title: str, memories: List[Tuple[int, Any]]) -> str:
    """Format one evidence group for the reflection context."""
    if not memories:
        return f"{title}\nNo matching memories found."

    entries = "\n\n".join(
        f"Memory {index}:\n{memory.text}"
        for index, memory in memories
    )
    return f"{title}\n{entries}"


def build_memory_context(
    exact_matches: List[Tuple[int, Any]],
    related_patterns: List[Tuple[int, Any]],
    resolution_evidence: List[Tuple[int, Any]],
) -> str:
    """Build the evidence context passed to Hindsight reflection."""
    return "\n\n".join([
        format_evidence_group("EXACT INCIDENT MATCHES", exact_matches),
        format_evidence_group("RELATED HISTORICAL PATTERNS", related_patterns),
        format_evidence_group("HISTORICAL RESOLUTION EVIDENCE", resolution_evidence),
    ])


def _validated_memories(response: Any) -> List[Any]:
    """Extract and validate the memories from a recall response."""
    if response is None or not hasattr(response, "results"):
        raise InvestigationError(
            "Hindsight returned an unexpected response (missing memory results).",
            UNEXPECTED_RESPONSE_CATEGORY,
        )

    results = response.results
    if results is None:
        raise InvestigationError(
            "Hindsight returned an unexpected response (missing memory results).",
            UNEXPECTED_RESPONSE_CATEGORY,
        )

    try:
        memories = list(results)
    except TypeError:
        raise InvestigationError(
            "Hindsight returned an unexpected response (invalid memory results).",
            UNEXPECTED_RESPONSE_CATEGORY,
        )

    for memory in memories:
        if not isinstance(getattr(memory, "text", None), str):
            raise InvestigationError(
                "Hindsight returned an unexpected response (invalid memory).",
                UNEXPECTED_RESPONSE_CATEGORY,
            )

    return memories


def _validated_analysis_text(analysis: Any) -> str:
    """Extract and validate the analysis text from a reflect response."""
    if analysis is None or not isinstance(getattr(analysis, "text", None), str):
        raise InvestigationError(
            "Hindsight returned an unexpected investigation report.",
            UNEXPECTED_RESPONSE_CATEGORY,
        )

    text = analysis.text
    if not text.strip():
        raise InvestigationError(
            "Hindsight returned an empty investigation report.",
            UNEXPECTED_RESPONSE_CATEGORY,
        )

    return text


def run_investigation(
    client: Any,
    config: HindsightConfig,
    service: str,
    error: str,
    deployment: str,
) -> InvestigationResult:
    """Run the full investigation workflow.

    Raises:
        InvestigationError: for expected Hindsight/network/response failures
            with a safe, user-facing message.
    """
    query = (
        f"Find historical production incidents involving "
        f"{service}, {error}, deployment {deployment}. "
        f"Retrieve their root causes and resolutions."
    )

    try:
        response = client.recall(bank_id=config.bank_id, query=query)
    except Exception as exc:
        raise translate_error(exc) from exc

    memories = _validated_memories(response)
    unique_results, duplicates_removed = deduplicate_memories(memories)
    exact_matches, related_patterns, resolution_evidence = classify_memories(
        unique_results, service, error, deployment,
    )

    memory_context = build_memory_context(
        exact_matches, related_patterns, resolution_evidence,
    )

    reflect_query = (
        "B. Relevant Historical Evidence\n"
        "C. Root Cause Analysis\n"
        f"Investigate this CURRENT production incident:\n"
        f"Service: {service}\n"
        f"Error: {error}\n"
        f"Deployment: {deployment}\n\n"
        "IMPORTANT INVESTIGATION RULES:\n"
        "1. Treat the supplied service, error, and deployment as the current incident.\n"
        "2. Use EXACT INCIDENT MATCHES only when the memory supports the relevant incident details.\n"
        "3. Use RELATED HISTORICAL PATTERNS only for comparisons across deployments or errors.\n"
        "4. Never present a related historical incident as an exact match.\n"
        "5. Use HISTORICAL RESOLUTION EVIDENCE only for claims about previous fixes.\n"
        "6. A memory may contain multiple incidents. Cite it only for the details it explicitly supports.\n"
        "7. Cite every historical claim using ONLY the exact labels supplied in the context, such as Memory 1 or Memory 3.\n"
        "8. Never cite UUIDs, chunk IDs, or any other identifier. Do not invent or renumber Memory labels.\n"
        "9. Clearly distinguish confirmed evidence from assumptions.\n"
        "10. If evidence is insufficient or conflicting, explicitly say so.\n"
        "11. Do not claim that a historical resolution will definitely fix the current incident.\n\n"
        "Use this report structure:\n"
        "A. Current Incident\n"
        "B. Relevant Historical Evidence\n"
        "C. Root Cause Analysis\n"
        "D. Recommended Next Steps\n"
    )

    try:
        analysis = client.reflect(
            bank_id=config.bank_id,
            query=reflect_query,
            budget="low",
            context=memory_context,
        )
    except Exception as exc:
        raise translate_error(exc) from exc

    analysis_text = _validated_analysis_text(analysis)
    cited_ids = extract_cited_ids(analysis_text)

    has_evidence = bool(exact_matches or related_patterns or resolution_evidence)
    empty = not unique_results

    return InvestigationResult(
        memories=memories,
        unique_results=unique_results,
        duplicates_removed=duplicates_removed,
        exact_matches=exact_matches,
        related_patterns=related_patterns,
        resolution_evidence=resolution_evidence,
        analysis_text=analysis_text,
        cited_ids=cited_ids,
        empty=empty,
        has_evidence=has_evidence,
    )
