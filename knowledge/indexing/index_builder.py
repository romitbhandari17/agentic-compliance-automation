"""Index builder for Annoy-based indices.

Usage:
python knowledge/indexing/index_builder.py --bucket my-bucket --tenant-id tenant-a --staging-prefix staging/vectors/ --index-prefix indexes/

This script downloads all jsonl vector files from the staging prefix for the tenant, builds an Annoy index, writes a metadata map (id -> metadata) and uploads the index and metadata to S3.
"""
import argparse
import json
import os
import tempfile
import uuid
from typing import Dict, List

import boto3

s3 = boto3.client("s3")

# optional Annoy import
try:
    from annoy import AnnoyIndex
    HAS_ANNOY = True
except Exception:
    AnnoyIndex = None
    HAS_ANNOY = False


def list_staging_objects(bucket: str, staging_prefix: str, tenant_id: str):
    prefix = os.path.join(staging_prefix.strip('/'), tenant_id) + '/'
    paginator = s3.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get('Contents', []):
            yield obj['Key']


def download_object(bucket: str, key: str, dest_dir: str) -> str:
    os.makedirs(dest_dir, exist_ok=True)
    local_path = os.path.join(dest_dir, os.path.basename(key))
    s3.download_file(bucket, key, local_path)
    return local_path


def build_annoy_index(vecs: List[List[float]], dim: int, n_trees: int = 10):
    """Build and return an AnnoyIndex-like object. If Annoy is not installed, return a simple brute-force index for testing.

    The returned object supports `add_item`, `build` (no-op), `save`, and `get_nns_by_vector(vector, k, include_distances=True)`.
    """
    if HAS_ANNOY:
        t = AnnoyIndex(dim, 'angular')
        for i, v in enumerate(vecs):
            t.add_item(i, v)
        t.build(n_trees)
        return t

    # fallback brute-force index
    class BruteIndex:
        def __init__(self, dim):
            self.vs = []

        def add_item(self, i, v):
            self.vs.append((i, v))

        def build(self, n_trees):
            pass

        def save(self, path):
            # save vectors as json for debug
            with open(path + '.json', 'w', encoding='utf-8') as f:
                json.dump([v for (_, v) in self.vs], f)

        def get_nns_by_vector(self, qv, k, include_distances=True):
            # compute cosine similarity
            import math

            def dot(a, b):
                return sum(x * y for x, y in zip(a, b))

            def norm(a):
                return math.sqrt(sum(x * x for x in a))

            scores = []
            for i, v in self.vs:
                denom = norm(qv) * norm(v)
                sim = dot(qv, v) / denom if denom != 0 else 0.0
                scores.append((i, 1.0 - sim))
            scores.sort(key=lambda x: x[1])
            ids = [i for i, _ in scores[:k]]
            dists = [d for _, d in scores[:k]]
            return ids, dists

    idx = BruteIndex(dim)
    for i, v in enumerate(vecs):
        idx.add_item(i, v)
    idx.build(n_trees)
    return idx


def build_index_for_tenant(bucket: str, tenant_id: str, staging_prefix: str = 'staging/vectors/', index_prefix: str = 'indexes/', n_trees: int = 10):
    """Build an Annoy index for the given tenant by consuming staged JSONL files and upload index+metadata to S3.

    Returns a tuple (index_s3_key, meta_s3_key) on success, or raises exceptions on failure.
    """
    with tempfile.TemporaryDirectory() as td:
        # download staging files
        # find staged files and select the latest staged file per doc_id (based on S3 LastModified)
        keys = list(list_staging_objects(bucket, staging_prefix, tenant_id))
        if not keys:
            raise RuntimeError('no staging files found')

        # list objects with LastModified and build mapping key -> lastmodified
        keys_info = []
        paginator = s3.get_paginator('list_objects_v2')
        prefix = os.path.join(staging_prefix.strip('/'), tenant_id) + '/'
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get('Contents', []):
                keys_info.append({'Key': obj['Key'], 'LastModified': obj.get('LastModified')})

        if not keys_info:
            raise RuntimeError('no staging files found')

        # build mapping file_key -> doc_id by reading first record of each file
        file_doc_map = {}
        for info in keys_info:
            k = info['Key']
            local = download_object(bucket, k, td)
            with open(local, 'r', encoding='utf-8') as f:
                first = f.readline()
                try:
                    rec0 = json.loads(first)
                    file_doc_map[k] = rec0.get('doc_id')
                except Exception:
                    file_doc_map[k] = None

        # choose latest file key per doc_id using LastModified
        latest_per_doc = {}
        for info in keys_info:
            k = info['Key']
            doc = file_doc_map.get(k)
            if not doc:
                continue
            lm = info.get('LastModified')
            cur = latest_per_doc.get(doc)
            if cur is None or (lm and cur[1] and lm > cur[1]):
                latest_per_doc[doc] = (k, lm)

        # include only vectors from the latest staged file per doc
        vecs = []
        metadata_map: Dict[int, Dict] = {}
        idx = 0
        included_keys = {v[0] for v in latest_per_doc.values()}
        for k in included_keys:
            local = download_object(bucket, k, td)
            with open(local, 'r', encoding='utf-8') as f:
                for line in f:
                    rec = json.loads(line)
                    vecs.append(rec['vector'])
                    metadata_map[idx] = {
                        'id': rec['id'],
                        'doc_id': rec.get('doc_id'),
                        'chunk_index': rec.get('chunk_index'),
                        'text': rec.get('text')[:1000],
                        'staged_file_uuid': rec.get('staged_file_uuid'),
                        'doc_hash': rec.get('doc_hash'),
                    }
                    idx += 1

        dim = len(vecs[0])
        print(f'building annoy index dim={dim} n_items={len(vecs)}')
        t = build_annoy_index(vecs, dim, n_trees=n_trees)

        # save index and metadata
        index_fname = os.path.join(td, f'{tenant_id}_{uuid.uuid4().hex}.ann')
        t.save(index_fname)
        meta_fname = os.path.join(td, f'{tenant_id}_{uuid.uuid4().hex}.meta.json')
        with open(meta_fname, 'w', encoding='utf-8') as f:
            json.dump(metadata_map, f)

        index_key = os.path.join(index_prefix.strip('/'), tenant_id, os.path.basename(index_fname))
        meta_key = os.path.join(index_prefix.strip('/'), tenant_id, os.path.basename(meta_fname))
        s3.upload_file(index_fname, bucket, index_key)
        s3.upload_file(meta_fname, bucket, meta_key)
        print(f'uploaded index to s3://{bucket}/{index_key}')
        print(f'uploaded metadata to s3://{bucket}/{meta_key}')
        return index_key, meta_key


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bucket', required=True)
    parser.add_argument('--tenant-id', required=True)
    parser.add_argument('--staging-prefix', default='staging/vectors/')
    parser.add_argument('--index-prefix', default='indexes/')
    parser.add_argument('--n-trees', type=int, default=10)
    args = parser.parse_args()

    try:
        build_index_for_tenant(args.bucket, args.tenant_id, args.staging_prefix, args.index_prefix, args.n_trees)
    except Exception as e:
        print('error building index:', e)


if __name__ == '__main__':
    main()

