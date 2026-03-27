"""FastAPI retrieval service for Annoy indices stored in S3.

Endpoints:
- POST /retrieve { tenant_id, query, k }

Behavior:
- Lazy-loads index and metadata for tenant from S3 into /tmp on demand
- Uses the same embedding model as `embedding/embed.py`
"""
import os
import json
import tempfile
from typing import List

import boto3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from annoy import AnnoyIndex
from knowledge.embedding.embed import get_model

s3 = boto3.client("s3")
app = FastAPI()

BUCKET = os.environ.get("INDEX_BUCKET") or "agentic-compliance-automation-dev-s3-artifacts"
INDEX_PREFIX = os.environ.get("INDEX_PREFIX") or "indexes/"

# in-memory cache of loaded indexes: tenant_id -> (AnnoyIndex, meta)
_INDEXS = {}


class RetrieveRequest(BaseModel):
    tenant_id: str
    query: str
    k: int = 5


class Hit(BaseModel):
    id: str
    score: float
    metadata: dict


class RetrieveResponse(BaseModel):
    results: List[Hit]


def load_index_for_tenant(tenant_id: str):
    if tenant_id in _INDEXS:
        return _INDEXS[tenant_id]
    # list objects under INDEX_PREFIX/tenant_id/
    prefix = os.path.join(INDEX_PREFIX.strip('/'), tenant_id) + '/'
    resp = s3.list_objects_v2(Bucket=BUCKET, Prefix=prefix)
    if 'Contents' not in resp:
        raise FileNotFoundError(f'no index found for tenant {tenant_id}')
    # pick the latest by LastModified
    objs = resp['Contents']
    objs.sort(key=lambda x: x['LastModified'], reverse=True)
    index_obj = None
    meta_obj = None
    for o in objs:
        if o['Key'].endswith('.ann'):
            index_obj = o['Key']
            break
    for o in objs:
        if o['Key'].endswith('.meta.json'):
            meta_obj = o['Key']
            break
    if index_obj is None or meta_obj is None:
        raise FileNotFoundError('index or meta missing')

    tmpdir = tempfile.mkdtemp(prefix=f'index_{tenant_id}_')
    index_local = os.path.join(tmpdir, os.path.basename(index_obj))
    meta_local = os.path.join(tmpdir, os.path.basename(meta_obj))
    s3.download_file(BUCKET, index_obj, index_local)
    s3.download_file(BUCKET, meta_obj, meta_local)

    # load meta
    with open(meta_local, 'r', encoding='utf-8') as f:
        meta = json.load(f)
    dim = len(next(iter(meta.values()))['text'].split())  # not reliable; we will load with model dim
    model = get_model()
    dim = model.get_sentence_embedding_dimension() if hasattr(model, 'get_sentence_embedding_dimension') else 384
    ann = AnnoyIndex(dim, 'angular')
    ann.load(index_local)
    _INDEXS[tenant_id] = (ann, meta)
    return _INDEXS[tenant_id]


@app.post('/retrieve', response_model=RetrieveResponse)
def retrieve(req: RetrieveRequest):
    try:
        ann, meta = load_index_for_tenant(req.tenant_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

    model = get_model()
    q_emb = model.encode([req.query])[0]
    ids, distances = ann.get_nns_by_vector(q_emb.tolist(), req.k, include_distances=True)
    results = []
    for i, d in zip(ids, distances):
        m = meta.get(str(i)) or meta.get(i)
        results.append({
            'id': m.get('id'),
            'score': float(d),
            'metadata': m,
        })
    return {'results': results}

