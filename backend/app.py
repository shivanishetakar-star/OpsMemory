from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from hindsight_client import Hindsight

from error_handling import (
    ConfigurationError,
    InvestigationError,
    load_config,
    translate_error,
)
from investigation import run_investigation


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

    try:
        config = load_config()
    except ConfigurationError as exc:
        st.error(exc.user_message)
    else:

        client = None

        try:
            client = Hindsight(
                base_url=config.base_url,
                api_key=config.api_key
            )

            with st.spinner("Investigating incident..."):
                result = run_investigation(
                    client, config, service, error, deployment,
                )

            if result.empty:
                st.warning(
                    "No relevant historical memories were found. "
                    "The investigation report is based on no historical evidence."
                )
            elif not result.has_evidence:
                st.warning(
                    "Historical memories were retrieved, but none match the "
                    "current incident details. The report is based on no "
                    "matching evidence."
                )

            st.subheader("🤖 AI Investigation Report")
            st.write(result.analysis_text)

            st.subheader("🔎 Evidence Tracker")

            if result.cited_ids:
                for memory_id in result.cited_ids:
                    if 1 <= memory_id <= len(result.unique_results):
                        memory = result.unique_results[memory_id - 1]

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

            if result.memories:
                st.success(
                    f"Retrieved {len(result.memories)} relevant memories."
                )

                for index, memory in enumerate(result.memories, start=1):
                    with st.expander(f"Memory {index}"):
                        st.write(memory.text)
            else:
                st.warning(
                    "No relevant historical memories found."
                )

        except InvestigationError as exc:
            st.error(exc.user_message)

        except Exception as exc:
            # Final safety net at the UI boundary. Never render raw
            # exception details, which can contain response bodies or tokens.
            st.error(translate_error(exc).user_message)

        finally:
            if client is not None:
                try:
                    client.close()
                except Exception:
                    pass
