"""Lightweight local persistence for turnover risk module settings and notes."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from uuid import uuid4


STORE_PATH = Path(__file__).resolve().parent / "data" / "risk_module_state.json"

DEFAULT_STATE = {
    "settings": {
        "highRiskThreshold": 70,
        "mediumRiskThreshold": 40,
        "updatedAt": "",
    },
    "employeeNotes": {},
    "followUps": {},
}


def _utc_now_iso():
    return datetime.now().isoformat(timespec="seconds")


def _ensure_store():
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not STORE_PATH.exists():
        STORE_PATH.write_text(
            json.dumps(DEFAULT_STATE, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _load_state():
    _ensure_store()
    try:
        data = json.loads(STORE_PATH.read_text(encoding="utf-8"))
    except Exception:
        data = deepcopy(DEFAULT_STATE)

    state = deepcopy(DEFAULT_STATE)
    if isinstance(data, dict):
        state["settings"].update(data.get("settings") or {})
        state["employeeNotes"].update(data.get("employeeNotes") or {})
        state["followUps"].update(data.get("followUps") or {})
    return state


def _save_state(state):
    _ensure_store()
    STORE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_risk_settings():
    state = _load_state()
    settings = deepcopy(state["settings"])
    settings["highRiskThreshold"] = int(float(settings.get("highRiskThreshold") or 70))
    settings["mediumRiskThreshold"] = int(float(settings.get("mediumRiskThreshold") or 40))

    # Keep thresholds in a sensible order.
    if settings["mediumRiskThreshold"] >= settings["highRiskThreshold"]:
        settings["mediumRiskThreshold"] = max(0, settings["highRiskThreshold"] - 10)
    return settings


def update_risk_settings(high_risk_threshold, medium_risk_threshold):
    state = _load_state()
    high = int(float(high_risk_threshold))
    medium = int(float(medium_risk_threshold))

    if high < 1:
        high = 1
    if high > 100:
        high = 100
    if medium < 0:
        medium = 0
    if medium >= high:
        medium = max(0, high - 10)

    state["settings"] = {
        "highRiskThreshold": high,
        "mediumRiskThreshold": medium,
        "updatedAt": _utc_now_iso(),
    }
    _save_state(state)
    return deepcopy(state["settings"])


def get_employee_note(employee_id):
    state = _load_state()
    return deepcopy(state["employeeNotes"].get(employee_id) or {"note": "", "updatedAt": ""})


def update_employee_note(employee_id, note, author="部门经理"):
    state = _load_state()
    value = {
        "note": str(note or "").strip(),
        "updatedAt": _utc_now_iso(),
        "updatedBy": author,
    }
    state["employeeNotes"][employee_id] = value
    _save_state(state)
    return deepcopy(value)


def get_follow_ups(employee_id):
    state = _load_state()
    items = deepcopy(state["followUps"].get(employee_id) or [])
    items.sort(key=lambda item: item.get("followUpDate") or "", reverse=True)
    return items


def add_follow_up(employee_id, status, note, owner="", follow_up_date="", next_action=""):
    state = _load_state()
    items = state["followUps"].setdefault(employee_id, [])
    record = {
        "id": uuid4().hex[:10],
        "status": str(status or "待跟进").strip() or "待跟进",
        "note": str(note or "").strip(),
        "owner": str(owner or "").strip(),
        "followUpDate": str(follow_up_date or "").strip(),
        "nextAction": str(next_action or "").strip(),
        "createdAt": _utc_now_iso(),
    }
    items.append(record)
    _save_state(state)
    return deepcopy(record)
