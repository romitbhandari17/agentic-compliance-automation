#!/usr/bin/env python3
"""Helper to run index_builder locally for a tenant"""
import subprocess
import sys

bucket = 'agentic-compliance-automation-dev-s3-artifacts'
tenant = 'tenant-a'
subprocess.check_call([
    sys.executable, 'knowledge/indexing/index_builder.py', '--bucket', bucket, '--tenant-id', tenant
])

