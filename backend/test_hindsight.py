
import os
from dotenv import load_dotenv
from hindsight_client import Hindsight

load_dotenv()

api_key = os.getenv("HINDSIGHT_API_KEY")
base_url = os.getenv("HINDSIGHT_BASE_URL")
bank_id = os.getenv("HINDSIGHT_BANK_ID")

if not all([api_key, base_url, bank_id]):
    raise ValueError("Missing Hindsight configuration in .env")

client = Hindsight(
    base_url=base_url,
    api_key=api_key
)

try:
    result = client.recall(
        bank_id=bank_id,
        query="Previous production incidents involving payment API errors"
    )

    print("Hindsight connection successful!")
    print("Memory bank:", bank_id)
    print("Retrieved memories:", len(result.results))

    for memory in result.results:
        print("-", memory.text)

except Exception as error:
    print("Hindsight connection failed.")
    print(type(error).__name__, error)

finally:
    client.close()
