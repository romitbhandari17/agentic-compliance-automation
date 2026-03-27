#!/usr/bin/env python3
"""
Simple S3 event processor for the Knowledge POC.
Usage (local):
python knowledge/process_s3_event.py --bucket my-bucket --key tenant-a/contracts/contract1.txt

This script downloads the object, expects plain text content (for now), chunks it, and calls the embedding module to create vectors.
"""
import argparse
import os
import boto3
import uuid
from knowledge.embedding.embed import embed_and_stage

s3 = boto3.client("s3")


def download_to_tmp(bucket, key):
    basename = os.path.basename(key)
    tmp_path = f"/tmp/{uuid.uuid4().hex}_{basename}"
    os.makedirs(os.path.dirname(tmp_path), exist_ok=True)
    s3.download_file(bucket, key, tmp_path)
    return tmp_path


def parse_tenant_from_key(key):
    # expect key like tenant-id/... or tenant-id
    parts = key.split("/")
    if parts:
        return parts[0]
    return "default"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--key", required=True)
    args = parser.parse_args()

    tmp_file = download_to_tmp(args.bucket, args.key)
    with open(tmp_file, "r", encoding="utf-8") as f:
        text = f.read()

    tenant_id = parse_tenant_from_key(args.key)
    # simple metadata
    doc_id = os.path.splitext(os.path.basename(args.key))[0]

    # call embedding pipeline
    embed_and_stage(
        text=text,
        tenant_id=tenant_id,
        doc_id=doc_id,
        bucket=args.bucket,
        staging_prefix="staging/vectors/",
    )


if __name__ == "__main__":
    main()

