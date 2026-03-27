#!/usr/bin/env python3
"""Extract clauses from a document (.txt or .pdf) and write clause-level JSONL into resources/sale_docs.

Usage:
python knowledge/ingest/extract_clauses.py --input path/to/contract.pdf --tenant tenant-a --doc contract1

Outputs to: resources/sale_docs/{tenant}_{doc}.jsonl

This script does NOT generate embeddings; run the embedding pipeline after creating the JSONL.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from typing import List

try:
    from PyPDF2 import PdfReader
    HAS_PDF = True
except Exception:
    PdfReader = None
    HAS_PDF = False


CLAUSE_PATTERNS = {
    "liability": re.compile(r"\bliability\b|limit of liability|limitation of liability|liability shall", re.I),
    "indemnification": re.compile(r"\bindemnif(y|ication)\b|hold harmless|indemnify", re.I),
    "confidentiality": re.compile(r"\bconfidential|non-disclosure|nda|confidentiality\b", re.I),
    "termination": re.compile(r"\btermination|terminate|expiration\b", re.I),
    "renewal": re.compile(r"\brenewal|renew|auto-renew|evergreen\b", re.I),
    "payment": re.compile(r"\bfees|payment|invoice|billing|pricing\b", re.I),
    "governing_law": re.compile(r"governing law|jurisdiction|venue", re.I),
    "intellectual_property": re.compile(r"intellectual property|ip rights|license|licensee|licensor", re.I),
    "data_protection": re.compile(r"data protection|privacy|gdpr|ccpa|hipaa|personal data|breach|security incident", re.I),
    "services": re.compile(r"\bservices?\b", re.I),
}


def extract_text_from_pdf(path: str) -> str:
    if not HAS_PDF:
        raise RuntimeError("PyPDF2 not installed; cannot extract PDF text. Install PyPDF2 or provide plain text input.")
    reader = PdfReader(path)
    pages = []
    for p in reader.pages:
        try:
            txt = p.extract_text() or ""
        except Exception:
            txt = ""
        pages.append(txt)
    return "\n\n".join(pages)


def extract_text(path: str) -> str:
    path = os.path.abspath(path)
    lower = path.lower()
    if lower.endswith(".pdf"):
        return extract_text_from_pdf(path)
    if lower.endswith(".doc"):
        # try to convert .doc to text using available system tools
        return convert_doc_to_text(path)
    # treat as plain text (including .txt and .docx if pre-converted)
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def detect_document_type(path: str, explicit_type: str = None) -> str:
    """Detect document type from filename or return explicit_type if provided.

    Returns a normalized document type string (e.g., 'sale_deed', 'nda', 'msa', 'dpa', 'will_deed', 'exchange_deed', 'sale_agreement').
    """
    if explicit_type:
        return explicit_type.lower().replace(" ", "_")
    name = os.path.basename(path).lower()
    # mapping of keywords to types
    mapping = {
        "sale deed": "sale_deed",
        "sale_deed": "sale_deed",
        "sale agreement": "sale_agreement",
        "sale": "sale_agreement",
        "deed": "sale_deed",
        "nda": "nda",
        "non-disclosure": "nda",
        "non disclosure": "nda",
        "master services agreement": "msa",
        "msa": "msa",
        "data processing": "dpa",
        "dpa": "dpa",
        "will": "will_deed",
        "exchange deed": "exchange_deed",
        "exchange_deed": "exchange_deed",
        "agreement": "agreement",
    }
    for k, v in mapping.items():
        if k in name:
            return v
    # fallback by extension
    ext = os.path.splitext(name)[1]
    if ext == ".doc" or ext == ".docx":
        # many docs are deeds/agreements; default to 'agreement'
        return "agreement"
    if ext == ".pdf":
        return "agreement"
    return "unknown"


def convert_doc_to_text(path: str) -> str:
    """Convert a legacy .doc file to plain text using available system tools.

    Tries macOS `textutil`, then `antiword`, `pandoc`, and `soffice` in that order.
    Returns extracted text or raises RuntimeError if no converter available.
    """
    converters = ["textutil", "antiword", "pandoc", "soffice"]
    # find available converter
    found = None
    for c in converters:
        if shutil.which(c):
            found = c
            break
    if not found:
        raise RuntimeError(
            "No converter found for .doc files. Install 'textutil' (macOS), 'antiword', 'pandoc', or 'libreoffice' (soffice), or provide a .txt file."
        )

    # create a temporary output file for conversion
    with tempfile.TemporaryDirectory() as td:
        out_txt = os.path.join(td, "out.txt")
        try:
            if found == "textutil":
                # macOS textutil: textutil -convert txt -output out.txt input.doc
                subprocess.run(["textutil", "-convert", "txt", "-output", out_txt, path], check=True)
            elif found == "antiword":
                # antiword writes to stdout
                with open(out_txt, "w", encoding="utf-8") as fo:
                    subprocess.run(["antiword", path], stdout=fo, check=True)
            elif found == "pandoc":
                subprocess.run(["pandoc", path, "-t", "plain", "-o", out_txt], check=True)
            elif found == "soffice":
                # libreoffice headless conversion: soffice --headless --convert-to txt:Text --outdir td path
                subprocess.run(["soffice", "--headless", "--convert-to", "txt:Text", "--outdir", td, path], check=True)
            else:
                raise RuntimeError("Unsupported converter: " + found)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Conversion failed using {found}: {e}")

        # try to read the produced text
        if os.path.exists(out_txt):
            with open(out_txt, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        # soffice may produce a file with same base name
        base_out = os.path.join(td, os.path.basename(path).rsplit('.', 1)[0] + ".txt")
        if os.path.exists(base_out):
            with open(base_out, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        raise RuntimeError("Document conversion produced no text output")


def sentence_split(text: str) -> List[str]:
    # naive sentence splitter on punctuation; keep abbreviations simple
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # preserve paragraph boundaries
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    sents = []
    for p in paras:
        # split on period/question/exclamation followed by whitespace
        parts = re.split(r'(?<=[\.!?])\s+', p)
        for s in parts:
            s = s.strip()
            if s:
                sents.append(s)
    return sents


def classify_sentence(sent: str):
    for name, rx in CLAUSE_PATTERNS.items():
        if rx.search(sent):
            return name
    return None


def group_sentences_into_clauses(sents: List[str]) -> List[dict]:
    clauses = []
    cur = {"sentences": [], "types": set()}
    for sent in sents:
        typ = classify_sentence(sent)
        if typ and cur["sentences"]:
            # start a new clause if this sentence looks like a new clause heading
            clauses.append(cur)
            cur = {"sentences": [sent], "types": set([typ])}
            continue
        # otherwise append
        cur["sentences"].append(sent)
        if typ:
            cur["types"].add(typ)
    if cur["sentences"]:
        clauses.append(cur)
    # convert to dict records
    records = []
    for c in clauses:
        text = " ".join(c["sentences"])[:10000]
        ctype = next(iter(c["types"]), None)
        records.append({"clause_type": ctype or "other", "clause_text": text})
    return records


def heuristic_risk_score(clause_text: str, clause_type: str):
    """Return (score 0-10, confidence 0-1) using a simple rule-based heuristic.

    This is a lightweight automatic assessment used as a prior_assessment. It is advisory only.
    """
    txt = clause_text.lower()
    # base values by clause type
    base = {
        "liability": 7,
        "indemnification": 6,
        "data_protection": 5,
        "termination": 6,
        "payment": 3,
        "confidentiality": 2,
        "services": 3,
        "governing_law": 2,
        "renewal": 4,
        "intellectual_property": 4,
        "other": 4,
    }
    score = base.get(clause_type or "other", 4)

    # keyword boosts / adjustments
    if re.search(r"unlimited liability|liability is unlimited|no cap on liability", txt):
        score = max(score, 9)
    if re.search(r"limit.*liability|cap .*liability|cap .*fees|fees paid", txt):
        score = max(score, 7)
    if re.search(r"gross negligence|willful misconduct|willful", txt):
        score = max(score, 8)
    if re.search(r"indemnif(y|ication).*any and all|any and all losses|all losses", txt):
        score = max(score, 8)
    if re.search(r"notify.*\b(72|48|24)\b.*hour|notify.*hours|breach notification", txt):
        # good notification reduces risk for data protection
        if clause_type == "data_protection":
            score = max(1, score - 3)
    if re.search(r"gdpr|ccpa|hipaa|soc2|iso 27001|iso27001", txt):
        if clause_type == "data_protection":
            score = max(1, score - 4)
    if re.search(r"terminate.*convenience|termination for convenience|terminate for convenience", txt):
        score = max(score, 7)
    if re.search(r"early termination|termination fee|remaining fees", txt):
        score = max(score, 6)

    # confidence: increase if strong keywords found
    conf = 0.6
    strong_kw = 0
    if re.search(r"unlimited liability|no cap|any and all|any and all losses|all losses", txt):
        strong_kw += 1
    if re.search(r"notify.*hour|breach notification|gdpr|ccpa|hipaa|soc2|iso27001", txt):
        strong_kw += 1
    if re.search(r"terminate for convenience|termination for convenience|early termination", txt):
        strong_kw += 1
    if strong_kw >= 2:
        conf = 0.9
    elif strong_kw == 1:
        conf = 0.75
    else:
        conf = 0.6

    # ensure numeric bounds
    score = max(0, min(10, int(round(score))))
    conf = max(0.0, min(1.0, float(conf)))
    return score, conf


def write_jsonl(records: List[dict], tenant: str, doc_id: str, out_dir: str, document_type: str = None):
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{tenant}_{doc_id}.jsonl")
    with open(out_path, "w", encoding="utf-8") as f:
        for i, r in enumerate(records):
            clause_text = r.get("clause_text", "")
            clause_type = r.get("clause_type")
            # compute heuristic prior assessment
            score, conf = heuristic_risk_score(clause_text, clause_type)
            rec = {
                "tenant_id": tenant,
                "doc_id": doc_id,
                "document_type": document_type,
                "chunk_id": f"{doc_id}_{i}",
                "clause_type": clause_type,
                "clause_text": clause_text,
                "n_tokens": len(clause_text.split()),
            }
            # compute hashes for provenance
            rec["doc_hash"] = hashlib.sha256(clause_text.encode("utf-8")).hexdigest()
            rec["chunk_hash"] = hashlib.sha256((clause_text + str(i)).encode("utf-8")).hexdigest()
            # add prior assessment as advisory metadata
            rec["prior_assessments"] = [
                {
                    "source": "auto-heuristic",
                    "score": score,
                    "confidence": conf,
                }
            ]
            # also expose top-level heuristic fields for convenience
            rec["heuristic_risk_score"] = score
            rec["heuristic_confidence"] = conf
            f.write(json.dumps(rec) + "\n")
    return out_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=False, default=None, help="path to input file or filename in resources/ (if omitted the script will process all supported files under the project's resources/ directory)")
    parser.add_argument("--tenant", required=True)
    parser.add_argument("--doc", required=False, help="optional doc id; if omitted when processing a single file the basename (without extension) will be used; when processing multiple files a per-file doc id is derived from each filename")
    parser.add_argument("--doc-type", required=False, help="optional document type override (sale_deed, nda, msa, dpa, will_deed, exchange_deed, sale_agreement)")
    parser.add_argument("--out", required=False, help="path to output directory")
    args = parser.parse_args()

    # Determine repository root (two levels up from this file: knowledge/ingest -> project root)
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    def resolve_candidate(path_str: str) -> str:
        # If simple filename, prefer repo-level resources/ and resources/sale_docs/
        if not os.path.isabs(path_str) and os.sep not in path_str:
            candidate = os.path.join(repo_root, "knowledge/resources/"+args.tenant, path_str)
            if os.path.exists(candidate):
                return candidate
            return os.path.abspath(path_str)
        return os.path.abspath(path_str)

    # If no --input provided, process all supported files in repo_root/resources/
    inputs = []
    if not args.input:
        resources_dir = os.path.join(repo_root, "knowledge/resources/"+args.tenant)
        if not os.path.exists(resources_dir):
            raise RuntimeError(f"resources directory not found at expected path: {resources_dir}")
        # collect supported extensions
        for fn in sorted(os.listdir(resources_dir)):
            if fn.lower().endswith(('.pdf', '.doc', '.docx', '.txt')):
                inputs.append(os.path.join(resources_dir, fn))
        if not inputs:
            raise RuntimeError(f"no supported files found under resources/ (searched {resources_dir})")
    else:
        resolved = resolve_candidate(args.input)
        inputs = [resolved]

    # Process each input file
    total = 0
    for input_path in inputs:
        print("extracting text from", input_path)
        if not os.path.exists(input_path):
            print(f"warning: file not found, skipping: {input_path}")
            continue
        text = extract_text(input_path)
        if not text or not text.strip():
            print(f"warning: no text extracted from {input_path}, skipping")
            continue

        sents = sentence_split(text)
        if not sents:
            print(f"warning: no sentences extracted from {input_path}, skipping")
            continue

        clause_records = group_sentences_into_clauses(sents)
        # derive document id and document type
        if args.doc:
            doc_id = args.doc
        else:
            doc_id = os.path.splitext(os.path.basename(input_path))[0]
        doc_type = detect_document_type(input_path, explicit_type=getattr(args, 'doc_type', None))
        out_path = os.path.join(repo_root, "knowledge/resources/"+args.tenant, "sale_docs")
        out = write_jsonl(clause_records, args.tenant, doc_id, out_path, document_type=doc_type)
        print("wrote", out, "with", len(clause_records), "clauses")
        total += len(clause_records)

    print(f"done: processed {len(inputs)} file(s), wrote {total} clauses to {args.out}")


if __name__ == "__main__":
    main()

