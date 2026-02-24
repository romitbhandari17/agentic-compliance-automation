# File: agents/compliance/main.py
"""
Compliance lambda for agentic flow.
Accepts the ingestion output format:
{
  "contract_id": "...",
  "s3": {"bucket": "...", "key": "..."},
  "s3_uri": "s3://.../...",
  "extracted_text": "..."
}

Performs simple heuristic checks for GDPR / SOX related concerns and then
sends a prompt to Amazon Bedrock (amazon.nova-lite) in us-east-1 to
produce a human-readable compliance summary.

This file includes print() and logger statements in each function.
"""

import os
import json
import logging
import re
import boto3
from typing import Dict, Any
import sys

# Add shared/ to path for tenant helpers
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "shared")))
from agents.shared.tenant_context import extract_tenant_id_from_s3_key, load_tenant_config

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Bedrock client is created explicitly in us-east-1 as requested
BEDROCK_REGION = "us-east-1"
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.amazon.nova-lite-v1:0")

bedrock = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)

# A few simple regex-based heuristics for PII/financial indicators
PII_PATTERNS = {
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "email": re.compile(r"[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+"),
    "phone": re.compile(r"\b\+?\d[\d\-() ]{7,}\b"),
    "account_number": re.compile(r"\baccount\s*(number|no)[:#\s]*\d{4,}\b", re.I),
}

FINANCIAL_KEYWORDS = [
    "invoice", "payment", "amount", "salary", "compensation", "financial statement",
    "balance sheet", "tax", "audit", "revenue", "expense",
]

GDPR_KEYWORDS = ["personal data", "data subject", "consent", "processing", "controller", "processor", "data protection"]


def _extract_overall_compliance(model_text: str) -> Dict[str, Any]:
    """Best-effort extraction of overall_compliance from non-JSON model output."""
    if not isinstance(model_text, str) or not model_text.strip():
        return {}

    match = re.search(r"\"overall_compliance\"\s*:\s*\{[^}]*\}", model_text)
    if not match:
        return {}

    snippet = "{" + match.group(0) + "}"
    try:
        parsed = json.loads(snippet)
    except Exception:
        return {}

    overall = parsed.get("overall_compliance")
    if not isinstance(overall, dict):
        return {}

    # Normalize expected keys if present
    normalized: Dict[str, Any] = {}
    if "compliance_status" in overall:
        normalized["compliance_status"] = overall.get("compliance_status")
    if "overall_compliance_score" in overall:
        normalized["overall_compliance_score"] = overall.get("overall_compliance_score")

    return normalized or overall


def _log_and_print(msg: str, *args: Any) -> None:
    if args:
        try:
            msg = msg % args
        except Exception:
            msg = f"{msg} {' '.join(str(a) for a in args)}"
    print(msg)
    logger.info(msg)


def analyze_text_rules(extracted_text: str) -> Dict[str, Any]:
    """Run simple heuristic checks for GDPR/SOX relevant indicators.
    Returns a dict summarizing findings.
    """
    _log_and_print("analyze_text_rules: starting analysis")

    findings = {"pii": {}, "financial_indicators": [], "gdpr_indicators": []}

    # PII detection
    for name, pattern in PII_PATTERNS.items():
        matches = pattern.findall(extracted_text or "")
        findings["pii"][name] = len(matches)
        _log_and_print(f"analyze_text_rules: found {len(matches)} matches for {name}")

    # Financial keyword checks
    lowered = (extracted_text or "").lower()
    for kw in FINANCIAL_KEYWORDS:
        if kw in lowered:
            findings["financial_indicators"].append(kw)
            _log_and_print(f"analyze_text_rules: financial keyword matched: {kw}")

    # GDPR keyword checks
    for kw in GDPR_KEYWORDS:
        if kw in lowered:
            findings["gdpr_indicators"].append(kw)
            _log_and_print(f"analyze_text_rules: GDPR keyword matched: {kw}")

    _log_and_print("analyze_text_rules: analysis complete")
    return findings


def _build_bedrock_prompt(
    contract_id: str,
    s3_uri: str,
    extracted_text: str,
    findings: Dict[str, Any],
    region: str,
    industry: str,
) -> str:
    _log_and_print("_build_bedrock_prompt: building prompt for bedrock model")

    # Truncate extracted_text to a reasonable size for model input if necessary
    max_chars = 5000
    text_sample = (extracted_text or "")
    truncated = False
    if len(text_sample) > max_chars:
        text_sample = text_sample[:max_chars]
        truncated = True
        _log_and_print("_build_bedrock_prompt: truncated extracted_text for model input")

    prompt = (
        f"You are a compliance assistant.\n"
        f"As compliance checks differ based on region and industry, " "Do the checks based on the extracted region and industry \n"
        "like following:" "Data Privacy: GPDR for EU, CCPA for US, HIPAA for healthcare etc.\n" 
        "Security: SOC2, ISO, etc. " f"Consider Region: {region or 'unknown'}\n" f"Consider Industry: {industry or 'unknown'}\n"
        f"Contract ID: {contract_id}\n"
        f"S3 URI: {s3_uri}\n"
        f"Perform GDPR and SOX related compliance checks on the following extracted contract text.\n"
        f"Provide a concise human-readable summary of compliance issues, a severity rating (low/medium/high), and recommended remediation steps.\n"
        f"Also include the heuristic findings (PII counts, financial indicators, GDPR keyword hits).\n\n"
        f"Heuristic findings: {json.dumps(findings)}\n\n"
        f"Contract text (truncated={truncated}):\n{text_sample}\n\n"
        f"overall_compliance_score: <number 0-10 derived from identified clause scores (0-10)>,\n"
        f"Return JSON object with keys: summary, severity, recommendations, details, overall_compliance. Keep the JSON parsable.\n"
        f"overall_compliance format:\n"
        f"{{\n"
        f"  \"compliance_status\": \"PARTIAL|PASS|FAIL\",\n"
        f"  \"overall_compliance_score\": ,\n"
        f"}}\n"
        f"In details, include an array named explainability with objects in this format:\n"
        f"{{\n"
        f"  \"clause\": \"Data Processing\",\n"
        f"  \"framework\": \"GDPR|SOX\",\n"
        f"  \"compliance_status\": \"Passed|Failed|NeedsReview\",\n"
        f"  \"violated_requirement\": \"string\",\n"
        f"  \"reasoning\": \"string\",\n"
        f"  \"score\": <0-10>\n"
        f"}}\n"
    )

    _log_and_print("_build_bedrock_prompt: prompt built successfully %s", prompt)
    return prompt


def call_bedrock_summary(prompt: str, model_id: str = None) -> str:
    """Call Bedrock model to produce a compliance summary. Returns the raw model text output.
    Uses the Bedrock Runtime API (invoke_model) with region fixed to us-east-1.

    If no model_id is provided (via argument or BEDROCK_MODEL_ID env var), return a helpful error message
    instead of attempting to call Bedrock with an invalid default.
    """
    # Determine model id: prefer explicit argument, then env var
    global output_text
    actual_model_id = model_id or BEDROCK_MODEL_ID or None
    _log_and_print(f"call_bedrock_summary: requested model_id={model_id} env_model={os.environ.get('BEDROCK_MODEL_ID')}")

    if not actual_model_id:
        msg = (
            "Bedrock model id not provided. Please set the environment variable BEDROCK_MODEL_ID to a valid model identifier "
            "or ARN (for example: arn:aws:bedrock:us-east-1:ACCOUNT_ID:model/MODEL_NAME or a modelId expected by Bedrock)."
        )
        _log_and_print(f"call_bedrock_summary: {msg}")
        return json.dumps({"summary": "Bedrock model id not configured", "error": msg})

    _log_and_print(f"call_bedrock_summary: invoking model {actual_model_id} in region {BEDROCK_REGION}")

    # Build a chat-style payload that includes the required `messages` key.
    body_dict = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"text": prompt}
                ]
            }
        ]
    }

    body = json.dumps(body_dict).encode("utf-8")
    _log_and_print(f"call_bedrock_summary: request body size={len(body)} bytes")

    try:
        response = bedrock.invoke_model(
            modelId=actual_model_id,
            contentType="application/json",
            accept="application/json",
            body=body,
        )

        # The response body is usually a streaming Body - read it
        model_bytes = response.get("body")
        if hasattr(model_bytes, "read"):
            raw = model_bytes.read()
        else:
            raw = model_bytes

        model_text = raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else str(raw)

        # Some Bedrock responses return a JSON object with `outputs` -> content -> text
        try:
            parsed = json.loads(model_text)
            # Try to extract common fields if present
            output_text = ""
            output_blocks = (
                parsed.get("output", {})
                .get("message", {})
                .get("content", [])
            )
            if isinstance(output_blocks, list):
                output_text = "".join(
                    block.get("text", "")
                    for block in output_blocks
                    if isinstance(block, dict)
                ).strip()

        except Exception:
            # not JSON or unexpected shape — keep raw model_text
            pass

        print("model tex %s",output_text)
        return output_text

    except Exception as e:
        # Improve the error message for invalid model identifiers
        err_msg = str(e)
        suggestion = "Ensure BEDROCK_MODEL_ID is a valid Bedrock model identifier or ARN and that your IAM principal has Bedrock access."
        _log_and_print(f"call_bedrock_summary: bedrock invocation failed: {err_msg}")
        return json.dumps({
            "summary": "Bedrock invocation failed",
            "error": err_msg,
            "suggestion": suggestion,
            "model_id_used": actual_model_id,
        })


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for compliance step. Accepts the ingestion output and returns a compliance summary.
    """
    _log_and_print("handler: compliance handler invoked")

    contract_id = event.get("contract_id")
    s3_info = event.get("s3") or {}
    s3_uri = event.get("s3_uri") or f"s3://{s3_info.get('bucket', '')}/{s3_info.get('key', '')}"
    extracted_text = event.get("extracted_text") or ""

    tenant_id = extract_tenant_id_from_s3_key(s3_info.get("key"))
    tenant_cfg = load_tenant_config(tenant_id)
    region = tenant_cfg.get("region") if isinstance(tenant_cfg, dict) else None
    industry = tenant_cfg.get("industry") if isinstance(tenant_cfg, dict) else None

    _log_and_print(f"handler: contract_id={contract_id}, s3_uri={s3_uri}")
    _log_and_print(f"handler: tenant_id={tenant_id}, region={region}, industry={industry}")

    # Run heuristic analysis
    findings = analyze_text_rules(extracted_text)

    # Build prompt and call Bedrock for a human-friendly summary
    prompt = _build_bedrock_prompt(contract_id, s3_uri, extracted_text, findings, region, industry)
    model_output = call_bedrock_summary(prompt)

    overall_compliance = {}
    overall_compliance = _extract_overall_compliance(model_output)

    result = {
        "contract_id": contract_id,
        "s3_uri": s3_uri,
        "s3":s3_info,
        # "findings": findings,
        # "model_output_raw": model_output,
        "model_response": model_output,
        "compliance_findings": overall_compliance,
    }

    _log_and_print("handler: compliance processing complete")
    return result

