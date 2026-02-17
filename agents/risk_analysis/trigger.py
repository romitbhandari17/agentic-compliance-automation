import json
import uuid
from main import handler

# Local trigger for the risk_analysis lambda

def make_event(contract_id: str = "", bucket: str = "agentic-compliance-automation-dev-s3-artifacts", key: str = "contracts/contract.pdf") -> dict:
    if not contract_id:
        contract_id = str(uuid.uuid4())
    return {
        "contract_id": contract_id,
        "s3": {"bucket": bucket, "key": key}
    }


if __name__ == "__main__":
    event = make_event()
    result = handler(event)
    print(json.dumps(result, indent=2))

