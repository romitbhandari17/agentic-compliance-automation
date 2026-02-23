import json
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger()
logger.setLevel(logging.INFO)

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "tenant_config.json")


def extract_tenant_id_from_s3_key(key: Optional[str]) -> Optional[str]:
    if not isinstance(key, str):
        return None
    cleaned = key.lstrip("/").strip()
    if not cleaned:
        return None
    return cleaned.split("/", 1)[0]


def load_tenant_config(tenant_id: Optional[str], config_path: Optional[str] = None) -> Dict[str, Any]:
    path = config_path or DEFAULT_CONFIG_PATH
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.warning("load_tenant_config: failed to read %s: %s", path, e)
        return {}

    if not isinstance(data, dict):
        return {}

    if tenant_id and tenant_id in data and isinstance(data[tenant_id], dict):
        return data[tenant_id]

    default_cfg = data.get("default")
    return default_cfg if isinstance(default_cfg, dict) else {}

