"""Indexer worker: polls SQS for tenant events and runs index builder.

Designed to be run as a long-running process on EC2/Fargate. For Lambda, use a short-lived invoker.
"""
import json
import os
import time
import boto3
from knowledge.indexing.index_builder import build_index_for_tenant

SQS_QUEUE_URL = os.environ.get('INDEX_QUEUE_URL')
BUCKET = os.environ.get('INDEX_BUCKET')
STAGING_PREFIX = os.environ.get('STAGING_PREFIX', 'staging/vectors/')
INDEX_PREFIX = os.environ.get('INDEX_PREFIX', 'indexes/')

sqs = boto3.client('sqs')


def poll_and_process():
    if not SQS_QUEUE_URL:
        raise RuntimeError('INDEX_QUEUE_URL not set')
    print('starting indexer worker, polling', SQS_QUEUE_URL)
    while True:
        resp = sqs.receive_message(QueueUrl=SQS_QUEUE_URL, MaxNumberOfMessages=5, WaitTimeSeconds=20)
        messages = resp.get('Messages', [])
        if not messages:
            continue
        for m in messages:
            try:
                body = json.loads(m['Body'])
                tenant_id = body.get('tenant_id')
                if not tenant_id:
                    print('no tenant_id in message', body)
                else:
                    print('building index for tenant', tenant_id)
                    try:
                        build_index_for_tenant(BUCKET, tenant_id, STAGING_PREFIX, INDEX_PREFIX)
                    except Exception as e:
                        print('error building index for', tenant_id, e)
                # delete message
                sqs.delete_message(QueueUrl=SQS_QUEUE_URL, ReceiptHandle=m['ReceiptHandle'])
            except Exception as e:
                print('failed to process message', e)
        time.sleep(1)


if __name__ == '__main__':
    poll_and_process()

