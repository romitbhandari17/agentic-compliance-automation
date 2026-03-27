"""Lambda-style handler for S3 object-created events.

Behavior:
- Parse S3 event to find bucket and key
- If key matches pattern {tenant_id}/kb/... then download, extract text (expects plain text for POC), call embedding.embed_and_stage
- Push a message to SQS (index-queue) with tenant_id so the indexer worker can rebuild

This file can be used as the Lambda handler (set handler to knowledge.invoke_s3_handler.handler)
"""
import json
import os
import re
import boto3
from knowledge.embedding.embed import embed_and_stage

SQS_QUEUE_URL = os.environ.get('INDEX_QUEUE_URL')
STAGING_PREFIX = os.environ.get('STAGING_PREFIX', 'staging/vectors/')

s3 = boto3.client('s3')
sqs = boto3.client('sqs')


def parse_tenant_from_key(key: str):
    # assume key like tenant-id/kb/...
    m = re.match(r'^([^/]+)/kb/(.+)$', key)
    if m:
        return m.group(1), m.group(2)
    return None, None


def handler(event, context=None):
    # AWS S3 event structure may contain multiple records
    for rec in event.get('Records', []):
        s3info = rec.get('s3', {})
        bucket = s3info.get('bucket', {}).get('name')
        key = s3info.get('object', {}).get('key')
        tenant_id, relpath = parse_tenant_from_key(key)
        if not tenant_id:
            print('s3 key not under tenant kb, skipping', key)
            continue

        # download and assume plain text for POC
        tmpfile = f'/tmp/{os.path.basename(key)}'
        s3.download_file(bucket, key, tmpfile)
        with open(tmpfile, 'r', encoding='utf-8') as f:
            text = f.read()

        doc_id = os.path.splitext(os.path.basename(key))[0]
        # call embedding
        staging_key = embed_and_stage(text=text, tenant_id=tenant_id, doc_id=doc_id, bucket=bucket, staging_prefix=STAGING_PREFIX)
        print('staged to', staging_key)

        # notify indexer via SQS
        if SQS_QUEUE_URL:
            msg = {'tenant_id': tenant_id}
            sqs.send_message(QueueUrl=SQS_QUEUE_URL, MessageBody=json.dumps(msg))
            print('sent sqs message for tenant', tenant_id)
        else:
            print('INDEX_QUEUE_URL not set; skipping SQS notify')


