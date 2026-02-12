"""
Local trigger for the invoke_sfn lambda handler.

Builds a sample S3 Put event and calls handler(event, None).

Usage:
  python3 agents/invoke/trigger.py --bucket my-bucket --key contracts/contract.pdf

This script will not package or deploy the lambda; it only calls the local handler function.
"""

import os
import json
import argparse
import traceback

from main import handler


def make_s3_put_event(bucket: str, key: str) -> dict:
    return {
        "Records": [
            {
                "eventVersion": "2.1",
                "eventSource": "aws:s3",
                "awsRegion": os.environ.get("AWS_REGION", "us-east-1"),
                "eventTime": "2020-09-09T12:34:56.000Z",
                "eventName": "ObjectCreated:Put",
                "s3": {
                    "bucket": {"name": bucket},
                    "object": {"key": key}
                }
            }
        ]
    }


def parse_args():
    p = argparse.ArgumentParser(description="Trigger the invoke_sfn lambda locally with a sample S3 event")
    p.add_argument("--bucket", default="agentic-compliance-automation-dev-s3-artifacts", help="S3 bucket name")
    p.add_argument("--key", default="contracts/contract.pdf", help="S3 object key")
    return p.parse_args()


def main():
    args = parse_args()

    event = make_s3_put_event(args.bucket, args.key)
    print("Invoking handler with event:\n", json.dumps(event, indent=2))

    try:
        result = handler(event, None)
        print("Handler returned:\n", json.dumps(result, indent=2))
    except Exception as e:
        print("Handler raised an exception:")
        print(repr(e))
        traceback.print_exc()


if __name__ == "__main__":
    main()

