# Knowledge POC (Annoy/FAISS)

This folder contains a small POC for a tenant-based knowledge base backed by Annoy (approximate nearest neighbors). The pipeline is:

1. S3 document arrives in tenant-specific prefix (e.g. s3://bucket/tenant-id/...) -> S3 event
2. `process_s3_event.py` (or Lambda wrapper) downloads the document, extracts text (currently expects plain text or already-extracted text), chunks it, and calls the embedding module
3. `embedding/embed.py` creates embeddings and writes a newline JSONL file of vectors and metadata to a staging S3 prefix
4. `indexing/index_builder.py` consumes staging JSONL and builds an Annoy index per tenant and uploads the index and metadata mapping to S3
5. `retrieval/retriever.py` runs a small FastAPI service to accept queries, embed queries with the same model, query the Annoy index, and return top-k results

Notes:
- The embedding module uses `sentence-transformers` by default. If you prefer Bedrock or another embedding provider, the code is structured to allow adding that backend.
- This is a POC: simple, single-node, and intended for low-volume/low-cost development. For production or larger scale, consider OpenSearch or managed vector DBs.

Run locally

1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r knowledge/requirements.txt
```

2. Start the retriever service (loads indexes lazily):

```bash
uvicorn knowledge.retrieval.retriever:app --host 0.0.0.0 --port 8080
```

3. Use the `process_s3_event.py` to process a single S3 event (or invoke from Lambda):

```bash
python knowledge/process_s3_event.py --bucket my-bucket --key tenant-a/contracts/contract1.txt
```

This README is a starting point; adapt to your environment and add Textract or PDF parsing in the ingestion step as needed.

