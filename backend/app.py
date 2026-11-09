import re
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from hindsight_client import Hindsight


def classify_memories(memories, service, error, deployment):
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
            for item in re.findall(r"HTTP\s*\d{3}", primary_text)
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




# Load environment variables
load_dotenv(Path(__file__).with_name(".env"))

st.set_page_config(
    page_title="OpsMemory",
    page_icon="🧠",
    layout="centered"
)

st.title("🧠 OpsMemory")
st.subheader("AI Incident Response Agent")

st.write(
    "Investigate production incidents "
    "using historical organizational memory."
)

st.divider()

# Incident inputs
service = st.text_input("Service", "Payment API")
error = st.text_input("Error", "HTTP 502")
deployment = st.text_input("Deployment", "v2.8")


if st.button("🔍 Investigate Incident", use_container_width=True):

    api_key = os.getenv("HINDSIGHT_API_KEY")
    base_url = os.getenv("HINDSIGHT_BASE_URL")
    bank_id = os.getenv("HINDSIGHT_BANK_ID")

    if not all([api_key, base_url, bank_id]):
        st.error("Missing Hindsight configuration in .env")

    else:

        client = None

        try:
            client = Hindsight(
                base_url=base_url,
                api_key=api_key
            )

            query = (
                f"Find historical production incidents involving "
                f"{service}, {error}, deployment {deployment}. "
                f"Retrieve their root causes and resolutions."
            )

            with st.spinner("Searching historical incident memories..."):

                result = client.recall(
                    bank_id=bank_id,
                    query=query
                )

            # Remove exact duplicate memories
            unique_results = []
            seen_memories = set()

            for memory in result.results:
                normalized_text = " ".join(
                    memory.text.split()
                ).casefold()

                if normalized_text and normalized_text not in seen_memories:
                    seen_memories.add(normalized_text)
                    unique_results.append(memory)

            duplicates_removed = (
                len(result.results) - len(unique_results)
            )
            exact_matches, related_patterns, resolution_evidence = (
                classify_memories(
                    unique_results,
                    service,
                    error,
                    deployment,
                )
            )

            def format_evidence_group(title, memories):
                if not memories:
                    return f"{title}\nNo matching memories found."

                entries = "\n\n".join(
                    f"Memory {index}:\n{memory.text}"
                    for index, memory in memories
                )

                return f"{title}\n{entries}"

            memory_context = "\n\n".join([
                format_evidence_group(
                    "EXACT INCIDENT MATCHES",
                    exact_matches
                ),
                format_evidence_group(
                    "RELATED HISTORICAL PATTERNS",
                    related_patterns
                ),
                format_evidence_group(
                    "HISTORICAL RESOLUTION EVIDENCE",
                    resolution_evidence
                )
            ])

            with st.spinner("Analyzing historical incidents..."):
                analysis = client.reflect(
                    bank_id=bank_id,
                    query=(
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
                    ),
                    budget="low",
                    context=memory_context
                )

            st.subheader("🤖 AI Investigation Report")
            st.write(analysis.text)

            st.subheader("🔎 Evidence Tracker")

            cited_ids = sorted({
                int(match)
                for match in re.findall(
                    r"\bMemory\s+(\d+)\b",
                    analysis.text,
                    re.IGNORECASE
                )
            })

            if cited_ids:
                for memory_id in cited_ids:
                    if 1 <= memory_id <= len(unique_results):
                        memory = unique_results[memory_id - 1]

                        with st.expander(f"Evidence: Memory {memory_id}"):
                            st.write(memory.text)
            else:
                st.warning(
                    "No supporting memory IDs were cited in the report."
                )

            st.subheader("📋 Current Incident")

            st.write(f"**Service:** {service}")
            st.write(f"**Error:** {error}")
            st.write(f"**Deployment:** {deployment}")

            st.subheader("🧠 Historical Memory")

            if result.results:

                st.success(
                    f"Retrieved {len(result.results)} relevant memories."
                )

                for index, memory in enumerate(
                    result.results, start=1
                ):
                    with st.expander(f"Memory {index}"):
                        st.write(memory.text)

            else:
                st.warning(
                    "No relevant historical memories found."
                )

        except Exception as e:
            st.error("Hindsight investigation failed.")
            st.code(str(e))

        finally:
            if client is not None:
                client.close()
