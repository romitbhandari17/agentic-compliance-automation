# File: agents/ingestion/main.py
import boto3
import time
import logging
import os
import uuid

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Use AWS_REGION environment variable if present, otherwise default to us-east-1
AWS_REGION = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"

s3 = boto3.client("s3", region_name=AWS_REGION)
textract = boto3.client("textract", region_name=AWS_REGION)


def _get_s3_object_bytes(bucket: str, key: str) -> bytes:
    resp = s3.get_object(Bucket=bucket, Key=key)
    return resp["Body"].read()


def _extract_text_from_bytes_image(image_bytes: bytes) -> str:
    resp = textract.detect_document_text(Document={"Bytes": image_bytes})
    lines = [b.get("Text", "") for b in resp.get("Blocks", []) if b.get("BlockType") == "LINE"]
    return "\n".join(lines)


def _extract_text_from_s3_pdf(bucket: str, key: str, max_wait_seconds: int = 300, poll_interval: float = 2.0) -> str:
    # Start asynchronous job (Textract requires S3 for PDF)
    start = textract.start_document_text_detection(DocumentLocation={"S3Object": {"Bucket": bucket, "Name": key}})
    job_id = start.get("JobId")
    if not job_id:
        raise RuntimeError(f"Failed to start Textract job for s3://{bucket}/{key}")

    deadline = time.time() + max_wait_seconds
    text_lines = []

    while time.time() < deadline:
        status_resp = textract.get_document_text_detection(JobId=job_id)
        status = status_resp.get("JobStatus")
        if status == "SUCCEEDED":
            # collect first page
            blocks = status_resp.get("Blocks", [])
            text_lines.extend([b.get("Text", "") for b in blocks if b.get("BlockType") == "LINE"])

            next_token = status_resp.get("NextToken")
            # fetch remaining pages if any
            while next_token:
                page = textract.get_document_text_detection(JobId=job_id, NextToken=next_token)
                blocks = page.get("Blocks", [])
                text_lines.extend([b.get("Text", "") for b in blocks if b.get("BlockType") == "LINE"])
                next_token = page.get("NextToken")

            return "\n".join(text_lines)
        elif status == "FAILED":
            raise RuntimeError(f"Textract job failed for s3://{bucket}/{key}")

        time.sleep(poll_interval)

    raise TimeoutError(f"Timed out waiting for Textract job {job_id} for s3://{bucket}/{key}")


def _extract_text_from_txt_bytes(txt_bytes: bytes) -> str:
    try:
        return txt_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return txt_bytes.decode("latin-1", errors="replace")


def handler(event, context):
    """
    Lambda handler for ingestion.
    Expected event:
      {
        "contract_id": "abc-123" (optional — will be generated if missing),
        "s3": { "bucket": "my-bucket", "key": "contracts/abc.pdf" }
      }
    Returns:
      {
        "contract_id": "...",
        "s3": { "bucket": "...", "key": "..." },
        "s3_uri": "s3://.../...",
        "extracted_text": "..."
      }
    """
    raw_contract_id = event.get("contract_id")
    # generate a UUID if contract_id is missing or empty
    contract_id = raw_contract_id if raw_contract_id else str(uuid.uuid4())

    s3_info = event.get("s3") or {}
    bucket = s3_info.get("bucket")
    key = s3_info.get("key")

    # Require S3 bucket/key; contract_id will be generated if not provided
    if not bucket or not key:
        logger.error("Missing required fields in event: s3.bucket and s3.key are required")
        raise ValueError("Missing required fields: s3.bucket and s3.key")

    _, ext = os.path.splitext(key.lower())
    ext = ext.lstrip(".")
    s3_uri = f"s3://{bucket}/{key}"

    try:
        if ext in ("png", "jpg", "jpeg", "tiff", "bmp"):
            logger.info("Extracting text from image via Textract (sync)")
            image_bytes = _get_s3_object_bytes(bucket, key)
            extracted_text = _extract_text_from_bytes_image(image_bytes)

        elif ext == "pdf":
            logger.info("Extracting text from PDF via Textract (async)")
            extracted_text = _extract_text_from_s3_pdf(bucket, key)

        elif ext in ("txt",):
            logger.info("Reading text file from S3")
            txt_bytes = _get_s3_object_bytes(bucket, key)
            extracted_text = _extract_text_from_txt_bytes(txt_bytes)

        else:
            # fallback: attempt to read raw bytes and try textract detect (works for many image-like formats)
            logger.info("Unknown extension, attempting to read and run Textract detect_document_text")
            raw_bytes = _get_s3_object_bytes(bucket, key)
            extracted_text = _extract_text_from_bytes_image(raw_bytes)
            if not extracted_text:
                raise ValueError(f"Unsupported or empty extraction for s3://{bucket}/{key}")

        return {
            "contract_id": contract_id,
            "s3": {"bucket": bucket, "key": key},
            "s3_uri": s3_uri,
            "extracted_text": extracted_text,
        }

    except Exception:
        logger.exception("Failed to extract text")
        raise
