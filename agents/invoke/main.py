"""
Lambda to be triggered by S3 Put events. It extracts S3 bucket/key and
starts the Step Functions state machine with an ingestion-style input object.

Expected S3 event records (standard S3 Put event schema). The handler constructs the input:
{
    "contract_id": "",  # empty: ingestion will generate UUID
    "s3": {"bucket": "...", "key": "..."},
    "s3_uri": "s3://.../..."
}

This implementation is intentionally minimal and includes print/logger statements
in each helper for observability.
"""
import os
import json
import logging
import uuid
from urllib.parse import unquote_plus
from datetime import datetime, timezone

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Use AWS_REGION env var if present; otherwise default to us-east-1
REGION = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"
# State machine ARN must be supplied via environment variable at runtime
STATE_MACHINE_ARN = os.environ.get("STATE_MACHINE_ARN") or "arn:aws:states:us-east-1:968239734180:stateMachine:agentic-compliance-automation-dev-state-machine"

sfn = boto3.client("stepfunctions", region_name=REGION)


def _build_event_from_s3_record(record: dict) -> dict:
    msg = "_build_event_from_s3_record: building event from S3 record"
    print(msg)
    logger.info(msg)

    s3 = record.get("s3", {})
    bucket = s3.get("bucket", {}).get("name")
    key = s3.get("object", {}).get("key")

    if bucket and key:
        key = unquote_plus(key)

    input_event = {
        "contract_id": "",
        "s3": {"bucket": bucket, "key": key},
        "s3_uri": f"s3://{bucket}/{key}"
    }

    logger.info(f"_build_event_from_s3_record: built event for s3://{bucket}/{key}")
    print(f"_build_event_from_s3_record: built event for s3://{bucket}/{key}")
    return input_event


def _start_state_machine(input_obj: dict) -> dict:
    msg = "_start_state_machine: starting state machine execution"
    print(msg)
    logger.info(msg)

    if not STATE_MACHINE_ARN:
        err = "STATE_MACHINE_ARN environment variable is not set"
        logger.error(f"_start_state_machine: {err}")
        print(f"_start_state_machine: {err}")
        return {"error": err}

    # Create a unique execution name
    exec_name = f"invoke-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{str(uuid.uuid4())[:8]}"

    try:
        resp = sfn.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            name=exec_name,
            input=json.dumps(input_obj)
        )
        exec_arn = resp.get("executionArn")
        logger.info(f"_start_state_machine: started executionArn={exec_arn}")
        print(f"_start_state_machine: started executionArn={exec_arn}")
        return {"status": "started", "executionArn": exec_arn}

    except Exception as e:
        logger.exception("_start_state_machine: failed to start execution")
        print(f"_start_state_machine: failed to start execution: {e}")
        return {"status": "error", "error": str(e)}


def handler(event, context):
    """Lambda handler triggered by S3 Put events. Starts Step Functions executions and returns results."""
    print("handler: invoked")
    logger.info("handler: invoked")
    logger.debug(json.dumps(event))

    records = event.get("Records") or []
    results = []

    for rec in records:
        try:
            input_obj = _build_event_from_s3_record(rec)
            start_resp = _start_state_machine(input_obj)
            results.append({"input": input_obj, "start_response": start_resp})
        except Exception as e:
            logger.exception("handler: unexpected error processing record")
            results.append({"status": "error", "error": str(e)})

    print("handler: completed")
    logger.info("handler: completed")
    return {"results": results}
