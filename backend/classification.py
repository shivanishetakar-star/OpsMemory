"""Rule-based classification of retrieved historical incident memories."""

import re


def classify_memories(memories, service, error, deployment):
    """Classify memories into exact matches, related patterns, and resolution evidence.

    Returns three lists of ``(index, memory)`` tuples, where ``index`` is the
    position of ``memory`` in ``memories`` starting at ``1``.
    """
    exact_matches = []
    related_patterns = []
    resolution_evidence = []

    service_key = service.casefold()
    error_key = re.sub(r"\s+", "", error.casefold())
    deployment_key = deployment.casefold()

    for index, memory in enumerate(memories, start=1):
        text = memory.text.casefold()
        primary_text = text.split("(earlier:", 1)[0]

        has_service = service_key in primary_text

        errors = {
            re.sub(r"\s+", "", item.casefold())
            for item in re.findall(r"HTTP\s*\d{3}", primary_text, re.IGNORECASE)
        }

        deployments = {
            item.casefold()
            for item in re.findall(
                r"\bv\d+(?:\.\d+)*\b",
                primary_text
            )
        }

        is_exact = (
            has_service
            and error_key in errors
            and deployment_key in deployments
        )

        if is_exact:
            exact_matches.append((index, memory))

        elif has_service and (
            any(item != error_key for item in errors)
            or any(item != deployment_key for item in deployments)
        ):
            related_patterns.append((index, memory))

        resolution_words = (
            "resolved",
            "resolution",
            "fixed",
            "restarted",
            "reducing",
            "reduced",
        )

        if service_key in text and any(
            word in text for word in resolution_words
        ):
            resolution_evidence.append((index, memory))

    return exact_matches, related_patterns, resolution_evidence
