import json
import uuid
import logging
import os
import re
from typing import Dict, Any, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Use AWS_REGION env var if present; otherwise default to us-east-1
REGION = os.environ.get("AWS_REGION") or "us-east-1"
# Bedrock settings (match `agents/compliance/main.py`)
BEDROCK_REGION = "us-east-1"
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.amazon.nova-lite-v1:0")

# Global bedrock client (explicit region per project requirement)
bedrock = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)


def _make_prompt(extracted_text: str, contract_id: Optional[str]) -> str:
    """Build a clear prompt asking the model to return exact JSON matching the required schema."""
    return (
        f"You are a legal assistant that analyzes contract text and returns a JSON object with the following schema:\n"
        "{\n"
        "  \"risk_breakdown\": { \"liability\": <0-10>, \"indemnification\": <0-10>, \"data_protection\": <0-10>, \"termination\": <0-10> },\n"
        "  \"overall_risk_score\": <number 0-10>,\n"
        "  \"risk_level\": \"Low|Medium|High\",\n"
        "  \"confidence_score\": <0.0-1.0>,\n"
        "  \"top_risks\": [\"string\", ...],\n"
        "  \"clauses\": [\n"
        "    {\n"
        "      \"clause_name\": \"string\",\n"
        "      \"risk_score\": <1-10>,\n"
        "      \"reasoning\": \"2-3 sentences explaining the risk\",\n"
        "      \"clause_text\": \"exact clause language used in the reasoning\",\n"
        "      \"confidence_score\": <0.0-1.0>\n"
        "    }\n"
        "  ]\n"
        "}\n"
        "Only output valid JSON (no extra commentary). Make numeric scores integers 0-10 for risk_breakdown and overall_risk_score can be decimal. "
        "Confidence must be between 0 and 1. Top risks should be a short list (strings). For each identified clause, include a risk_score, 2-3 sentence reasoning, and the exact clause_text used.\n\n"
        f"Contract ID: {contract_id}\n"
        "Now analyze the following extracted text from the contract and produce JSON that follows the schema exactly. If some categories are not present, score them conservatively (low risk=0, high risk=10) and explain nothing, only return the JSON.\n\n"
        "EXTRACTED_TEXT:\n" + extracted_text
    )


def _invoke_bedrock(prompt: str, model_id: str = None) -> Dict[str, Any]:
    """Invoke Bedrock (bedrock-runtime) using the same pattern as the compliance lambda.

    Returns a dict containing raw output (string) on success or an error object on failure.
    """
    actual_model_id = model_id or BEDROCK_MODEL_ID or None
    logger.info("_invoke_bedrock: requested model_id=%s env_model=%s", model_id, os.environ.get("BEDROCK_MODEL_ID"))

    if not actual_model_id:
        msg = (
            "Bedrock model id not provided. Please set the environment variable BEDROCK_MODEL_ID to a valid model identifier or ARN."
        )
        logger.warning("_invoke_bedrock: %s", msg)
        return {"success": False, "raw": json.dumps({"error": "Bedrock model id not configured", "message": msg})}

    logger.info("_invoke_bedrock: invoking model %s in region %s", actual_model_id, BEDROCK_REGION)

    # Build a chat-style payload that includes the required `messages` key matching compliance lambda
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
    logger.info("_invoke_bedrock: request body size=%d bytes", len(body))

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

        # Try to extract common fields if present (some Bedrock responses include outputs->content->text)
        try:
            parsed = json.loads(model_text)
            if isinstance(parsed, dict):
                outputs = parsed.get("outputs") or parsed.get("result")
                if outputs and isinstance(outputs, list):
                    first = outputs[0]
                    content = first.get("content") if isinstance(first, dict) else None
                    if isinstance(content, list):
                        texts = [c.get("text") for c in content if isinstance(c, dict) and c.get("text")]
                        if texts:
                            model_text = "\n".join(texts)
        except Exception:
            # not JSON or unexpected shape — keep raw model_text
            pass

        logger.info("_invoke_bedrock: model invocation successful")
        return {"success": True, "raw": model_text}

    except Exception as e:
        err_msg = str(e)
        suggestion = "Ensure BEDROCK_MODEL_ID is a valid Bedrock model identifier or ARN and that your IAM principal has Bedrock access."
        logger.exception("_invoke_bedrock: bedrock invocation failed: %s", err_msg)
        return {"success": False, "raw": json.dumps({
            "summary": "Bedrock invocation failed",
            "error": err_msg,
            "suggestion": suggestion,
            "model_id_used": actual_model_id,
        })}


def _extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """Try to find the first JSON object in the text and parse it."""
    if not text:
        return None
    # Direct parse attempt
    try:
        return json.loads(text)
    except Exception:
        pass

    # Fallback: find the largest { ... } substring
    # This is a best-effort heuristic
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start:end + 1]
        try:
            return json.loads(candidate)
        except Exception:
            pass

    # Try regex-based extraction of JSON-like portions (simpler pattern)
    matches = re.findall(r"\{[^}]*\}", text, flags=re.DOTALL)
    for m in matches:
        try:
            return json.loads(m)
        except Exception:
            continue

    return None


def _compute_heuristic_from_text(text: str) -> Dict[str, Any]:
    """Fallback heuristic analysis if Bedrock fails: very simple keyword-based scoring."""
    lower = text.lower()
    scores = {
        "liability": 0,
        "indemnification": 0,
        "data_protection": 0,
        "termination": 0,
    }

    # Simple heuristics: presence of certain keywords increases risk
    if "unlimited liability" in lower or "liability" in lower and "cap" not in lower:
        scores["liability"] = 8
    if "indemnif" in lower:
        scores["indemnification"] = 6
    if "data breach" in lower or "personal data" in lower or "gdpr" in lower:
        scores["data_protection"] = 7
    if "termination" in lower or "terminate" in lower:
        scores["termination"] = 4

    # ensure numeric and compute overall
    vals = list(scores.values())
    overall = round(sum(vals) / len(vals), 2)
    risk_level = "Low"
    if overall >= 7:
        risk_level = "High"
    elif overall >= 4:
        risk_level = "Medium"

    top_risks = []
    if scores["liability"] >= 7:
        top_risks.append("Unlimited liability clause")
    if scores["data_protection"] >= 6:
        top_risks.append("No explicit data breach notification timeline")

    return {
        "risk_breakdown": scores,
        "overall_risk_score": overall,
        "risk_level": risk_level,
        "confidence_score": 0.5,
        "top_risks": top_risks,
    }


def handler(event: Dict[str, Any], context=None) -> Dict[str, Any]:
    """Entry point for the risk analysis lambda.

    Expected input format (from ingestion lambda):
    {
      "contract_id": "...",
      "s3": {"bucket": "...", "key": "..."},
      "s3_uri": "s3://...",
      "extracted_text": "..."
    }

    Returns structured analysis JSON. Uses Bedrock when available and falls back to heuristics on errors.
    """
    contract_id = event.get("contract_id") or str(uuid.uuid4())
    extracted_text = event.get("extracted_text")

    if not extracted_text:
        logger.warning("No extracted_text provided in event for contract %s", contract_id)
        return {
            "contract_id": contract_id,
            "error": "no_extracted_text",
            "message": "No extracted_text present in event",
        }

    prompt = _make_prompt(extracted_text, contract_id)

    # Call Bedrock
    bedrock_result = _invoke_bedrock(prompt)

    model_output_raw = bedrock_result.get("raw")
    model_output_parsed = None
    analysis = None

    if bedrock_result.get("success") and model_output_raw:
        # Try to parse model output as JSON
        parsed = _extract_json_from_text(model_output_raw)
        model_output_parsed = parsed
        if parsed:
            # Basic validation: ensure keys exist
            keys_ok = all(k in parsed for k in ("risk_breakdown", "overall_risk_score", "risk_level", "confidence_score", "top_risks"))
            if keys_ok:
                analysis = parsed
            else:
                logger.warning("Bedrock returned JSON but missing expected keys for contract %s", contract_id)

    if analysis is None:
        # Either Bedrock failed or didn't return valid JSON — fallback heuristic
        heuristic = _compute_heuristic_from_text(extracted_text)
        analysis = heuristic

    # Return a rich response including raw model output for debugging
    return {
        "contract_id": contract_id,
        "s3": event.get("s3"),
        "s3_uri": event.get("s3_uri"),
        "model_output_raw": model_output_raw,
        "findings": analysis,
        "model_output_parsed": model_output_parsed,
    }
