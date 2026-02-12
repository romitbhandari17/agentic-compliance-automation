"""
Trigger script to start the contract review Step Functions state machine.

Usage examples:
  # using env vars
  export STATE_MACHINE_ARN="arn:aws:states:us-east-1:123456789012:stateMachine:agentic-compliance-automation-dev-state-machine"
  python3 src/scripts/trigger_step_function.py --bucket agentic-compliance-automation-dev-s3-artifacts --key contracts/contract.pdf

  # passing state machine arn on the CLI and waiting for completion (max 300s)
  python3 src/scripts/trigger_step_function.py --state-machine-arn $ARN --wait --timeout 300

Notes:
- This script will call AWS Step Functions StartExecution and requires AWS credentials in the environment.
- REGION is taken from AWS_REGION or AWS_DEFAULT_REGION env var; defaults to us-east-1.
"""

import os
import sys
import json
import time
import uuid
import argparse
import logging
import boto3
from datetime import datetime, timezone

logger = logging.getLogger("trigger_step_function")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(handler)

DEFAULT_REGION = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"


def build_event(contract_id: str, bucket: str, key: str) -> dict:
    logger.info("build_event: building Step Functions input event")
    print("build_event: building Step Functions input event")

    if contract_id == "":
        # allow empty contract_id so ingestion lambda can generate one
        contract_id = ""

    s3 = {"bucket": bucket, "key": key}
    s3_uri = f"s3://{bucket}/{key}"

    event = {
        "contract_id": contract_id,
        "s3": s3,
        "s3_uri": s3_uri
    }

    logger.info(f"build_event: event ready for contract_id={contract_id} s3_uri={s3_uri}")
    print(f"build_event: event ready for contract_id={contract_id} s3_uri={s3_uri}")
    return event


def start_execution(stepfunctions_client, state_machine_arn: str, event: dict, name_prefix: str = "trigger") -> str:
    execution_name = f"{name_prefix}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{str(uuid.uuid4())[:8]}"
    logger.info(f"start_execution: starting execution {execution_name} for state machine {state_machine_arn}")
    print(f"start_execution: starting execution {execution_name} for state machine {state_machine_arn}")

    try:
        resp = stepfunctions_client.start_execution(
            stateMachineArn=state_machine_arn,
            name=execution_name,
            input=json.dumps(event)
        )
        execution_arn = resp.get("executionArn")
        logger.info(f"start_execution: started executionArn={execution_arn}")
        print(f"start_execution: started executionArn={execution_arn}")
        return execution_arn
    except Exception as e:
        logger.exception("start_execution: failed to start execution")
        print(f"start_execution: failed to start execution: {e}")
        raise


def wait_for_completion(stepfunctions_client, execution_arn: str, timeout_seconds: int = 300, poll_interval: int = 3) -> dict:
    logger.info(f"wait_for_completion: waiting for execution {execution_arn} to complete (timeout={timeout_seconds}s)")
    print(f"wait_for_completion: waiting for execution {execution_arn} to complete (timeout={timeout_seconds}s)")

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            desc = stepfunctions_client.describe_execution(executionArn=execution_arn)
            status = desc.get("status")
            logger.info(f"wait_for_completion: status={status}")
            print(f"wait_for_completion: status={status}")

            if status in ("SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED"):
                output = desc.get("output")
                return {"status": status, "output": output, "raw": desc}

        except Exception as e:
            logger.exception("wait_for_completion: describe_execution failed")
            print(f"wait_for_completion: describe_execution failed: {e}")

        time.sleep(poll_interval)

    raise TimeoutError(f"Execution did not reach a terminal state within {timeout_seconds} seconds")


def parse_args(argv):
    p = argparse.ArgumentParser(description="Trigger the contract review Step Functions state machine")
    p.add_argument("--state-machine-arn", dest="state_machine_arn", help="State machine ARN (or set STATE_MACHINE_ARN env var)")
    p.add_argument("--bucket", default="agentic-compliance-automation-dev-s3-artifacts", help="S3 bucket name")
    p.add_argument("--key", default="contracts/contract.pdf", help="S3 object key")
    p.add_argument("--contract-id", default="", help="Contract ID to pass through (leave empty to let ingestion generate)")
    p.add_argument("--region", default=DEFAULT_REGION, help="AWS region to use (default from env or us-east-1)")
    p.add_argument("--wait", action="store_true", help="Wait for execution to complete and print result")
    p.add_argument("--timeout", type=int, default=30000, help="Max seconds to wait when --wait is set")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])

    state_machine_arn = "arn:aws:states:us-east-1:968239734180:stateMachine:agentic-compliance-automation-dev-state-machine" or os.environ.get("STATE_MACHINE_ARN")
    if not state_machine_arn:
        print("Error: state machine ARN must be provided via --state-machine-arn or STATE_MACHINE_ARN env var")
        sys.exit(2)

    region = args.region
    client = boto3.client("stepfunctions", region_name=region)

    event = build_event(args.contract_id, args.bucket, args.key)

    try:
        execution_arn = start_execution(client, state_machine_arn, event)
    except Exception as e:
        print(f"Failed to start execution: {e}")
        sys.exit(1)

    if args.wait:
        try:
            result = wait_for_completion(client, execution_arn, timeout_seconds=args.timeout)
            print("Execution finished:")
            print(json.dumps(result, indent=2))
        except Exception as e:
            print(f"Error while waiting for execution: {e}")
            sys.exit(1)
    else:
        print(f"Started execution: {execution_arn}")


if __name__ == "__main__":
    main()

