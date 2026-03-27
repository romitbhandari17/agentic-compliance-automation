# Knowledge Pipeline: SQS, Embeddings, and Index Storage

This document summarizes the Knowledge POC pipeline and how SQS and embedding storage are handled. It mirrors the explanation provided in the interactive session.

## End-to-end summary

- When a new document is put into S3 under the tenant KB path (pattern: `<tenant_id>/kb/...`), the S3 event is expected to invoke the handler in `knowledge/invoke_s3_handler.py`.
- The handler downloads the object, chunks/embeds the text by calling `knowledge.embedding.embed.embed_and_stage(...)`, and uploads the produced newline JSONL file(s) of vectors to S3 under a staging prefix.
- After staging, the handler sends a small SQS message containing the tenant id to notify the indexer. The SQS queue URL is configured via environment variable `INDEX_QUEUE_URL`.
- An indexer worker `knowledge/indexing/indexer_worker.py` polls that SQS queue, receives the tenant id, and calls `build_index_for_tenant(...)` in `knowledge/indexing/index_builder.py` to build an Annoy index and upload `.ann` and `.meta.json` to S3 under the indexes prefix.
- The retriever `knowledge/retrieval/retriever.py` lazy-loads the latest `.ann` and `.meta.json` for a tenant from S3 and answers queries.

## Where embeddings are stored

- Embeddings are staged as newline JSONL files uploaded to S3 under:
  - `staging_prefix/tenant_id/<generated_filename>.jsonl` (default `staging/vectors/`)
- JSONL record format (one object per chunk):

```json
{
  "id": "<doc_id>_<chunk_index>",
  "tenant_id": "<tenant_id>",
  "doc_id": "<doc_id>",
  "chunk_index": <int>,
  "text": "<chunk_text>",
  "vector": [<float>, <float>, ...]
}
```

- The index builder consumes staged JSONL files and uploads:
  - `indexes/{tenant_id}/{tenant}_{uuid}.ann`
  - `indexes/{tenant_id}/{tenant}_{uuid}.meta.json`

## How SQS is used

- Sender: `knowledge/invoke_s3_handler.handler` sends a JSON message `{"tenant_id":"<tenant>"}` to the queue URL set in `INDEX_QUEUE_URL`.
- Consumer: `knowledge/indexing/indexer_worker.py` polls the queue, receives the tenant id, calls `build_index_for_tenant(...)`, and deletes the SQS message.
- Purpose: decouple embedding/staging from index building and allow indexer to run independently and handle bursts/retries.

## Files and functions

- `knowledge/embedding/embed.py`: `embed_and_stage(text, tenant_id, doc_id, bucket, staging_prefix)`
- `knowledge/invoke_s3_handler.py`: `handler(event, context)` (S3 event handler)
- `knowledge/indexing/index_builder.py`: `build_index_for_tenant(bucket, tenant_id, ...)`
- `knowledge/indexing/indexer_worker.py`: long-running SQS poller that calls the builder
- `knowledge/retrieval/retriever.py`: FastAPI retriever that loads `.ann` and `.meta.json` and serves searches

## Local simulation

See `knowledge/simulate_local_run.py` for a self-contained local simulation that:

- creates a sample text
- chunks and embeds (uses `sentence-transformers` if installed, otherwise falls back to deterministic random vectors)
- writes staged JSONL to `knowledge/local_staging/{tenant}`
- builds an Annoy index locally and saves `*.ann` and `*.meta.json` under `knowledge/local_indexes/{tenant}`
- loads the index and runs a sample retrieval query

This simulation runs without AWS credentials and demonstrates the pipeline logic end-to-end locally.

## Notes and next steps

- For production, replace local storage with S3 upload/download, and run the SQS/Lambda components in AWS.
- Add PDF/Textract processing in `invoke_s3_handler` if documents are PDFs/scans.
- Consider dedup/debounce strategies to prevent excessive rebuilds from many S3 events.

