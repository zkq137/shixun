import os
import re
import uuid
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import quote
import json as _json
from urllib.error import HTTPError, URLError

from flask import Flask, Response, jsonify, request, stream_with_context
from flask_cors import CORS

from backend.wechat_config import (
    WECHAT_APP_ID,
    WECHAT_APP_SECRET,
    WECHAT_QR_URL,
    WECHAT_TOKEN_URL,
    WECHAT_USERINFO_URL,
    FRONTEND_SUCCESS_URL,
)
from backend.dify_client import run_workflow, get_dify_settings
from backend.risk_module_store import add_follow_up, get_follow_ups, get_risk_settings, update_employee_note, update_risk_settings

from backend.queries import (
    get_nine_box,
    get_overview,
    get_risk_alerts,
    get_risk_overview,
    get_risk_employees,
    get_risk_employee_detail,
    get_succession_candidates,
    get_succession_candidates_filtered,
    get_departments,
    get_training_plans,
    get_employee_by_no,
    get_potential_list,
    get_potential_by_id,
    save_potential_assessment,
    get_potential_assessment_history,
    get_all_assessment_records,
    get_training_list,
    add_training,
    update_training_status,
    delete_training,
    get_completed_trainings_from_ability,
    get_position_risk_list,
    get_employee_risk_list,
    get_position_profile_names,
)
from backend.face_auth import get_face_encoding, compare_faces, decode_base64_image

app = Flask(__name__)
app.json.ensure_ascii = False  # 确保JSON返回中文不转义
CORS(app)

# ── 二维码登录 Session 存储 ─────────────────────────────
# token -> { "status": "pending"|"scanned"|"confirmed", "created_at": timestamp }
qrcode_sessions = {}
promotion_agent_sessions = {}

BASE_DIR = Path(__file__).resolve().parent
LOCAL_ENV_PATH = BASE_DIR / ".env"
_LOCAL_ENV_CACHE = None


def _load_local_env():
    global _LOCAL_ENV_CACHE
    if _LOCAL_ENV_CACHE is not None:
        return _LOCAL_ENV_CACHE

    values = {}
    try:
        raw_text = LOCAL_ENV_PATH.read_text(encoding="utf-8")
    except Exception:
        raw_text = ""

    for line in raw_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value

    _LOCAL_ENV_CACHE = values
    return values


def _get_setting(name, default=""):
    env_value = os.getenv(name)
    if env_value not in (None, ""):
        return env_value
    return _load_local_env().get(name, default)


def _clean_base_url(raw_value):
    value = (raw_value or "").strip()
    if not value:
        return "http://127.0.0.1"
    if value.endswith("/v1"):
        value = value[:-3]
    return value.rstrip("/")


def _get_succession_dify_settings():
    base_url = _clean_base_url(_get_setting("DIFY_BASE_URL", "http://127.0.0.1"))
    api_key = (_get_setting("DIFY_SUCCESSION_API_KEY") or "").strip()

    # Fallback to local_settings.py if .env fails
    if not api_key:
        try:
            from backend.local_settings import (
                DIFY_SUCCESSION_API_KEY as LOCAL_SUCCESSION_KEY,
            )
            api_key = (LOCAL_SUCCESSION_KEY or "").strip()
        except ImportError:
            pass

    return {
        "base_url": base_url,
        "api_key": api_key,
        "workflow_url": f"{base_url}/v1/workflows/run",
    }


def _strip_model_private_thought(value):
    text = str(value or "")
    text = re.sub(r"<think>.*?</think>\s*", "", text, flags=re.S | re.I)
    text = re.sub(r"</?think>\s*", "", text, flags=re.I)
    return text.strip()


def _normalize_succession_workflow_response(body):
    data = body.get("data") if isinstance(body, dict) else {}
    outputs = data.get("outputs") if isinstance(data, dict) else {}
    if not outputs and isinstance(body, dict):
        outputs = body.get("outputs") or {}

    promotion_report = _strip_model_private_thought(outputs.get("promotion_report"))
    if promotion_report in (None, ""):
        promotion_report = _strip_model_private_thought(outputs.get("text") or outputs.get("answer") or outputs.get("result") or "")

    error = ""
    if isinstance(data, dict):
        error = data.get("error") or ""
    if not error and isinstance(body, dict):
        error = body.get("error") or ""

    cleaned_outputs = dict(outputs)
    for key in ("promotion_report", "chat_reply", "assistant_message", "updated_report", "revised_report", "text", "answer", "result"):
        if key in cleaned_outputs:
            cleaned_outputs[key] = _strip_model_private_thought(cleaned_outputs[key])
    return {
        "workflow_run_id": body.get("workflow_run_id") or (data or {}).get("id") or "",
        "task_id": body.get("task_id") or (data or {}).get("task_id") or "",
        "status": (data or {}).get("status") or body.get("status") or "unknown",
        "error": error,
        "promotion_report": promotion_report,
        "chat_reply": cleaned_outputs.get("chat_reply") or cleaned_outputs.get("assistant_message") or "",
        "updated_report": cleaned_outputs.get("updated_report") or cleaned_outputs.get("revised_report") or "",
        "position_profile_raw": outputs.get("position_profile_raw") or "",
        "candidate_pool_raw": outputs.get("candidate_pool_raw") or "",
        "outputs": cleaned_outputs,
        "raw": body,
    }


def _get_promotion_dify_settings():
    base_url = _clean_base_url(_get_setting("DIFY_BASE_URL", "http://127.0.0.1"))
    api_key = (_get_setting("DIFY_PROMOTION_API_KEY") or "").strip()

    # Fallback to local_settings.py if .env fails
    if not api_key:
        try:
            from backend.local_settings import (
                DIFY_PROMOTION_API_KEY as LOCAL_PROMOTION_KEY,
            )
            api_key = (LOCAL_PROMOTION_KEY or "").strip()
        except ImportError:
            pass

    return {
        "base_url": base_url,
        "api_key": api_key,
        "workflow_url": f"{base_url}/v1/workflows/run",
    }


def _call_dify_workflow(settings, inputs, user="admin"):
    if not settings["api_key"]:
        raise RuntimeError("Dify API Key is not configured")

    payload = _json.dumps(
        {
            "inputs": inputs,
            "response_mode": "blocking",
            "user": user,
        },
        ensure_ascii=False,
    ).encode("utf-8")

    req = Request(
        settings["workflow_url"],
        data=payload,
        headers={
            "Authorization": f"Bearer {settings['api_key']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urlopen(req, timeout=300) as resp:
        body = _json.loads(resp.read().decode("utf-8"))

    return _normalize_succession_workflow_response(body)


DIFY_MANAGER_COMMENT_LIMIT = 3800
PROMOTION_CONTEXT_LIMIT = 900
PROMOTION_CHAT_ITEM_LIMIT = 360
PROMOTION_REPORT_LIMIT = 12000
PROMOTION_QUESTION_LIMIT = 1200
def _clip_text(value, limit):
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n（内容过长，已截断）"


def _compact_chat_content(value):
    return _clip_text(" ".join(str(value or "").split()), PROMOTION_CHAT_ITEM_LIMIT)


def _build_promotion_manager_comment(manager_comment, query="", context=""):
    parts = [
        _clip_text(manager_comment, 1800),
        f"本轮问题：{_clip_text(query, 500)}" if query else "",
        f"最近对话上下文：\n{_clip_text(context, PROMOTION_CONTEXT_LIMIT)}" if context else "",
    ]
    text = "\n\n".join(part for part in parts if part)
    return _clip_text(text, DIFY_MANAGER_COMMENT_LIMIT)


def _split_promotion_chat_package(text):
    raw = _strip_model_private_thought(text)
    if not raw:
        return "", "", ""
    thinking_match = re.search(r"THINKING_SUMMARY:\s*(.*?)(?:\nCHAT_REPLY:|\nUPDATED_REPORT:|\Z)", raw, re.S)
    reply_match = re.search(r"CHAT_REPLY:\s*(.*?)(?:\nUPDATED_REPORT:|\Z)", raw, re.S)
    report_match = re.search(r"UPDATED_REPORT:\s*(.*)\Z", raw, re.S)
    thinking = thinking_match.group(1).strip() if thinking_match else ""
    fallback = re.sub(r"THINKING_SUMMARY:\s*.*?(?:\nCHAT_REPLY:|\Z)", "", raw, flags=re.S)
    fallback = re.sub(r"UPDATED_REPORT:\s*.*\Z", "", fallback, flags=re.S).strip()
    reply = reply_match.group(1).strip() if reply_match else fallback
    report = report_match.group(1).strip() if report_match else ""
    return thinking, reply, report


def _build_promotion_inputs(data, conversation_context=""):
    mode = (data.get("mode") or "generate").strip().lower()
    if mode not in {"generate", "chat"}:
        mode = "chat" if (data.get("followup_question") or data.get("query")) else "generate"

    target_position = (data.get("target_position") or "").strip()
    promotion_rule = (data.get("promotion_rule") or "").strip()
    manager_comment = (data.get("manager_comment") or "").strip()
    created_by = (data.get("created_by") or "HR").strip() or "HR"
    followup_question = (data.get("followup_question") or data.get("query") or "").strip()
    current_report = (data.get("current_report") or "").strip()

    inputs = {
        "mode": mode,
        "target_position": target_position,
        "promotion_rule": promotion_rule,
        "manager_comment": _clip_text(manager_comment, 2400),
        "created_by": created_by,
        "current_report": _clip_text(current_report, PROMOTION_REPORT_LIMIT),
        "followup_question": _clip_text(followup_question, PROMOTION_QUESTION_LIMIT),
        "conversation_context": _clip_text(conversation_context, PROMOTION_CONTEXT_LIMIT),
    }
    return mode, created_by, inputs


def _get_promotion_session(conversation_id, target_position=""):
    session = promotion_agent_sessions.get(conversation_id)
    if not isinstance(session, dict):
        session = {"messages": [], "current_report": "", "target_position": target_position or ""}
        promotion_agent_sessions[conversation_id] = session
    session.setdefault("messages", [])
    session.setdefault("current_report", "")
    session.setdefault("target_position", target_position or "")
    return session

def _call_succession_workflow(inputs, user="admin"):
    return _call_dify_workflow(_get_succession_dify_settings(), inputs, user)


def _call_promotion_workflow(inputs, user="admin"):
    return _call_dify_workflow(_get_promotion_dify_settings(), inputs, user)

def cleanup_expired_sessions():
    """清理超过5分钟的过期session"""
    now = time.time()
    expired = [k for k, v in qrcode_sessions.items() if now - v["created_at"] > 300]
    for k in expired:
        del qrcode_sessions[k]


@app.route("/")
def home():
    return "Flask 后端服务运行中"


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "service": "flask-backend"})


@app.get("/api/hello")
def hello():
    return jsonify({"message": "Hello from Flask API"})


@app.get("/api/overview")
def overview():
    return jsonify(get_overview())


@app.get("/api/nine-box")
def nine_box():
    return jsonify(get_nine_box())


@app.get("/api/succession")
def succession():
    return jsonify(get_succession_candidates())


@app.get("/api/risks")
def risks():
    return jsonify(get_risk_alerts())


@app.get("/api/risk-overview")
def risk_overview():
    return jsonify(get_risk_overview())


@app.get("/api/risk-employees")
def risk_employees():
    level = request.args.get("level")
    keyword = request.args.get("keyword")
    page = request.args.get("page", 1)
    page_size = request.args.get("pageSize", 10)
    return jsonify(
        get_risk_employees(
            level=level,
            keyword=keyword,
            page=page,
            page_size=page_size,
        )
    )


@app.get("/api/risk-employees/<employee_id>")
def risk_employee_detail(employee_id):
    result = get_risk_employee_detail(employee_id)
    if result is None:
        return jsonify({"error": "未找到该员工"}), 404
    return jsonify(result)


@app.get("/api/risk-settings")
def risk_settings():
    return jsonify(get_risk_settings())


@app.post("/api/risk-settings")
def update_risk_settings_api():
    data = request.get_json() or {}
    high = data.get("highRiskThreshold", 70)
    medium = data.get("mediumRiskThreshold", 40)
    return jsonify(update_risk_settings(high, medium))


@app.post("/api/risk-employees/<employee_id>/note")
def update_risk_employee_note(employee_id):
    data = request.get_json() or {}
    note = data.get("note", "")
    author = data.get("author", "????")
    return jsonify(update_employee_note(employee_id, note, author=author))


@app.get("/api/risk-employees/<employee_id>/follow-ups")
def risk_employee_follow_ups(employee_id):
    return jsonify({"items": get_follow_ups(employee_id)})


@app.post("/api/risk-employees/<employee_id>/follow-ups")
def create_risk_employee_follow_up(employee_id):
    data = request.get_json() or {}
    record = add_follow_up(
        employee_id,
        status=data.get("status", "???"),
        note=data.get("note", ""),
        owner=data.get("owner", ""),
        follow_up_date=data.get("followUpDate", ""),
        next_action=data.get("nextAction", ""),
    )
    return jsonify(record), 201
@app.get("/api/succession/candidates")
def succession_candidates_list():
    """Filter succession candidates by position or employee name."""
    position = request.args.get("position", "").strip()
    candidate = request.args.get("candidate", "").strip()
    data = get_succession_candidates_filtered(
        position if position else None,
        candidate if candidate else None,
    )
    return jsonify(data)


@app.get("/api/succession/positions")
def succession_positions():
    """Get position_profile.position_name values for the workflow selector."""
    return jsonify(get_position_profile_names())


@app.post("/api/succession/workflow")
def succession_workflow():
    """Call the promotion decision Dify workflow."""
    data = request.get_json() or {}
    target_position = data.get("target_position", "").strip()
    target_position_name = data.get("target_position_name", "").strip()
    target_position_level = data.get("target_position_level", "").strip()
    target_department = data.get("target_department", "").strip()
    promotion_rule = data.get("promotion_rule", "").strip()
    manager_comment = data.get("manager_comment", "").strip()
    created_by = data.get("created_by", "HR").strip() or "HR"

    if not target_position and not target_position_name:
        return jsonify({"error": "请填写目标岗位名称"}), 400

    inputs = {
        "target_position": target_position or target_position_name,
        "target_position_name": target_position_name or target_position,
        "target_position_level": target_position_level,
        "target_department": target_department,
        "bumen": target_department,
        "cengji": target_position_level,
        "gangwei": target_position_name or target_position,
        "promotion_rule": promotion_rule,
        "manager_comment": manager_comment,
        "created_by": created_by,
    }

    try:
        result = _call_succession_workflow(inputs, user=created_by)
        return jsonify(result)
    except HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8", errors="replace")
        except Exception:
            detail = str(exc)
        return jsonify({"error": f"Dify workflow request failed: {detail or str(exc)}"}), 502
    except URLError as exc:
        return jsonify({"error": f"Dify workflow network error: {str(exc)}"}), 502
    except Exception as exc:
        return jsonify({"error": f"Dify workflow request failed: {str(exc)}"}), 502



@app.get("/api/departments")
def departments_list():
    return jsonify(get_departments())


@app.get("/api/promotion-agent/positions")
def promotion_agent_positions():
    """Position names for the standalone promotion decision assistant."""
    return jsonify(get_position_profile_names())


@app.post("/api/promotion-agent/workflow")
def promotion_agent_workflow():
    """Blocking call for the standalone promotion decision assistant."""
    data = request.get_json() or {}
    conversation_context = (data.get("conversation_context") or "").strip()
    mode, created_by, inputs = _build_promotion_inputs(data, conversation_context=conversation_context)

    if not inputs["target_position"]:
        return jsonify({"error": "Please fill in target_position"}), 400
    if mode == "chat" and not inputs["followup_question"]:
        return jsonify({"error": "请填写追问内容"}), 400

    try:
        result = _call_promotion_workflow(inputs, user=created_by)
        package_source = result.get("chat_reply") or result.get("promotion_report") or ""
        parsed_thinking, parsed_reply, parsed_report = _split_promotion_chat_package(package_source)
        if parsed_thinking:
            result["thinking_summary"] = parsed_thinking
        if parsed_reply and parsed_reply != package_source:
            result["chat_reply"] = parsed_reply
        if parsed_report:
            result["updated_report"] = result.get("updated_report") or parsed_report
            result["promotion_report"] = parsed_report
        elif result.get("updated_report") and not result.get("promotion_report"):
            result["promotion_report"] = result["updated_report"]
        return jsonify(result)
    except HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8", errors="replace")
        except Exception:
            detail = str(exc)
        return jsonify({"error": f"Dify workflow request failed: {detail or str(exc)}"}), 502
    except URLError as exc:
        return jsonify({"error": f"Dify workflow network error: {str(exc)}"}), 502
    except Exception as exc:
        return jsonify({"error": f"Dify workflow request failed: {str(exc)}"}), 502


@app.post("/api/promotion-agent/chat/stream")
@app.post("/api/promotion-agent/stream")
def promotion_agent_stream():
    """SSE wrapper for the standalone promotion decision assistant."""
    data = request.get_json() or {}
    conversation_id = (data.get("conversation_id") or "").strip() or uuid.uuid4().hex
    session = _get_promotion_session(conversation_id, (data.get("target_position") or "").strip())

    recent_context = (data.get("conversation_context") or "").strip()
    session_context = "\n".join(
        f"{'用户' if item.get('role') == 'user' else '助手'}: {_compact_chat_content(item.get('content', ''))}"
        for item in session["messages"][-8:]
    )
    merged_context = "\n".join(part for part in [_clip_text(recent_context, PROMOTION_CONTEXT_LIMIT), session_context] if part)
    data["conversation_context"] = merged_context

    mode, created_by, inputs = _build_promotion_inputs(data, conversation_context=merged_context)
    if not inputs["target_position"]:
        inputs["target_position"] = session.get("target_position", "")
    if not inputs["target_position"]:
        return jsonify({"error": "Please fill in target_position"}), 400
    if mode == "chat" and not inputs["followup_question"]:
        return jsonify({"error": "请填写追问内容"}), 400

    session["target_position"] = inputs["target_position"]
    if inputs.get("current_report"):
        session["current_report"] = inputs["current_report"]
    elif session.get("current_report") and mode == "chat":
        inputs["current_report"] = session["current_report"]

    def sse(event, payload):
        return f"event: {event}\ndata: {_json.dumps(payload, ensure_ascii=False)}\n\n"

    def stream_text(text, chunk_size=18):
        content = str(text or "")
        for index in range(0, len(content), chunk_size):
            yield sse("delta", {"delta": content[index:index + chunk_size]})

    def generate():
        run_started_at = time.time()
        yield sse("session", {"conversation_id": conversation_id})

        if mode == "generate":
            yield sse("status", {"message": "已接收生成请求，正在生成晋升正文..."})
        else:
            yield sse("status", {"message": "已接收追问，正在判断是否需要查询数据库..."})
        settings = _get_promotion_dify_settings()

        if not settings["api_key"]:
            yield sse("error", {"error": "DIFY_PROMOTION_API_KEY is not configured in local .env"})
            return

        payload = _json.dumps({"inputs": inputs, "response_mode": "streaming", "user": created_by}, ensure_ascii=False).encode("utf-8")
        req = Request(settings["workflow_url"], data=payload, headers={"Authorization": f"Bearer {settings['api_key']}", "Content-Type": "application/json"}, method="POST")

        final_body = None
        streamed_any_text = False
        try:
            with urlopen(req, timeout=300) as resp:
                for raw_line in resp:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line.startswith("data:"):
                        continue
                    raw_data = line[5:].strip()
                    if raw_data == "[DONE]":
                        break
                    try:
                        chunk = _json.loads(raw_data)
                    except Exception:
                        continue
                    event_name = chunk.get("event") or "message"
                    if event_name == "workflow_started":
                        yield sse("status", {"message": "工作流已启动，正在处理请求..."})
                    elif event_name in {"node_started", "node_finished"}:
                        title = (chunk.get("data") or {}).get("title") or "分析节点"
                        yield sse("status", {"message": title})
                    elif event_name in {"text_chunk", "message"}:
                        text_delta = chunk.get("answer") or chunk.get("text") or chunk.get("delta") or ""
                        if text_delta:
                            streamed_any_text = True
                            yield sse("delta", {"delta": text_delta})
                    elif event_name == "workflow_finished":
                        final_body = chunk

            result = _normalize_succession_workflow_response(final_body or {})
            if mode == "generate":
                report = result.get("promotion_report") or ""
                if report:
                    session["current_report"] = report
                if report and not streamed_any_text:
                    yield from stream_text(report, chunk_size=28)
                    streamed_any_text = True
                session["messages"].append({"role": "assistant", "content": _compact_chat_content(report or "已生成晋升正文")})
                yield sse("status", {"message": "生成完成，正文已更新"})
            else:
                package_text = result.get("chat_reply") or result.get("promotion_report") or ""
                thinking_summary, reply, updated_report = _split_promotion_chat_package(package_text)
                if thinking_summary:
                    result["thinking_summary"] = thinking_summary
                if reply:
                    result["chat_reply"] = reply
                if updated_report:
                    result["updated_report"] = updated_report
                    result["promotion_report"] = result.get("promotion_report") or updated_report
                    session["current_report"] = updated_report
                elif result.get("updated_report"):
                    session["current_report"] = result["updated_report"]
                if package_text and not streamed_any_text:
                    yield from stream_text(package_text, chunk_size=18)
                    streamed_any_text = True
                session["messages"].append({"role": "assistant", "content": _compact_chat_content(reply or result.get("promotion_report") or "已完成本轮追问")})
                yield sse("status", {"message": "本轮追问完成"})

            if mode == "generate" and result.get("promotion_report"):
                result["updated_report"] = result.get("updated_report") or result["promotion_report"]
            result["elapsed_ms"] = int((time.time() - run_started_at) * 1000)
            result["tool_usage"] = {
                "database": bool(result.get("position_profile_raw") or result.get("candidate_pool_raw")),
                "revise_report": bool(result.get("updated_report") and mode == "chat"),
                "ask_user": False,
            }
            yield sse("done", result)
        except HTTPError as exc:
            try:
                detail = exc.read().decode("utf-8", errors="replace")
            except Exception:
                detail = str(exc)
            yield sse("error", {"error": f"Dify workflow request failed: {detail or str(exc)}"})
        except URLError as exc:
            yield sse("error", {"error": f"Dify workflow network error: {str(exc)}"})
        except Exception as exc:
            yield sse("error", {"error": f"Dify workflow request failed: {str(exc)}"})

    return Response(stream_with_context(generate()), mimetype="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/training-plans")
def training_plans():
    return jsonify(get_training_plans())


@app.get("/api/potential")
def potential_list():
    return jsonify(get_potential_list())


@app.get("/api/potential/<employee_id>")
def potential_by_id(employee_id):
    result = get_potential_by_id(employee_id)
    if result is None:
        return jsonify({"error": "未找到该员工"}), 404
    return jsonify(result)


@app.post("/api/potential-assessment/save")
def create_potential_assessment():
    """保存一条评估记录"""
    data = request.get_json()
    if not data or "employee_id" not in data:
        return jsonify({"error": "缺少 employee_id"}), 400

    ok = save_potential_assessment(
        employee_id=data["employee_id"],
        name=data.get("name", ""),
        assessment_detail=data.get("assessment_detail"),
    )
    if ok:
        return jsonify({"success": True, "message": "评估记录已保存"})
    return jsonify({"error": "保存失败"}), 500


@app.get("/api/potential/<employee_id>/assessments")
def potential_assessment_history(employee_id):
    """获取某员工的评估历史"""
    records = get_potential_assessment_history(employee_id)
    return jsonify(records)


@app.get("/api/potential-assessments/all")
def all_potential_assessments():
    """获取所有评估记录"""
    records = get_all_assessment_records()
    return jsonify(records)


@app.get("/api/position-risks")
def position_risks():
    """岗位风险研判列表"""
    try:
        data = get_position_risk_list()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.get("/api/employee-risks")
def employee_risks():
    """员工流失风险列表"""
    try:
        data = get_employee_risk_list()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.get("/api/employees/<employee_no>")
def employee_query(employee_no):
    result = get_employee_by_no(employee_no)
    if result is None:
        return jsonify({"error": "未找到该员工"}), 404
    return jsonify(result)


# ── 二维码登录 API ──────────────────────────────────────

@app.post("/api/auth/qrcode")
def auth_qrcode():
    """生成二维码登录令牌"""
    cleanup_expired_sessions()
    token = uuid.uuid4().hex[:16]
    qrcode_sessions[token] = {
        "status": "pending",
        "created_at": time.time(),
    }
    return jsonify({"token": token})


@app.get("/api/auth/status/<token>")
def auth_status(token):
    """轮询二维码状态：pending / scanned / confirmed"""
    session = qrcode_sessions.get(token)
    if not session:
        return jsonify({"status": "expired"})
    now = time.time()
    if now - session["created_at"] > 300:
        del qrcode_sessions[token]
        return jsonify({"status": "expired"})
    return jsonify({"status": session["status"]})


@app.post("/api/auth/scan/<token>")
def auth_scan(token):
    """模拟手机扫码（将二维码标记为已扫描）"""
    session = qrcode_sessions.get(token)
    if not session:
        return jsonify({"error": "二维码已过期"}), 404
    if session["status"] != "pending":
        return jsonify({"error": "二维码已被处理"}), 400
    session["status"] = "scanned"
    return jsonify({"status": "scanned", "message": "扫码成功，请在手机上确认登录"})


@app.post("/api/auth/confirm/<token>")
def auth_confirm(token):
    """模拟手机确认登录"""
    session = qrcode_sessions.get(token)
    if not session:
        return jsonify({"error": "二维码已过期"}), 404
    if session["status"] != "scanned":
        return jsonify({"error": "请先扫码"}), 400
    session["status"] = "confirmed"
    return jsonify({"status": "confirmed", "message": "登录成功"})


@app.post("/api/auth/logout")
def auth_logout():
    """退出登录"""
    return jsonify({"status": "ok", "message": "已退出登录"})


# ── 微信扫码登录 API ────────────────────────────────────


# Dify AI 智能体配置（本地部署）
DIFY_API_URL = "http://127.0.0.1/v1/chat-messages"
DIFY_APP_ID = "app-13oLzUizeaNgxlBqh913Hu9g"

# 培训智能体配置
TRAINING_AGENT_ID = "app-i76mFs84OFgh5PXW2flJ9UXi"

# 工作流 API 端点（Workflow 模式使用独立的 endpoint）
WORKFLOW_API_URL = "http://127.0.0.1/v1/workflows/run"

# 继任计划工作流配置
SUCCESSION_AGENT_ID = "app-ws17cPnRGZMVvFQZoHZMgPIl"

# 干预方案生成 Agent
INTERVENTION_AGENT_ID = "app-9Q1j8ibjjf2l1U0dU39QYF34"


@app.post("/api/ai/chat")
def ai_chat():
    """代理前端请求到 Dify AI 智能体（Agent 模式需 streaming）"""
    data = request.get_json()
    if not data or "query" not in data:
        return jsonify({"error": "缺少 query 参数"}), 400

    payload = _json.dumps({
        "inputs": data.get("inputs", {}),
        "query": data["query"],
        "response_mode": "streaming",
        "conversation_id": data.get("conversation_id", ""),
        "user": data.get("user", "admin"),
    }).encode("utf-8")

    try:
        req = Request(
            DIFY_API_URL,
            data=payload,
            headers={
                "Authorization": f"Bearer {DIFY_APP_ID}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(req, timeout=60) as resp:
            # 读取 streaming 响应，逐行聚合 answer
            full_answer = ""
            conv_id = ""
            for line in resp:
                line = line.decode("utf-8").strip()
                if line.startswith("data: "):
                    try:
                        chunk = _json.loads(line[6:])
                        if "answer" in chunk:
                            full_answer += chunk["answer"]
                        if chunk.get("conversation_id"):
                            conv_id = chunk["conversation_id"]
                        if chunk.get("event") == "message_end":
                            break
                    except _json.JSONDecodeError:
                        continue
        return jsonify({
            "answer": full_answer,
            "conversation_id": conv_id,
        })
    except Exception as e:
        return jsonify({"error": f"AI 服务调用失败: {str(e)}"}), 502


@app.get("/api/dify/status")
def dify_status():
    settings = get_dify_settings()
    return jsonify(
        {
            "baseUrl": settings["base_url"],
            "workflowUrl": settings["workflow_url"],
            "configured": bool(settings["api_key"]),
        }
    )


@app.post("/api/risk-intervention")
def risk_intervention():
    data = request.get_json() or {}
    employee_input = data.get("employeeInput") or data.get("employee_input")

    if not employee_input:
        return jsonify({"error": "缺少 employeeInput"}), 400

    if isinstance(employee_input, dict):
        employee_input = _json.dumps(employee_input, ensure_ascii=False)

    workflow_inputs = {
        "employee_input": employee_input,
        "analysis_mode": data.get("analysisMode", "single"),
        "high_risk_threshold": str(data.get("highRiskThreshold", 70)),
        "medium_risk_threshold": str(data.get("mediumRiskThreshold", 40)),
    }

    try:
        result = run_workflow(
            workflow_inputs,
            user=data.get("user", "risk-module"),
            response_mode="blocking",
        )
        return jsonify(
            {
                "answer": result["text"],
                "status": result["status"],
                "workflow_run_id": result["workflow_run_id"],
                "task_id": result["task_id"],
                "outputs": result["outputs"],
            }
        )
    except HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8")
        except Exception:
            detail = str(exc)
        return jsonify({"error": f"Dify 调用失败：{detail}"}), 502
    except Exception as exc:
        return jsonify({"error": f"Dify 调用失败：{str(exc)}"}), 502


@app.get("/api/auth/wechat/url")
def wechat_auth_url():
    """返回微信扫码登录的授权URL（前端弹窗使用）"""
    state = uuid.uuid4().hex
    # 当前服务器地址作为回调
    callback = quote(f"{request.host_url.rstrip('/')}/api/auth/wechat/callback")
    auth_url = (
        f"{WECHAT_QR_URL}"
        f"?appid={WECHAT_APP_ID}"
        f"&redirect_uri={callback}"
        f"&response_type=code"
        f"&scope=snsapi_login"
        f"&state={state}"
        f"#wechat_redirect"
    )
    return jsonify({"url": auth_url, "state": state})
@app.post("/api/ai/training-chat")
def training_ai_chat():
    """培训智能体对话（使用独立的培训 Agent）"""
    data = request.get_json()
    if not data or "query" not in data:
        return jsonify({"error": "缺少 query 参数"}), 400

    payload = _json.dumps({
        "inputs": data.get("inputs", {}),
        "query": data["query"],
        "response_mode": "streaming",
        "conversation_id": data.get("conversation_id", ""),
        "user": data.get("user", "admin"),
    }).encode("utf-8")

    try:
        req = Request(
            DIFY_API_URL,
            data=payload,
            headers={
                "Authorization": f"Bearer {TRAINING_AGENT_ID}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(req, timeout=60) as resp:
            full_answer = ""
            conv_id = ""
            for line in resp:
                line = line.decode("utf-8").strip()
                if line.startswith("data: "):
                    try:
                        chunk = _json.loads(line[6:])
                        if "answer" in chunk:
                            full_answer += chunk["answer"]
                        if chunk.get("conversation_id"):
                            conv_id = chunk["conversation_id"]
                        if chunk.get("event") == "message_end":
                            break
                    except _json.JSONDecodeError:
                        continue
        return jsonify({
            "answer": full_answer,
            "conversation_id": conv_id,
        })
    except Exception as e:
        return jsonify({"error": f"培训智能体调用失败: {str(e)}"}), 502


# ── 培训计划 CRUD API ──────────────────────────────────
@app.get("/api/training/list")
def training_list():
    """获取培训计划列表"""
    try:
        data = get_training_list()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.post("/api/training/add")
def training_add():
    """添加培训计划"""
    data = request.get_json()
    if not data or not all(k in data for k in ("employee_id", "name", "training_plan")):
        return jsonify({"error": "缺少必填参数"}), 400
    ok = add_training(data["employee_id"], data["name"], data["training_plan"])
    if ok:
        return jsonify({"status": "ok", "message": "培训计划添加成功"})
    return jsonify({"error": "添加失败"}), 500
@app.post("/api/training/update-status")
def training_update_status():
    """更新培训完成状态"""
    data = request.get_json()
    if not data or not all(k in data for k in ("employee_id", "training_plan", "is_completed")):
        return jsonify({"error": "缺少必填参数"}), 400
    ok = update_training_status(data["employee_id"], data["training_plan"], data["is_completed"])
    if ok:
        return jsonify({"status": "ok", "message": "状态更新成功"})
    return jsonify({"error": "更新失败"}), 500
@app.post("/api/training/delete")
def training_delete():
    """删除培训计划"""
    data = request.get_json()
    if not data or not all(k in data for k in ("employee_id", "training_plan")):
        return jsonify({"error": "缺少必填参数"}), 400
    ok = delete_training(data["employee_id"], data["training_plan"])
    if ok:
        return jsonify({"status": "ok", "message": "培训计划已删除"})
    return jsonify({"error": "删除失败"}), 500


@app.get("/api/training/completed-abilities")
def training_completed_abilities():
    """获取能力表中员工已完成的培训"""
    data = get_completed_trainings_from_ability()
    return jsonify(data)


# ── 扫脸登录 API ───────────────────────────────────────


@app.post("/api/face/register")
def face_register():
    """扫脸注册：上传人脸照片（支持多帧），提取特征并存储"""
    data = request.get_json()
    if not data or "username" not in data:
        return jsonify({"error": "缺少必填参数: username"}), 400

    username = data["username"].strip()
    if not username:
        return jsonify({"error": "用户名不能为空"}), 400

    # 支持多帧（images 数组）和单帧（image）
    images = data.get("images", [])
    if not images and "image" in data:
        images = [data["image"]]
    if not images:
        return jsonify({"error": "缺少必填参数: image 或 images"}), 400

    import json
    from backend.db import query_one, execute

    # 检查用户名是否已存在
    existing = query_one(
        "SELECT id FROM face_users WHERE username = %s", (username,)
    )
    if existing:
        return jsonify({"error": "用户名已存在"}), 409

    # 对每帧提取特征，取平均值
    encodings = []
    errors = []
    for i, img_b64 in enumerate(images):
        enc, msg = get_face_encoding(img_b64)
        if enc is None:
            errors.append(f"第{i + 1}帧: {msg}")
        else:
            encodings.append(enc)

    if not encodings:
        detail = "；".join(errors) if errors else "特征提取失败"
        return jsonify({"error": f"所有帧均未检测到人脸。{detail}"}), 400

    # 多帧特征取平均
    import numpy as np
    avg_encoding = np.mean(encodings, axis=0).tolist()

    affected = execute(
        "INSERT INTO face_users (username, face_encoding) VALUES (%s, %s)",
        (username, json.dumps(avg_encoding)),
    )
    if affected:
        frames_used = f"（基于 {len(encodings)}/{len(images)} 帧）"
        return jsonify({"status": "ok", "message": f"人脸注册成功 {frames_used}"})
    return jsonify({"error": "注册失败"}), 500


@app.post("/api/face/login")
def face_login():
    """扫脸登录：上传人脸照片，与数据库中的特征进行比对"""
    data = request.get_json()
    if not data or "image" not in data:
        return jsonify({"error": "缺少必填参数: image"}), 400

    image_b64 = data["image"]
    encoding, msg = get_face_encoding(image_b64)
    if encoding is None:
        return jsonify({"error": msg}), 400

    # 从数据库获取所有用户的人脸特征
    from backend.db import query_all

    import json

    users = query_all("SELECT id, username, face_encoding FROM face_users")
    if not users:
        return jsonify({"error": "尚未注册任何用户，请先注册"}), 404

    best_match = None
    best_similarity = 0

    for user in users:
        known_encoding = json.loads(user["face_encoding"])
        match, similarity = compare_faces(known_encoding, encoding)
        if match and similarity > best_similarity:
            best_similarity = similarity
            best_match = user["username"]

    if best_match:
        return jsonify({
            "status": "ok",
            "message": "登录成功",
            "username": best_match,
            "similarity": round(best_similarity, 3),
        })
    else:
        return jsonify({"error": "人脸不匹配，请重试或使用其他方式登录"}), 401


@app.get("/api/face/users")
def face_users_list():
    """获取已注册的人脸用户列表（仅返回用户名）"""
    from backend.db import query_all

    users = query_all("SELECT id, username, created_at FROM face_users ORDER BY created_at DESC")
    return jsonify(users)


@app.post("/api/face/delete")
def face_user_delete():
    """删除指定人脸用户"""
    data = request.get_json()
    if not data or "username" not in data:
        return jsonify({"error": "缺少必填参数: username"}), 400

    from backend.db import execute

    affected = execute(
        "DELETE FROM face_users WHERE username = %s", (data["username"],)
    )
    if affected:
        return jsonify({"status": "ok", "message": "用户已删除"})
    return jsonify({"error": "用户不存在"}), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)











