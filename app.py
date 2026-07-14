import uuid
import time
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
import json as _json

from flask import Flask, jsonify, request, redirect
from flask_cors import CORS

from backend.wechat_config import (
    WECHAT_APP_ID,
    WECHAT_APP_SECRET,
    WECHAT_QR_URL,
    WECHAT_TOKEN_URL,
    WECHAT_USERINFO_URL,
    FRONTEND_SUCCESS_URL,
)

from backend.queries import (
    get_nine_box,
    get_overview,
    get_risk_alerts,
    get_succession_candidates,
    get_succession_candidates_filtered,
    get_departments,
    get_training_plans,
    get_employee_by_no,
    get_potential_list,
    get_potential_by_id,
    update_potential,
    get_training_list,
    add_training,
    update_training_status,
    delete_training,
    get_position_risk_list,
    get_employee_risk_list,
)

app = Flask(__name__)
CORS(app)

# ── 二维码登录 Session 存储 ─────────────────────────────
# token -> { "status": "pending"|"scanned"|"confirmed", "created_at": timestamp }
qrcode_sessions = {}


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


@app.get("/api/succession/candidates")
def succession_candidates_list():
    """按岗位名称/员工姓名筛选继任候选人"""
    position = request.args.get("position", "").strip()
    candidate = request.args.get("candidate", "").strip()
    data = get_succession_candidates_filtered(
        position if position else None,
        candidate if candidate else None,
    )
    return jsonify(data)


@app.get("/api/succession/departments")
def succession_departments():
    """获取部门列表"""
    return jsonify(get_departments())


@app.post("/api/succession/workflow")
def succession_workflow():
    """调用继任计划工作流（Dify）"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "缺少请求参数"}), 400

    department = data.get("department", "").strip()
    level = data.get("level", "").strip()
    position = data.get("position", "").strip()

    if not all([department, level, position]):
        return jsonify({"error": "请填写完整的岗位信息（部门、层级、岗位名称）"}), 400

    payload = _json.dumps({
        "inputs": {
            "bumen": department,
            "cengji": level,
            "gangwei": position,
        },
        "response_mode": "blocking",
        "user": "admin",
    }).encode("utf-8")

    try:
        req = Request(
            WORKFLOW_API_URL,
            data=payload,
            headers={
                "Authorization": f"Bearer {SUCCESSION_AGENT_ID}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(req, timeout=300) as resp:
            result = _json.loads(resp.read())
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"工作流调用失败: {str(e)}"}), 502


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
DIFY_API_URL = "http://192.168.125.130/v1/chat-messages"
DIFY_APP_ID = "app-13oLzUizeaNgxlBqh913Hu9g"

# 培训智能体配置
TRAINING_AGENT_ID = "app-i76mFs84OFgh5PXW2flJ9UXi"

# 工作流 API 端点（Workflow 模式使用独立的 endpoint）
WORKFLOW_API_URL = "http://192.168.125.130/v1/workflows/run"

# 继任计划工作流配置
SUCCESSION_AGENT_ID = "app-8dC5kB9slXrtnTDXBc67xM1u"


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


@app.route("/api/auth/wechat/callback")
def wechat_callback():
    """微信回调：用户扫码后微信302跳转到这里"""
    code = request.args.get("code")
    state = request.args.get("state")

    if not code:
        return "<h2>授权失败，缺少 code 参数</h2>"

    try:
        # 1. 用 code 换取 access_token
        token_params = urlencode({
            "appid": WECHAT_APP_ID,
            "secret": WECHAT_APP_SECRET,
            "code": code,
            "grant_type": "authorization_code",
        })
        req = Request(f"{WECHAT_TOKEN_URL}?{token_params}")
        with urlopen(req, timeout=10) as resp:
            token_data = _json.loads(resp.read())

        if "errcode" in token_data:
            return f"<h2>微信登录失败: {token_data.get('errmsg', '未知错误')}</h2>"

        access_token = token_data["access_token"]
        openid = token_data["openid"]

        # 2. 获取用户信息
        user_params = urlencode({
            "access_token": access_token,
            "openid": openid,
        })
        req2 = Request(f"{WECHAT_USERINFO_URL}?{user_params}")
        with urlopen(req2, timeout=10) as resp2:
            user_info = _json.loads(resp2.read())

        # 3. 创建登录 session
        session_token = uuid.uuid4().hex[:16]
        qrcode_sessions[session_token] = {
            "status": "confirmed",
            "created_at": time.time(),
            "user": {
                "openid": openid,
                "nickname": user_info.get("nickname", "微信用户"),
                "avatar": user_info.get("headimgurl", ""),
            },
        }

        # 4. 302 跳回前端，附带 session_token
        return redirect(f"{FRONTEND_SUCCESS_URL}?token={session_token}")

    except Exception as e:
        return f"<h2>微信登录异常: {str(e)}</h2>"


@app.get("/api/auth/wechat/user/<token>")
def wechat_user_info(token):
    """前端轮询：获取登录后的用户信息"""
    session = qrcode_sessions.get(token)
    if not session or session["status"] != "confirmed":
        return jsonify({"error": "未登录或已过期"}), 401
    now = time.time()
    if now - session["created_at"] > 86400:
        del qrcode_sessions[token]
        return jsonify({"error": "会话已过期"}), 401
    return jsonify({
        "status": "confirmed",
        "user": session.get("user", {}),
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)