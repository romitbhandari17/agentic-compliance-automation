"""
Simple local trigger for the ingestion lambda handler.
Assumption: the user intended the S3 field to be named "bucket" (not the malformed key shown earlier).

Usage: run this file from the `agents/ingestion` folder (so local imports work) with Python 3.x.
This will call `handler(event, None)` and print the returned payload or any raised exception.
"""

import json

# Import the handler from the sibling module
from main import handler


def make_event() -> dict:
    return {
        "contract_id": "",
        "s3": {
            # assumed key name is 'bucket'
            "bucket": "agentic-compliance-automation-dev-s3-artifacts",
            "key": "contracts/contract.pdf",
        },
    }


def main():
    event = make_event()
    print("Invoking ingestion.handler with event:")
    print(json.dumps(event, indent=2))

    try:
        result = handler(event, None)
        print("\nHandler result:")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print("\nHandler raised an exception:")
        print(repr(e))


if __name__ == "__main__":
    main()

