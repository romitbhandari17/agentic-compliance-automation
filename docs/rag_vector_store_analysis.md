# RAG & Vector-store Analysis — agentic-compliance-automation

## Summary

This document provides a concise analysis and recommendations for adding a Retrieval-Augmented Generation (RAG) layer to the agentic-compliance-automation project. It compares vector-store options (OpenSearch Service k-NN vs Aurora PostgreSQL with pgvector), lists low-cost approaches for a POC, estimates cost ranges, and describes a recommended least-cost POC architecture using disk-backed ANN (Annoy/FAISS) for tenant knowledge bases stored in S3.

## Checklist — what this document contains

- Short summary and purpose
- RAG building blocks and where they map into the repo flow
- Key cost drivers for vector stores and embeddings
- Detailed comparison: OpenSearch Service (k-NN) vs Aurora PostgreSQL + pgvector
- Low-cost POC options and tradeoffs
- Recommended least-cost POC architecture (Annoy/FAISS on EC2) with chunking and indexing guidance
- Rough monthly cost ranges (dev, medium, large) — illustrative
- Migration triggers (when to move to OpenSearch or managed vector DB)
- Implementation plan and next steps (concrete artifacts)
- Appendix: raw vector storage calculation and example

---

## 1. RAG building blocks — where they fit in the existing flow

High-level building blocks:

- Document store (raw documents): S3 (already used in the repo)
- Ingestion & chunking: ingestion Lambda / worker (chunks → metadata)
- Embedding generation: Bedrock or chosen embedding service called from ingestion or a dedicated worker
- Vector index / vector store: Annoy / FAISS / OpenSearch / Aurora / managed vector DB
- Retrieval service / API: query → embed → ANN search → top-K results + metadata
- Reranker / LM prompt layer: LLM prompt assembly using retrieved contexts (used by compliance/risk/decision agents)
- Orchestration: Lambda & Step Functions (existing `step_functions/contract_review.asl.json`)

How these map to the repo flow:

- S3 → S3 PUT event → trigger/invoke Lambda → Step Functions orchestration
- Ingestion: extract → chunk → embed → stage vectors (S3/DynamoDB/SQS)
- Index builder: periodic/triggered process builds ANN indices (Annoy/FAISS) or writes to OpenSearch/Aurora
- Retrieval: runtime Lambdas call retrieval service or library to fetch context for Bedrock LLM calls

## 2. Key cost drivers (vector store + embeddings)

- Embedding API cost (per-token or per-call) — usually the largest recurring cost
- Vector storage: raw vector bytes (D * 4 bytes), metadata, and index overhead (2–5x depending on index type)
- Compute for search: CPU/RAM for nearest-neighbor search, index builds
- Storage I/O and EBS/EFS/Governed managed storage costs
- Managed node-hours (OpenSearch, Aurora, managed vector DBs)
- Network / data transfer and snapshot/backup storage

---

## 3. Detailed comparison — OpenSearch Service (k-NN) vs Aurora PostgreSQL + pgvector

### OpenSearch Service (k-NN)

- Cost characteristics: node-based pricing (data nodes + EBS) and snapshot costs. Costs increase with higher-memory instance classes.
- Performance: purpose-built for search; supports approximate k-NN (HNSW) and hybrid vector+text queries; low-latency retrieval for tuned clusters.
- Scaling: horizontal via adding data nodes and shards; suitable for multi-GB/TB vector datasets.
- Pros: mature search features, hybrid queries, snapshots to S3, integrated monitoring.
- Cons: JVM tuning, heavier ops or higher managed cost for small deployments.

### Aurora PostgreSQL + pgvector

- Cost characteristics: instance-hours + storage; storage auto-scales but I/O can add cost.
- Performance: good for small-to-medium vector sets; may require large instances for high QPS or millions of vectors.
- Scaling: vertical scaling and read replicas; partitioning requires manual sharding for large scale.
- Pros: SQL + join capabilities, transactional semantics, familiar tooling.
- Cons: not purpose-built for ANN; may need significant tuning at scale.

### Recommendation from comparison

- For small-to-medium datasets with tight SQL needs → Aurora + pgvector.
- For large datasets, high QPS, or hybrid text+vector queries → OpenSearch Service (k-NN) or managed vector DB.

---

## 4. Low-cost POC options (tradeoffs)

- Annoy/FAISS on a single small EC2: cheapest; simple; single-node; best for <100k vectors.
- Lambda + EFS: serverless-ish; watch cold starts and EFS costs.
- Small OpenSearch cluster: realistic, supports hybrid queries, higher monthly cost than single EC2.
- Aurora + pgvector: good if you need SQL tight coupling; moderate cost for small datasets.
- Managed vector DBs (Pinecone/Weaviate): higher cost but minimal ops and good performance.

---

## 5. Recommended least-cost approach for tenant KB RAG (POC)

Recommendation: build a POC with Annoy or FAISS on a small EC2 instance (or small fleet). Key points:

- Per-tenant index files for small tenants (simpler security & isolation).
- Ingestion Lambda writes newline-delimited JSON (.jsonl) with {id, tenant_id, vector, metadata} to S3 (or pushes events to SQS).
- Index builder (EC2) consumes staged vectors, builds Annoy/FAISS index files and uploads them to S3; use atomic swap of index files for zero-downtime replacement.
- Retrieval API (small FastAPI/Flask) runs on EC2; loads index into memory (or memory-maps Annoy) and serves /retrieve.

Chunking guidance:
- Chunk size: aim for 400–800 tokens.
- Overlap: 10–25% (20% recommended).
- Store metadata: tenant_id, doc_id, chunk_offset, snippet_link.

Index rebuild strategy:
- Incremental staging → periodic rebuild when threshold reached (e.g., 10k vectors) or time-based (nightly).
- Atomic swap of index file on successful build.

Multi-tenant approach:
- Per-tenant indices for small tenants; sharded/grouped indices for medium tenants; dedicated resources for large tenants.

Retrieval API contract (example):

POST /retrieve
```json
{ "tenant_id": "acme", "query": "force majeure implications", "k": 10 }
```

Response: top-k matches with {id, score, metadata, snippet}

---

## 6. Rough monthly cost ranges (illustrative)

- Annoy/FAISS on EC2:
  - Dev: $20–120 / month
  - Medium: $100–500 / month
  - Large: $400–2,000 / month
- Lambda + EFS: Dev $30–150; Medium $200–800; Large $800–4,000+
- OpenSearch Service: Dev $200–800; Medium $1,000–5,000; Large $5,000–25,000+
- Aurora + pgvector: Dev $50–300; Medium $300–1,200; Large $1,200–10,000+
- Managed vector DBs: Dev $50–300; Medium $300–2,000; Large $2,000–15,000+

Note: excludes embedding/model inference costs (Bedrock) which can dominate depending on volume.

---

## 7. Migration triggers — when to move off the cheapest option

- Dataset approaches millions of vectors (e.g., >2–5M)
- Need sub-50ms tail latency at scale or sustained high QPS (>100 RPS)
- Multi-tenant filtering and flexible metadata queries become complex
- Need cross-region/HA, SLAs, or enterprise features

---

## 8. Implementation plan & next steps (concrete artifacts)

Phase A — POC (Annoy/FAISS on EC2)

1. Ingestion code
   - Update `agents/ingestion/main.py`: chunk → embed → stage vectors to S3 (.jsonl)
2. Index builder
   - `tools/index_builder.py` on EC2: consumes staged vectors and builds index files
3. Retrieval API
   - `services/retriever.py` (FastAPI) that loads index and serves search
4. Terraform snippets
   - Minimal EC2 + EBS + S3 + IAM + SQS
5. Tests
   - Unit tests for chunking, index build, and retrieval

Phase B — Hardening & Migration-ready

- Add metrics, backups, shard/partition strategies, snapshots to S3
- Create Terraform modules for OpenSearch and Aurora for migration
- Run load tests; tune index types and instance sizes

Concrete deliverables I can produce next (pick from):
- Terraform snippet for POC EC2 + S3 + IAM
- Python skeletons: ingestion, index_builder, retriever (FastAPI)
- Cost calculator script (parametric) to estimate OpenSearch vs Aurora costs

---

## 9. Inputs required for a precise cost estimate

- Expected total vectors (N) and embedding dimension (D)
- Expected QPS / concurrency and latency targets
- Ingest rate (docs/day) and update frequency
- Desired HA / replica policy and retention/backups
- Preferred AWS region

---

## 10. Appendix — raw vector storage calculation (formula + example)

Formula:

- Raw vector bytes per vector = dimension * 4 (float32)
- Raw vector storage (GB) = vectors * (dimension * 4) / (1024^3)
- Add metadata per vector (estimate 100–400 bytes)
- Index overhead multiplier (m) depending on index type (2–5x typical)

Worked example:

- dimension = 1536, vectors = 1,000,000
- raw vector bytes per vector = 1536 * 4 = 6,144 bytes (~6.0 KB)
- raw vector storage = ~5.72 GiB
- metadata (200 bytes/vector) = ~0.19 GiB
- index overhead (assume +20%) ≈ 1.14 GiB
- total ≈ 7.05 GiB

---

## Quick operational tips

- Keep consistent embedding model/version and record it with each vector
- Chunk conservatively (400–800 tokens) and store minimal metadata
- Use atomic index swaps for zero-downtime updates
- Cache hot queries and avoid re-embedding identical content

---

If you want, I can now:

- create the POC Terraform and FastAPI skeleton described above, or
- produce a parametric cost calculator for your expected vectors/QPS, or
- create the ingestion/index-builder/retriever Python artifacts.

Select which artifact you want next.

