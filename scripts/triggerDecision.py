import json
import os
import sys

# Ensure repo root is on sys.path when running from scripts/
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.decision.main import handler


def main() -> None:
    event = {
        "contract_id": "abc-123",
        "s3": {"bucket": "example-bucket", "key": "acme/contract.pdf"},
        "s3_uri": "s3://example-bucket/acme/contract.pdf",
        "compliance_findings": {
            "compliance_status": "Non-Compliant",
            "overall_compliance_score": 4.8,
        },
        "risk_analysis_findings": {
            "overall_risk_score": 6.2,
            "overall_confidence": 0.65,
        },
    }

    result = handler(event, None)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
