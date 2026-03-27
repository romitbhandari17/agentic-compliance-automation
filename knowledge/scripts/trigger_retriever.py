#!/usr/bin/env python3
"""Quick script to call the retriever locally for testing."""
import requests
import os

HOST = os.environ.get('RETRIEVER_HOST', 'http://localhost:8080')


def query(tenant_id, q, k=5):
    res = requests.post(f"{HOST}/retrieve", json={'tenant_id': tenant_id, 'query': q, 'k': k})
    print(res.status_code)
    print(res.text)


if __name__ == '__main__':
    query('tenant-a', 'what does the data protection clause say?', 5)

