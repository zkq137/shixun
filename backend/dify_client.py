"""Helpers for calling local Dify apps."""

import json
import os
from urllib.request import Request, urlopen


try:
    from backend.local_settings import DIFY_API_KEY as LOCAL_DIFY_API_KEY
    from backend.local_settings import DIFY_BASE_URL as LOCAL_DIFY_BASE_URL
except ImportError:
    LOCAL_DIFY_API_KEY = ""
    LOCAL_DIFY_BASE_URL = ""


def _clean_base_url(raw_value):
    value = (raw_value or "").strip()
    if not value:
        return "http://localhost"
    if value.endswith("/v1"):
        value = value[:-3]
    return value.rstrip("/")


def get_dify_settings():
    base_url = _clean_base_url(
        os.getenv("DIFY_BASE_URL") or LOCAL_DIFY_BASE_URL or "http://localhost"
    )
    api_key = (os.getenv("DIFY_API_KEY") or LOCAL_DIFY_API_KEY or "").strip()
    return {
        "base_url": base_url,
        "api_key": api_key,
        "workflow_url": f"{base_url}/v1/workflows/run",
    }


def _extract_workflow_text(outputs):
    if not isinstance(outputs, dict):
        return str(outputs or "")

    for key in ("text", "answer", "result", "output"):
        value = outputs.get(key)
        if value:
            return str(value)

    return json.dumps(outputs, ensure_ascii=False, indent=2)


def run_workflow(inputs, user="admin", response_mode="blocking"):
    settings = get_dify_settings()
    if not settings["api_key"]:
        raise RuntimeError(
            "未配置 Dify API Key。请在 backend/local_settings.py 或环境变量中设置 DIFY_API_KEY。"
        )

    payload = json.dumps(
        {
            "inputs": inputs,
            "response_mode": response_mode,
            "user": user,
        }
    ).encode("utf-8")

    request = Request(
        settings["workflow_url"],
        data=payload,
        headers={
            "Authorization": f"Bearer {settings['api_key']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urlopen(request, timeout=120) as response:
        body = json.loads(response.read().decode("utf-8"))

    data = body.get("data") or {}
    outputs = data.get("outputs") or {}

    return {
        "workflow_run_id": body.get("workflow_run_id") or data.get("id") or "",
        "task_id": body.get("task_id") or "",
        "status": data.get("status") or body.get("status") or "unknown",
        "outputs": outputs,
        "text": _extract_workflow_text(outputs),
        "raw": body,
    }
