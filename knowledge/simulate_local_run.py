"""Local simulator for the Knowledge POC pipeline without AWS dependencies.

Runs an end-to-end flow:
- create sample text
- chunk, embed (sentence-transformers if available else deterministic random vectors)
- write JSONL to local staging dir
- build Annoy index from staging files
- run a retrieval query against the built index

This is useful to validate the pipeline locally without S3/SQS.
"""
import os
import sys
import json
import uuid
import random
from typing import List

# ensure project root is on sys.path so `knowledge` package imports work when running this script directly
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from knowledge.embedding.embed import chunk_text
from knowledge.indexing.index_builder import build_annoy_index

BASE = os.path.dirname(__file__)
LOCAL_STAGING = os.path.join(BASE, 'local_staging')
LOCAL_INDEXES = os.path.join(BASE, 'local_indexes')


def deterministic_vector(seed: int, dim: int = 384):
    random.seed(seed)
    return [random.random() for _ in range(dim)]


from knowledge.embedding.embed import embed_texts, get_model, HAS_ST
USE_MODEL = HAS_ST


def stage_vectors_locally(tenant_id: str, doc_id: str, text: str):
    chunks = chunk_text(text, chunk_size=100, overlap=20)
    if USE_MODEL:
        embs = embed_texts(chunks)
    else:
        embs = [deterministic_vector(i, dim=384) for i in range(len(chunks))]

    os.makedirs(os.path.join(LOCAL_STAGING, tenant_id), exist_ok=True)
    fname = os.path.join(LOCAL_STAGING, tenant_id, f'{tenant_id}_{doc_id}_{uuid.uuid4().hex}.jsonl')
    with open(fname, 'w', encoding='utf-8') as f:
        for idx, (chunk, emb) in enumerate(zip(chunks, embs)):
            rec = {
                'id': f'{doc_id}_{idx}',
                'tenant_id': tenant_id,
                'doc_id': doc_id,
                'chunk_index': idx,
                'text': chunk,
                'vector': emb if isinstance(emb, list) else emb.tolist(),
            }
            f.write(json.dumps(rec) + '\n')
    print('staged', fname)
    return fname


def build_local_index(tenant_id: str):
    # collect staging files
    pref = os.path.join(LOCAL_STAGING, tenant_id)
    files = [os.path.join(pref, f) for f in os.listdir(pref) if f.endswith('.jsonl')]
    vecs = []
    meta = {}
    idx = 0
    for fpath in files:
        with open(fpath, 'r', encoding='utf-8') as f:
            for line in f:
                rec = json.loads(line)
                vecs.append(rec['vector'])
                meta[idx] = {'id': rec['id'], 'doc_id': rec['doc_id'], 'chunk_index': rec['chunk_index'], 'text': rec['text'][:1000]}
                idx += 1
    dim = len(vecs[0])
    t = build_annoy_index(vecs, dim, n_trees=10)
    os.makedirs(os.path.join(LOCAL_INDEXES, tenant_id), exist_ok=True)
    ann_path = os.path.join(LOCAL_INDEXES, tenant_id, f'{tenant_id}.ann')
    meta_path = os.path.join(LOCAL_INDEXES, tenant_id, f'{tenant_id}.meta.json')
    t.save(ann_path)
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f)
    print('local index saved', ann_path, meta_path)
    return ann_path, meta_path


def retrieve_local(tenant_id: str, query: str, k: int = 3):
    # embed query
    if USE_MODEL:
        model = get_model()
        q_emb = model.encode([query])[0]
    else:
        q_emb = deterministic_vector(999, dim=384)

    # load index: prefer Annoy if available, otherwise load fallback json vectors produced by the brute-force saver
    meta_path = os.path.join(LOCAL_INDEXES, tenant_id, f'{tenant_id}.meta.json')
    with open(meta_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)

    try:
        from annoy import AnnoyIndex
        # determine dim: prefer embedding model dimension if available
        if USE_MODEL:
            try:
                model = get_model()
                dim = model.get_sentence_embedding_dimension()
            except Exception:
                dim = 384
        else:
            dim = 384
        ann = AnnoyIndex(dim, 'angular')
        ann.load(os.path.join(LOCAL_INDEXES, tenant_id, f'{tenant_id}.ann'))
        ids, dists = ann.get_nns_by_vector(q_emb, k, include_distances=True)
    except Exception:
        # fallback: load saved json vectors from the index save step
        ann_json = os.path.join(LOCAL_INDEXES, tenant_id, f'{tenant_id}.ann.json')
        with open(ann_json, 'r', encoding='utf-8') as f:
            vectors = json.load(f)
        # brute force search
        def dot(a, b):
            return sum(x * y for x, y in zip(a, b))

        def norm(a):
            return sum(x * x for x in a) ** 0.5

        scores = []
        for i, v in enumerate(vectors):
            denom = norm(q_emb) * norm(v)
            sim = dot(q_emb, v) / denom if denom != 0 else 0.0
            scores.append((i, 1.0 - sim))
        scores.sort(key=lambda x: x[1])
        ids = [i for i, _ in scores[:k]]
        dists = [d for _, d in scores[:k]]
    results = []
    for i, d in zip(ids, dists):
        m = meta.get(str(i)) or meta.get(i)
        results.append({'id': m.get('id'), 'score': float(d), 'metadata': m})
    return results


def main():
    tenant = 'tenant-a'
    doc = 'contract1'
    sample_text = 'This contract covers data protection, GDPR compliance, liability limits, indemnification, and termination clauses. The vendor will implement security measures and notify the customer within 72 hours of any incident.'
    stage_vectors_locally(tenant, doc, sample_text)
    build_local_index(tenant)
    res = retrieve_local(tenant, 'data protection and notification requirements', k=3)
    print('retrieve results:')
    for r in res:
        print(r)


if __name__ == '__main__':
    main()

