
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from hindsight_client import Hindsight

load_dotenv()

client = Hindsight(
    base_url=os.getenv("HINDSIGHT_BASE_URL"),
    api_key=os.getenv("HINDSIGHT_API_KEY")
)

bank_id = os.getenv("HINDSIGHT_BANK_ID")

data_file = Path(__file__).parent / "incidents.json"

try:
    with open(data_file, "r") as file:
        incidents = json.load(file)

    for incident in incidents:
        content = f"""
        Incident ID: {incident['id']}
        Service: {incident['service']}
        Error: {incident['error']}
        Deployment: {incident['deployment']}
        Root Cause: {incident['root_cause']}
        Resolution: {incident['resolution']}
        """

        result = client.retain(
            bank_id=bank_id,
            content=content,
            context="Historical production incident report",
            document_id=f"incident-{incident['id']}"
        )

        print(f"Stored incident: {incident['id']}")

    print("\nAll incidents submitted to Hindsight!")

except Exception as error:
    print("Memory ingestion failed:", error)

finally:
    client.close()
