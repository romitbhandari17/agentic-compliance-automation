"""Embedding utilities for the Knowledge POC.

Functions:
- embed_and_stage(text, tenant_id, doc_id, bucket, staging_prefix)

This implementation uses `sentence-transformers` locally. Replace embedding call with Bedrock or other provider as needed.
"""
import json
import os
import uuid
from typing import List

import boto3

s3 = boto3.client("s3")

# choose model here; replace with Bedrock or other when needed
EMBED_MODEL_NAME = os.environ.get("EMBED_MODEL_NAME", "all-MiniLM-L6-v2")
_model = None

# sentence-transformers optional import
try:
    from sentence_transformers import SentenceTransformer
    HAS_ST = True
except Exception:
    SentenceTransformer = None
    HAS_ST = False


def get_model():
    """Lazily load and return the sentence-transformers model. Raises RuntimeError if not available."""
    global _model
    if not HAS_ST:
        raise RuntimeError('sentence-transformers not available')
    if _model is None:
        _model = SentenceTransformer(EMBED_MODEL_NAME)
    return _model


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = words[i : i + chunk_size]
        chunks.append(" ".join(chunk))
        i += chunk_size - overlap
    return chunks


def embed_texts(texts: List[str]):
    """Return embeddings for a list of texts using sentence-transformers.

    Raises RuntimeError if the local model is not available.
    """
    model = get_model()
    embeddings = model.encode(texts, show_progress_bar=False)
    return embeddings


def embed_and_stage(text: str, tenant_id: str, doc_id: str, bucket: str, staging_prefix: str = "staging/vectors/"):
    import hashlib

    chunks = chunk_text(text, chunk_size=500, overlap=100)
    embeddings = embed_texts(chunks)
    # provenance
    file_uuid = uuid.uuid4().hex
    doc_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    # prepare newline jsonl
    records = []
    for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        import hashlib as _hashlib
        chunk_hash = _hashlib.sha256(chunk.encode("utf-8")).hexdigest()
        rec = {
            "staged_file_uuid": file_uuid,
            "doc_hash": doc_hash,
            "id": f"{doc_id}_{file_uuid}_{idx}",
            "tenant_id": tenant_id,
            "doc_id": doc_id,
            "chunk_index": idx,
            "chunk_hash": chunk_hash,
            "text": chunk,
            "vector": emb.tolist() if hasattr(emb, "tolist") else list(emb),
        }
        records.append(rec)

    # write to /tmp and upload to s3
    fname = f"/tmp/{tenant_id}_{doc_id}_{uuid.uuid4().hex}.jsonl"
    os.makedirs(os.path.dirname(fname), exist_ok=True)
    with open(fname, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    key = os.path.join(staging_prefix.strip("/"), tenant_id, os.path.basename(fname))
    s3.upload_file(fname, bucket, key)
    print(f"staged {len(records)} vectors to s3://{bucket}/{key}")
    return key

