"""
Decision lambda for agentic flow.
Decides next action based on compliance and risk analysis outputs.
"""

import json
import logging
from typing import Any, Dict, Optional
import os
import sys

# Add shared/ to path for tenant helpers
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "shared")))
from agents.shared.tenant_context import extract_tenant_id_from_s3_key, load_tenant_config

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _log(msg: str) -> None:
    print(msg)
    logger.info(msg)


def _to_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _find_first_number(payload: Any, keys: set) -> Optional[float]:
    if isinstance(payload, dict):
        for k, v in payload.items():
            if k in keys:
                num = _to_float(v)
                if num is not None:
                    return num
            num = _find_first_number(v, keys)
            if num is not None:
                return num
    elif isinstance(payload, list):
        for item in payload:
            num = _find_first_number(item, keys)
            if num is not None:
                return num
    return None


def _extract_compliance_status(event: Dict[str, Any]) -> Optional[str]:
    status = event.get("compliance_status")
    if isinstance(status, str) and status.strip():
        return status

    compliance = event.get("compliance_findings") or {}
    if isinstance(compliance, dict):
        status = compliance.get("compliance_status")
        if isinstance(status, str) and status.strip():
            return status

    return None


def _normalize_compliance_status(status: Optional[str]) -> Optional[str]:
    if not status:
        return None
    value = status.strip().lower()
    if value in {"non-compliant", "non_compliant", "fail", "failed", "failures", "failing"}:
        return "Non-Compliant"
    if value in {"compliant", "pass", "passed", "ok", "success"}:
        return "Compliant"
    if value in {"partial", "partially_compliant", "partially compliant", "needsreview", "needs_review", "needs review"}:
        return "Partial"
    return status


def _resolve_thresholds(event: Dict[str, Any]) -> Dict[str, float]:
    s3_info = event.get("s3") or {}
    tenant_id = extract_tenant_id_from_s3_key(s3_info.get("key"))
    print(f"_resolve_thresholds: tenant_id={tenant_id}")
    tenant_config = load_tenant_config(tenant_id)
    print(f"_resolve_thresholds: tenant_config={tenant_config}")

    risk_threshold = _to_float(tenant_config.get("risk_score_threshold"))
    confidence_threshold = _to_float(tenant_config.get("confidence_threshold"))

    return {
        "tenant_id": tenant_id,
        "risk_score_threshold": risk_threshold if risk_threshold is not None else 7.0,
        "confidence_threshold": confidence_threshold if confidence_threshold is not None else 0.7,
    }


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    _log("handler: decision lambda invoked")

    compliance_findings = event.get("compliance_findings") or {}
    risk_findings = event.get("risk_analysis_findings") or {}

    thresholds = _resolve_thresholds(event)
    risk_score_threshold = thresholds["risk_score_threshold"]
    confidence_threshold = thresholds["confidence_threshold"]
    _log(f"handler: thresholds risk_score_threshold={risk_score_threshold}, confidence_threshold={confidence_threshold}")

    compliance_status_raw = _extract_compliance_status(event)
    compliance_status = _normalize_compliance_status(compliance_status_raw)

    overall_risk_score = _to_float(risk_findings.get("overall_risk_score"))
    overall_confidence = _to_float(risk_findings.get("overall_confidence"))

    decision = "Auto-Approve"
    reason = "Default approval"

    if overall_risk_score is not None and overall_risk_score >= risk_score_threshold:
        decision = "Legal Review"
        reason = f"overall_risk_score={overall_risk_score} >= {risk_score_threshold}"
    elif compliance_status == "Non-Compliant":
        decision = "Escalate"
        reason = "compliance_status=Non-Compliant"
    elif overall_confidence is not None and overall_confidence < confidence_threshold:
        decision = "Human Review"
        reason = f"overall_confidence={overall_confidence} < {confidence_threshold}"

    result = {
        "contract_id": event.get("contract_id"),
        "s3": event.get("s3"),
        "s3_uri": event.get("s3_uri"),
        "compliance_status": compliance_status or compliance_status_raw,
        "overall_compliance_score": _to_float(compliance_findings.get("overall_compliance_score")),
        "overall_risk_score": overall_risk_score,
        "overall_confidence": overall_confidence,
        "decision": decision,
        "reason": reason,
        "thresholds": {
            "risk_score_threshold": risk_score_threshold,
            "confidence_threshold": confidence_threshold,
        },
        "tenant_id": thresholds.get("tenant_id"),
        "inputs": {
            "compliance_findings": compliance_findings,
            "risk_analysis_findings": risk_findings,
        },
    }

    _log(f"handler: decision={decision} reason={reason}")
    return result

