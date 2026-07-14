"""Database queries for the current talent pipeline schema."""

from datetime import date
import re

from backend.db import execute, query_all, query_one
from backend.risk_module_store import get_employee_note, get_follow_ups, get_risk_settings


KEY_JOB_LEVELS = {"经理层", "总监层", "高管层", "决策层"}
HIGH_VALUE_TAGS = ("核心骨干", "储备人才")


def _safe_float(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _safe_int(value, default=0):
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def _split_text(value):
    if not value:
        return []
    return [item.strip() for item in re.split(r"[、,，;；/|\s]+", str(value)) if item.strip()]


def _compute_nine_grid(performance_score, potential_score):
    if performance_score >= 4.5:
        perf_level = "高绩效"
    elif performance_score >= 3.0:
        perf_level = "中绩效"
    else:
        perf_level = "低绩效"

    if potential_score >= 80:
        pot_level = "高潜"
    elif potential_score >= 60:
        pot_level = "中潜"
    else:
        pot_level = "低潜"

    return f"{pot_level}-{perf_level}"


def _normalize_risk_level(raw_level, raw_score, thresholds=None):
    score = _safe_float(raw_score)
    thresholds = thresholds or get_risk_settings()
    high_threshold = _safe_float(thresholds.get("highRiskThreshold"), 70)
    medium_threshold = _safe_float(thresholds.get("mediumRiskThreshold"), 40)

    if score >= high_threshold:
        return "高风险"
    if score >= medium_threshold:
        return "中风险"
    if score > 0:
        return "低风险"

    text = str(raw_level or "").strip()
    if "高" in text:
        return "高风险"
    if "中" in text:
        return "中风险"
    if "低" in text:
        return "低风险"
    return "低风险"


def _normalize_position_risk_level(raw_level, raw_score):
    text = str(raw_level or "").strip()
    if "高" in text:
        return "高"
    if "中" in text:
        return "中"
    if "低" in text:
        return "低"

    score = _safe_float(raw_score)
    if score >= 60:
        return "高"
    if score >= 40:
        return "中"
    return "低"


def _format_succession_level(raw_level):
    text = str(raw_level or "").strip()
    mapping = {
        "1": "即刻可继任",
        "2": "1-2年可继任",
        "3": "2-3年可继任",
        "ready now": "即刻可继任",
        "ready_now": "即刻可继任",
        "ready": "即刻可继任",
    }
    return mapping.get(text.lower(), text or "暂无")


def _load_position_risk_map():
    try:
        rows = query_all(
            """
            SELECT position_name, total_risk_score, risk_level
            FROM position_risk
            """
        )
    except Exception:
        return {}

    result = {}
    for row in rows:
        position_name = str(row.get("position_name") or "").strip()
        if not position_name:
            continue
        result[position_name] = {
            "positionRiskScore": _safe_float(row.get("total_risk_score")),
            "positionRiskLevel": _normalize_position_risk_level(
                row.get("risk_level"), row.get("total_risk_score")
            ),
        }
    return result


def _load_position_profile_map():
    try:
        rows = query_all("SELECT * FROM position_profile")
    except Exception:
        return {}

    result = {}
    for row in rows:
        position_name = str(row.get("position_name") or "").strip()
        if position_name:
            result[position_name] = row
    return result


def _load_succession_map():
    try:
        rows = query_all(
            """
            SELECT
                candidate_employee_id,
                employee_name,
                department,
                target_position,
                match_score,
                succession_level
            FROM succession_candidates
            ORDER BY match_score DESC
            """
        )
    except Exception:
        return {}

    result = {}
    for row in rows:
        employee_id = str(row.get("candidate_employee_id") or "").strip()
        if not employee_id:
            continue
        current = result.get(employee_id)
        if current is None or _safe_float(row.get("match_score")) > _safe_float(current.get("match_score")):
            result[employee_id] = row
    return result


def _load_employee_ability_map():
    try:
        rows = query_all(
            """
            SELECT employee_id, skill_tags, training_completed
            FROM employee_ability
            """
        )
    except Exception:
        return {}

    result = {}
    for row in rows:
        employee_id = str(row.get("employee_id") or "").strip()
        if employee_id:
            result[employee_id] = row
    return result


def _load_employee_potential_map():
    try:
        rows = query_all(
            """
            SELECT employee_id, potential_score, potential_level, talent_tag
            FROM employee_potential
            """
        )
    except Exception:
        return {}

    result = {}
    for row in rows:
        employee_id = str(row.get("employee_id") or "").strip()
        if employee_id:
            result[employee_id] = row
    return result


def _load_table_columns(table_name):
    try:
        rows = query_all(f"SHOW COLUMNS FROM {table_name}")
    except Exception:
        return set()
    return {str(row.get("Field") or "").strip() for row in rows}


def _log_risk_error(stage, exc):
    print(f"[risk-module] {stage} failed: {exc.__class__.__name__}: {exc}")


def _fetch_risk_employee_rows(employee_id=None):
    columns = _load_table_columns("employee_talent_data")
    select_specs = [
        ("employee_id", "employee_id", "''"),
        ("name", "name", "''"),
        ("age", "age", "NULL"),
        ("gender", "gender", "''"),
        ("position_name", "position_name", "''"),
        ("job_level", "job_level", "''"),
        ("rank_name", "rank_name", "''"),
        ("department", "department", "''"),
        ("performance_score", "performance_score", "0"),
        ("tenure_years", "tenure_years", "0"),
        ("base_salary", "base_salary", "0"),
        ("compensation_factor", "compensation_factor", "1"),
        ("attrition_risk_score", "attrition_risk_score", "0"),
        ("attrition_risk", "attrition_risk", "NULL"),
        ("work_mode", "work_mode", "''"),
        ("manager_id", "manager_id", "NULL"),
    ]

    select_parts = []
    for field_name, alias, fallback in select_specs:
        if field_name in columns:
            select_parts.append(f"{field_name} AS {alias}")
        else:
            select_parts.append(f"{fallback} AS {alias}")

    sql = f"""
        SELECT
            {", ".join(select_parts)}
        FROM employee_talent_data
    """
    params = ()
    if employee_id:
        sql += " WHERE employee_id = %s"
        params = (employee_id,)
    else:
        if "attrition_risk_score" in columns and "attrition_risk" in columns:
            sql += """
                WHERE attrition_risk IS NOT NULL
                   OR attrition_risk_score IS NOT NULL
            """
        elif "attrition_risk_score" in columns:
            sql += """
                WHERE attrition_risk_score IS NOT NULL
            """
        elif "attrition_risk" in columns:
            sql += """
                WHERE attrition_risk IS NOT NULL
            """
    sql += " ORDER BY COALESCE(attrition_risk_score, 0) DESC, employee_id ASC"
    rows = query_all(sql, params)

    ability_map = _load_employee_ability_map()
    potential_map = _load_employee_potential_map()

    for row in rows:
        employee_key = str(row.get("employee_id") or "").strip()
        ability = ability_map.get(employee_key, {})
        potential = potential_map.get(employee_key, {})
        row["skill_tags"] = ability.get("skill_tags") or row.get("skill_tags") or ""
        row["training_completed"] = (
            ability.get("training_completed") or row.get("training_completed") or ""
        )
        row["potential_score"] = potential.get("potential_score") or row.get("potential_score") or 0
        row["potential_level"] = potential.get("potential_level") or row.get("potential_level") or ""
        row["talent_tag"] = potential.get("talent_tag") or row.get("talent_tag") or ""

    return rows


def _is_key_position(row, position_risk_info, position_profile):
    job_level = str(row.get("job_level") or "").strip()
    if job_level in KEY_JOB_LEVELS:
        return True

    if (position_risk_info or {}).get("positionRiskLevel") == "高":
        return True

    is_manager = str((position_profile or {}).get("is_manager") or "").strip()
    return is_manager == "是"


def _compute_priority_level(row, risk_level, position_risk_info, position_profile, succession_info):
    if risk_level == "高风险":
        return "high"

    talent_tag = str(row.get("talent_tag") or "").strip()
    potential_level = str(row.get("potential_level") or "").strip()

    high_value = any(tag in talent_tag for tag in HIGH_VALUE_TAGS) or "A" in potential_level or "S" in potential_level
    key_position = _is_key_position(row, position_risk_info, position_profile)
    has_succession_role = succession_info is not None

    if risk_level == "中风险" and (high_value or key_position or has_succession_role):
        return "high"
    return "normal"


def _build_risk_reason(row, position_risk_info):
    reasons = []

    risk_score = _safe_float(row.get("attrition_risk_score"))
    performance_score = _safe_float(row.get("performance_score"))
    tenure_years = _safe_float(row.get("tenure_years"))
    compensation_factor = _safe_float(row.get("compensation_factor"))
    training_completed = _split_text(row.get("training_completed"))
    talent_tag = str(row.get("talent_tag") or "").strip()
    potential_level = str(row.get("potential_level") or "").strip()
    work_mode = str(row.get("work_mode") or "").strip()

    if risk_score >= 60:
        reasons.append("离职风险评分偏高")
    if performance_score and performance_score <= 2:
        reasons.append("近期绩效偏低")
    if 0 < tenure_years < 3:
        reasons.append("司龄较短，稳定性待观察")
    if compensation_factor and compensation_factor < 0.95:
        reasons.append("薪酬竞争力偏弱")
    if not training_completed:
        reasons.append("培训发展支持不足")
    if "远程" in work_mode:
        reasons.append("远程办公需额外关注归属感")
    if "待优化" in talent_tag:
        reasons.append("当前人才标签提示需要重点关注")
    if "C" in potential_level:
        reasons.append("潜力等级偏低，发展信心可能不足")
    if (position_risk_info or {}).get("positionRiskLevel") == "高":
        reasons.append("所在岗位替补难度较高")

    if not reasons:
        reasons.append("存在流失倾向，建议结合直属经理反馈进一步核实")

    return reasons


def _build_risk_actions(row, risk_level, priority_level, position_risk_info, position_profile, succession_info):
    actions = []

    compensation_factor = _safe_float(row.get("compensation_factor"))
    training_completed = _split_text(row.get("training_completed"))
    required_training = _split_text((position_profile or {}).get("required_training"))
    missing_training = [item for item in required_training if item not in training_completed]

    if priority_level == "high":
        actions.append("3个工作日内安排HRBP和直属经理进行保留面谈")
    else:
        actions.append("纳入月度风险观察名单并持续跟踪")

    if compensation_factor and compensation_factor < 0.95:
        actions.append("评估薪酬竞争力与内部公平性，必要时提出调整建议")

    if missing_training:
        actions.append(f"补齐关键培训：{'、'.join(missing_training[:3])}")
    elif not training_completed:
        actions.append("补充职业发展与岗位能力类培训")

    if succession_info is not None:
        actions.append("同步继任计划负责人，评估该员工流失对梯队的影响")

    if (position_risk_info or {}).get("positionRiskLevel") == "高":
        actions.append("提前准备岗位替补和工作交接方案")

    if len(actions) < 2:
        actions.append("结合近期项目压力、团队氛围和个人诉求进行一对一沟通")

    return actions[:4]


def _build_employee_input_payload(row, risk_item, key_position, succession_info):
    return {
        "员工工号": row.get("employee_id"),
        "姓名": row.get("name"),
        "所属部门": row.get("department"),
        "岗位名称": row.get("position_name"),
        "职级层级": row.get("job_level"),
        "职级": row.get("rank_name"),
        "绩效评分": _safe_float(row.get("performance_score")),
        "司龄(年)": _safe_float(row.get("tenure_years")),
        "薪酬系数": _safe_float(row.get("compensation_factor")),
        "已完成培训": "、".join(_split_text(row.get("training_completed"))),
        "潜力评分": _safe_float(row.get("potential_score")),
        "潜力等级": row.get("potential_level"),
        "流失风险分": risk_item["riskScore"],
        "流失风险": risk_item["riskLevel"],
        "人才标签": row.get("talent_tag"),
        "办公方式": row.get("work_mode"),
        "是否关键岗位": "是" if key_position else "否",
        "是否继任候选": "是" if succession_info is not None else "否",
    }


def _build_intervention_context(row, risk_item, key_position, succession_info, required_training):
    candidate_text = "是" if succession_info is not None else "否"
    target_position = (succession_info or {}).get("target_position") or "无"

    return (
        f"员工姓名：{row.get('name') or row.get('employee_id')}\n"
        f"员工工号：{row.get('employee_id')}\n"
        f"所属部门：{row.get('department') or '未标注'}\n"
        f"岗位名称：{row.get('position_name') or '未标注'}\n"
        f"职级层级：{row.get('job_level') or '未标注'}\n"
        f"职级：{row.get('rank_name') or '未标注'}\n"
        f"绩效评分：{risk_item['performanceScore']}\n"
        f"潜力评分：{risk_item['potentialScore']}\n"
        f"潜力等级：{risk_item['potentialLevel'] or '未标注'}\n"
        f"流失风险分：{risk_item['riskScore']}\n"
        f"流失风险等级：{risk_item['riskLevel']}\n"
        f"干预优先级：{risk_item['priorityLevel']}\n"
        f"主要风险因素：{'、'.join(risk_item['reasonTags'])}\n"
        f"建议动作：{'；'.join(risk_item['recommendedActions'])}\n"
        f"是否关键岗位：{'是' if key_position else '否'}\n"
        f"是否继任候选：{candidate_text}\n"
        f"继任目标岗位：{target_position}\n"
        f"已完成培训：{'、'.join(_split_text(row.get('training_completed'))) or '无'}\n"
        f"岗位要求培训：{'、'.join(required_training) or '无'}"
    )


def _build_risk_item(row, position_risk_map, position_profile_map, succession_map, thresholds=None):
    position_name = str(row.get("position_name") or "").strip()
    employee_id = str(row.get("employee_id") or "").strip()

    position_risk_info = position_risk_map.get(position_name, {})
    position_profile = position_profile_map.get(position_name, {})
    succession_info = succession_map.get(employee_id)

    risk_score = _safe_int(row.get("attrition_risk_score"))
    risk_level = _normalize_risk_level(row.get("attrition_risk"), risk_score, thresholds=thresholds)
    priority_level = _compute_priority_level(
        row,
        risk_level,
        position_risk_info,
        position_profile,
        succession_info,
    )
    reason_tags = _build_risk_reason(row, position_risk_info)
    recommended_actions = _build_risk_actions(
        row,
        risk_level,
        priority_level,
        position_risk_info,
        position_profile,
        succession_info,
    )

    return {
        "employeeId": employee_id,
        "employee": row.get("name") or employee_id or "未知员工",
        "department": row.get("department") or "未标注部门",
        "positionName": position_name or "未标注岗位",
        "jobLevel": row.get("job_level") or "",
        "rankName": row.get("rank_name") or "",
        "riskScore": risk_score,
        "riskLevel": risk_level,
        "priorityLevel": priority_level,
        "performanceScore": _safe_float(row.get("performance_score")),
        "potentialScore": _safe_float(row.get("potential_score")),
        "potentialLevel": row.get("potential_level") or "",
        "tenureYears": _safe_float(row.get("tenure_years")),
        "compensationFactor": _safe_float(row.get("compensation_factor")),
        "talentTag": row.get("talent_tag") or "",
        "workMode": row.get("work_mode") or "",
        "positionRiskLevel": position_risk_info.get("positionRiskLevel") or "低",
        "positionRiskScore": position_risk_info.get("positionRiskScore") or 0,
        "isKeyPosition": _is_key_position(row, position_risk_info, position_profile),
        "isSuccessionCandidate": succession_info is not None,
        "reasonTags": reason_tags,
        "reason": " + ".join(reason_tags),
        "recommendedActions": recommended_actions,
        "action": "；".join(recommended_actions[:3]),
    }


def _build_risk_dataset():
    rows = _fetch_risk_employee_rows()
    position_risk_map = _load_position_risk_map()
    position_profile_map = _load_position_profile_map()
    succession_map = _load_succession_map()
    thresholds = get_risk_settings()

    items = [
        _build_risk_item(
            row,
            position_risk_map,
            position_profile_map,
            succession_map,
            thresholds=thresholds,
        )
        for row in rows
    ]

    items.sort(
        key=lambda item: (
            1 if item["priorityLevel"] == "high" else 0,
            item["riskScore"],
            1 if item["isKeyPosition"] else 0,
        ),
        reverse=True,
    )
    return items


def _matches_keyword(item, keyword):
    if not keyword:
        return True

    keyword = str(keyword).strip().lower()
    if not keyword:
        return True

    haystack = " ".join(
        [
            str(item.get("employee") or ""),
            str(item.get("employeeId") or ""),
            str(item.get("department") or ""),
            str(item.get("positionName") or ""),
            str(item.get("jobLevel") or ""),
            str(item.get("rankName") or ""),
            str(item.get("talentTag") or ""),
            str(item.get("reason") or ""),
        ]
    ).lower()
    return keyword in haystack


def _mock_risk_dataset():
    items = [
        {
            "employeeId": "E0007",
            "employee": "\u674e\u7136",
            "department": "\u7814\u53d1\u4e2d\u5fc3",
            "positionName": "\u540e\u7aef\u5de5\u7a0b\u5e08",
            "jobLevel": "\u5458\u5de5\u5c42",
            "rankName": "\u4e2d\u7ea7",
            "riskScore": 82,
            "riskLevel": "\u9ad8\u98ce\u9669",
            "priorityLevel": "high",
            "performanceScore": 2.0,
            "potentialScore": 78.0,
            "potentialLevel": "A\u7ea7",
            "tenureYears": 1.4,
            "compensationFactor": 0.84,
            "talentTag": "\u6838\u5fc3\u9aa8\u5e72",
            "workMode": "\u8fdc\u7a0b\u529e\u516c",
            "positionRiskLevel": "\u9ad8",
            "positionRiskScore": 76,
            "isKeyPosition": True,
            "isSuccessionCandidate": True,
            "reasonTags": [
                "\u8fd1\u671f\u7ee9\u6548\u504f\u4f4e",
                "\u85aa\u916c\u7ade\u4e89\u529b\u504f\u5f31",
                "\u8fdc\u7a0b\u529e\u516c\u9700\u989d\u5916\u5173\u6ce8\u5f52\u5c5e\u611f",
            ],
            "reason": "\u8fd1\u671f\u7ee9\u6548\u504f\u4f4e + \u85aa\u916c\u7ade\u4e89\u529b\u504f\u5f31 + \u8fdc\u7a0b\u529e\u516c\u9700\u989d\u5916\u5173\u6ce8\u5f52\u5c5e\u611f",
            "recommendedActions": [
                "3\u4e2a\u5de5\u4f5c\u65e5\u5185\u5b89\u6392 HRBP \u4e0e\u76f4\u5c5e\u7ecf\u7406\u8fdb\u884c\u4fdd\u7559\u9762\u8c08",
                "\u8bc4\u4f30\u85aa\u916c\u7ade\u4e89\u529b\u5e76\u7ed9\u51fa\u8c03\u6574\u5efa\u8bae",
                "\u8865\u5145\u5c97\u4f4d\u53d1\u5c55\u8def\u5f84\u548c\u5173\u952e\u9879\u76ee\u673a\u4f1a",
            ],
            "action": "3\u4e2a\u5de5\u4f5c\u65e5\u5185\u5b89\u6392 HRBP \u4e0e\u76f4\u5c5e\u7ecf\u7406\u8fdb\u884c\u4fdd\u7559\u9762\u8c08\uff1b\u8bc4\u4f30\u85aa\u916c\u7ade\u4e89\u529b\u5e76\u7ed9\u51fa\u8c03\u6574\u5efa\u8bae\uff1b\u8865\u5145\u5c97\u4f4d\u53d1\u5c55\u8def\u5f84\u548c\u5173\u952e\u9879\u76ee\u673a\u4f1a",
        },
        {
            "employeeId": "E0012",
            "employee": "\u5468\u5b81",
            "department": "\u5e02\u573a\u4e2d\u5fc3",
            "positionName": "\u62db\u5546\u4e3b\u7ba1",
            "jobLevel": "\u4e3b\u7ba1\u5c42",
            "rankName": "\u9ad8\u7ea7",
            "riskScore": 67,
            "riskLevel": "\u9ad8\u98ce\u9669",
            "priorityLevel": "high",
            "performanceScore": 3.0,
            "potentialScore": 72.0,
            "potentialLevel": "B\u7ea7",
            "tenureYears": 2.1,
            "compensationFactor": 0.90,
            "talentTag": "\u50a8\u5907\u4eba\u624d",
            "workMode": "\u6df7\u5408\u529e\u516c",
            "positionRiskLevel": "\u4e2d",
            "positionRiskScore": 58,
            "isKeyPosition": True,
            "isSuccessionCandidate": False,
            "reasonTags": [
                "\u53f8\u9f84\u8f83\u77ed\uff0c\u7a33\u5b9a\u6027\u4ecd\u9700\u89c2\u5bdf",
                "\u85aa\u916c\u7ade\u4e89\u529b\u504f\u5f31",
                "\u53d1\u5c55\u578b\u57f9\u8bad\u6295\u5165\u4e0d\u8db3",
            ],
            "reason": "\u53f8\u9f84\u8f83\u77ed\uff0c\u7a33\u5b9a\u6027\u4ecd\u9700\u89c2\u5bdf + \u85aa\u916c\u7ade\u4e89\u529b\u504f\u5f31 + \u53d1\u5c55\u578b\u57f9\u8bad\u6295\u5165\u4e0d\u8db3",
            "recommendedActions": [
                "\u7eb3\u5165\u9ad8\u4f18\u5148\u7ea7\u4fdd\u7559\u540d\u5355\u5e76\u8fdb\u884c\u6708\u5ea6\u8ddf\u8e2a",
                "\u8865\u5145\u53d1\u5c55\u578b\u57f9\u8bad\u4e0e\u5c97\u4f4d\u8f6e\u5c97\u673a\u4f1a",
                "\u7ed3\u5408\u4e1a\u52a1\u8282\u594f\u5b89\u6392\u4e00\u5bf9\u4e00\u6c9f\u901a",
            ],
            "action": "\u7eb3\u5165\u9ad8\u4f18\u5148\u7ea7\u4fdd\u7559\u540d\u5355\u5e76\u8fdb\u884c\u6708\u5ea6\u8ddf\u8e2a\uff1b\u8865\u5145\u53d1\u5c55\u578b\u57f9\u8bad\u4e0e\u5c97\u4f4d\u8f6e\u5c97\u673a\u4f1a\uff1b\u7ed3\u5408\u4e1a\u52a1\u8282\u594f\u5b89\u6392\u4e00\u5bf9\u4e00\u6c9f\u901a",
        },
        {
            "employeeId": "E0021",
            "employee": "\u9648\u66e6",
            "department": "\u4f9b\u5e94\u94fe\u4e2d\u5fc3",
            "positionName": "\u91c7\u8d2d\u4e13\u5458",
            "jobLevel": "\u5458\u5de5\u5c42",
            "rankName": "\u521d\u7ea7",
            "riskScore": 55,
            "riskLevel": "\u4e2d\u98ce\u9669",
            "priorityLevel": "normal",
            "performanceScore": 3.0,
            "potentialScore": 61.0,
            "potentialLevel": "B\u7ea7",
            "tenureYears": 1.1,
            "compensationFactor": 0.93,
            "talentTag": "\u666e\u901a\u5458\u5de5",
            "workMode": "\u73b0\u573a\u529e\u516c",
            "positionRiskLevel": "\u4e2d",
            "positionRiskScore": 49,
            "isKeyPosition": False,
            "isSuccessionCandidate": False,
            "reasonTags": [
                "\u53f8\u9f84\u8f83\u77ed\uff0c\u7a33\u5b9a\u6027\u4ecd\u9700\u89c2\u5bdf",
                "\u85aa\u916c\u7ade\u4e89\u529b\u504f\u5f31",
            ],
            "reason": "\u53f8\u9f84\u8f83\u77ed\uff0c\u7a33\u5b9a\u6027\u4ecd\u9700\u89c2\u5bdf + \u85aa\u916c\u7ade\u4e89\u529b\u504f\u5f31",
            "recommendedActions": [
                "\u7eb3\u5165\u6708\u5ea6\u98ce\u9669\u89c2\u5bdf\u540d\u5355",
                "\u5173\u6ce8\u8bd5\u7528\u540e\u53d1\u5c55\u9884\u671f\u4e0e\u5c97\u4f4d\u5339\u914d\u5ea6",
            ],
            "action": "\u7eb3\u5165\u6708\u5ea6\u98ce\u9669\u89c2\u5bdf\u540d\u5355\uff1b\u5173\u6ce8\u8bd5\u7528\u540e\u53d1\u5c55\u9884\u671f\u4e0e\u5c97\u4f4d\u5339\u914d\u5ea6",
        },
        {
            "employeeId": "E0033",
            "employee": "\u738b\u54f2",
            "department": "\u7814\u53d1\u4e2d\u5fc3",
            "positionName": "\u6d4b\u8bd5\u5de5\u7a0b\u5e08",
            "jobLevel": "\u5458\u5de5\u5c42",
            "rankName": "\u4e2d\u7ea7",
            "riskScore": 43,
            "riskLevel": "\u4e2d\u98ce\u9669",
            "priorityLevel": "normal",
            "performanceScore": 3.0,
            "potentialScore": 58.0,
            "potentialLevel": "C\u7ea7",
            "tenureYears": 4.8,
            "compensationFactor": 0.97,
            "talentTag": "\u666e\u901a\u5458\u5de5",
            "workMode": "\u8fdc\u7a0b\u529e\u516c",
            "positionRiskLevel": "\u4f4e",
            "positionRiskScore": 32,
            "isKeyPosition": False,
            "isSuccessionCandidate": False,
            "reasonTags": [
                "\u8fdc\u7a0b\u529e\u516c\u9700\u989d\u5916\u5173\u6ce8\u5f52\u5c5e\u611f",
                "\u6f5c\u529b\u7b49\u7ea7\u504f\u4f4e\uff0c\u53d1\u5c55\u4fe1\u5fc3\u53ef\u80fd\u4e0d\u8db3",
            ],
            "reason": "\u8fdc\u7a0b\u529e\u516c\u9700\u989d\u5916\u5173\u6ce8\u5f52\u5c5e\u611f + \u6f5c\u529b\u7b49\u7ea7\u504f\u4f4e\uff0c\u53d1\u5c55\u4fe1\u5fc3\u53ef\u80fd\u4e0d\u8db3",
            "recommendedActions": [
                "\u5b89\u6392\u76f4\u5c5e\u7ecf\u7406\u8fdb\u884c\u804c\u4e1a\u53d1\u5c55\u6c9f\u901a",
                "\u8865\u5145\u6210\u957f\u578b\u8bad\u7ec3\u8425\u6216\u8de8\u9879\u76ee\u673a\u4f1a",
            ],
            "action": "\u5b89\u6392\u76f4\u5c5e\u7ecf\u7406\u8fdb\u884c\u804c\u4e1a\u53d1\u5c55\u6c9f\u901a\uff1b\u8865\u5145\u6210\u957f\u578b\u8bad\u7ec3\u8425\u6216\u8de8\u9879\u76ee\u673a\u4f1a",
        },
        {
            "employeeId": "E0040",
            "employee": "\u8d75\u6674",
            "department": "\u8d22\u52a1\u90e8",
            "positionName": "\u8d22\u52a1\u5206\u6790\u5e08",
            "jobLevel": "\u5458\u5de5\u5c42",
            "rankName": "\u4e2d\u7ea7",
            "riskScore": 28,
            "riskLevel": "\u4f4e\u98ce\u9669",
            "priorityLevel": "normal",
            "performanceScore": 4.0,
            "potentialScore": 75.0,
            "potentialLevel": "A\u7ea7",
            "tenureYears": 5.2,
            "compensationFactor": 1.02,
            "talentTag": "\u50a8\u5907\u4eba\u624d",
            "workMode": "\u73b0\u573a\u529e\u516c",
            "positionRiskLevel": "\u4f4e",
            "positionRiskScore": 25,
            "isKeyPosition": False,
            "isSuccessionCandidate": True,
            "reasonTags": ["\u5f53\u524d\u672a\u53d1\u73b0\u7279\u522b\u7a81\u51fa\u7684\u663e\u6027\u98ce\u9669\u56e0\u7d20"],
            "reason": "\u5f53\u524d\u672a\u53d1\u73b0\u7279\u522b\u7a81\u51fa\u7684\u663e\u6027\u98ce\u9669\u56e0\u7d20",
            "recommendedActions": ["\u4fdd\u6301\u5e38\u89c4\u5173\u6ce8\u5e76\u7ed3\u5408\u664b\u5347\u8282\u594f\u8fdb\u884c\u8bbf\u8c08"],
            "action": "\u4fdd\u6301\u5e38\u89c4\u5173\u6ce8\u5e76\u7ed3\u5408\u664b\u5347\u8282\u594f\u8fdb\u884c\u8bbf\u8c08",
        },
    ]

    thresholds = get_risk_settings()
    for item in items:
        item["riskLevel"] = _normalize_risk_level(
            item.get("riskLevel"),
            item.get("riskScore"),
            thresholds=thresholds,
        )
    return items


def _build_risk_overview_payload(items):
    total = len(items)
    high = len([item for item in items if item["riskLevel"] == "\u9ad8\u98ce\u9669"])
    medium = len([item for item in items if item["riskLevel"] == "\u4e2d\u98ce\u9669"])
    low = len([item for item in items if item["riskLevel"] == "\u4f4e\u98ce\u9669"])
    high_priority = len([item for item in items if item["priorityLevel"] == "high"])
    departments = len({item["department"] for item in items if item["department"]})

    focus_candidates = [
        item for item in items
        if item["riskLevel"] == "\u9ad8\u98ce\u9669"
    ]

    department_counts = {}
    for item in items:
        department = item["department"]
        department_counts[department] = department_counts.get(department, 0) + 1

    department_distribution = [
        {"department": name, "count": count}
        for name, count in sorted(department_counts.items(), key=lambda pair: pair[1], reverse=True)[:6]
    ]

    reason_counts = {}
    for item in items:
        for reason in item.get("reasonTags") or []:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

    reason_distribution = [
        {"label": name, "count": count}
        for name, count in sorted(reason_counts.items(), key=lambda pair: pair[1], reverse=True)[:6]
    ]

    return {
        "summary": {
            "total": total,
            "high": high,
            "medium": medium,
            "low": low,
            "departments": departments,
            "highPriority": high_priority,
            "lastUpdated": date.today().isoformat(),
        },
        "riskDistribution": [
            {"label": "\u9ad8\u98ce\u9669", "value": high, "color": "#dc2626"},
            {"label": "\u4e2d\u98ce\u9669", "value": medium, "color": "#ea580c"},
            {"label": "\u4f4e\u98ce\u9669", "value": low, "color": "#16a34a"},
        ],
        "priorityDistribution": [
            {"label": "\u9ad8\u4f18\u5148\u7ea7", "value": high_priority, "color": "#0f766e"},
            {"label": "\u5e38\u89c4\u8ddf\u8fdb", "value": max(total - high_priority, 0), "color": "#94a3b8"},
        ],
        "focusEmployees": focus_candidates[:6],
        "departmentDistribution": department_distribution,
        "reasonDistribution": reason_distribution,
    }


def _paginate_risk_items(items, keyword=None, page=1, page_size=10):
    if keyword:
        items = [item for item in items if _matches_keyword(item, keyword)]

    page = max(_safe_int(page, 1), 1)
    page_size = max(_safe_int(page_size, 10), 1)
    total = len(items)
    total_pages = max((total + page_size - 1) // page_size, 1)
    if page > total_pages:
        page = total_pages

    start = (page - 1) * page_size
    end = start + page_size
    page_items = items[start:end]

    return {
        "total": total,
        "page": page,
        "pageSize": page_size,
        "totalPages": total_pages,
        "keyword": keyword or "",
        "items": page_items,
    }


def _build_mock_risk_detail(employee_id):
    item = next((entry for entry in _mock_risk_dataset() if entry["employeeId"] == employee_id), None)
    if item is None:
        return None

    employee_input = {
        "\u5458\u5de5\u5de5\u53f7": item["employeeId"],
        "\u59d3\u540d": item["employee"],
        "\u6240\u5c5e\u90e8\u95e8": item["department"],
        "\u5c97\u4f4d\u540d\u79f0": item["positionName"],
        "\u804c\u7ea7\u5c42\u7ea7": item["jobLevel"],
        "\u804c\u7ea7": item["rankName"],
        "\u7ee9\u6548\u8bc4\u5206": item["performanceScore"],
        "\u53f8\u9f84(\u5e74)": item["tenureYears"],
        "\u85aa\u916c\u7cfb\u6570": item["compensationFactor"],
        "\u5df2\u5b8c\u6210\u57f9\u8bad": "\u6c9f\u901a\u6280\u5de7\u3001\u9879\u76ee\u534f\u4f5c",
        "\u6f5c\u529b\u8bc4\u5206": item["potentialScore"],
        "\u6f5c\u529b\u7b49\u7ea7": item["potentialLevel"],
        "\u6d41\u5931\u98ce\u9669\u5206": item["riskScore"],
        "\u6d41\u5931\u98ce\u9669": item["riskLevel"],
        "\u4eba\u624d\u6807\u7b7e": item["talentTag"],
        "\u529e\u516c\u65b9\u5f0f": item["workMode"],
        "\u662f\u5426\u5173\u952e\u5c97\u4f4d": "\u662f" if item["isKeyPosition"] else "\u5426",
        "\u662f\u5426\u7ee7\u4efb\u5019\u9009": "\u662f" if item["isSuccessionCandidate"] else "\u5426",
    }

    return {
        "employeeId": item["employeeId"],
        "employee": item["employee"],
        "department": item["department"],
        "positionName": item["positionName"],
        "jobLevel": item["jobLevel"],
        "rankName": item["rankName"],
        "riskScore": item["riskScore"],
        "riskLevel": item["riskLevel"],
        "priorityLevel": item["priorityLevel"],
        "reason": item["reason"],
        "reasonTags": item["reasonTags"],
        "recommendedActions": item["recommendedActions"],
        "summary": f"{item['employee']}\u5f53\u524d\u4e3a{item['riskLevel']}\uff0c\u98ce\u9669\u5206\u4e3a{item['riskScore']}\uff0c\u5e72\u9884\u4f18\u5148\u7ea7\u4e3a{item['priorityLevel']}\u3002",
        "profile": {
            "age": None,
            "gender": None,
            "tenureYears": item["tenureYears"],
            "baseSalary": None,
            "compensationFactor": item["compensationFactor"],
            "workMode": item["workMode"],
            "talentTag": item["talentTag"],
            "managerId": None,
        },
        "assessment": {
            "performanceScore": item["performanceScore"],
            "potentialScore": item["potentialScore"],
            "potentialLevel": item["potentialLevel"],
        },
        "positionRisk": {
            "positionRiskLevel": item["positionRiskLevel"],
            "positionRiskScore": item["positionRiskScore"],
            "isKeyPosition": item["isKeyPosition"],
            "positionType": None,
            "isManager": None,
        },
        "development": {
            "trainingCompleted": ["\u6c9f\u901a\u6280\u5de7", "\u9879\u76ee\u534f\u4f5c"],
            "requiredTraining": ["\u804c\u4e1a\u53d1\u5c55\u89c4\u5212", "\u5173\u952e\u5c97\u4f4d\u80fd\u529b\u8bad\u7ec3"],
            "missingTraining": ["\u804c\u4e1a\u53d1\u5c55\u89c4\u5212", "\u5173\u952e\u5c97\u4f4d\u80fd\u529b\u8bad\u7ec3"],
            "skillTags": [],
        },
        "succession": {
            "isCandidate": item["isSuccessionCandidate"],
            "targetPosition": item["positionName"] if item["isSuccessionCandidate"] else None,
            "matchScore": 0,
            "successionLevel": "\u5f85\u8bc4\u4f30" if item["isSuccessionCandidate"] else "\u6682\u65e0",
        },
        "employeeInput": employee_input,
        "employeeInputText": str(employee_input),
        "managerNote": {"note": "", "updatedAt": "", "updatedBy": ""},
        "followUps": [],
        "interventionContext": (
            f"\u5458\u5de5\u59d3\u540d\uff1a{item['employee']}\\n"
            f"\u5458\u5de5\u5de5\u53f7\uff1a{item['employeeId']}\\n"
            f"\u6240\u5c5e\u90e8\u95e8\uff1a{item['department']}\\n"
            f"\u5c97\u4f4d\u540d\u79f0\uff1a{item['positionName']}\\n"
            f"\u98ce\u9669\u7b49\u7ea7\uff1a{item['riskLevel']}\\n"
            f"\u98ce\u9669\u5206\uff1a{item['riskScore']}\\n"
            f"\u5e72\u9884\u4f18\u5148\u7ea7\uff1a{item['priorityLevel']}\\n"
            f"\u4e3b\u8981\u98ce\u9669\u56e0\u7d20\uff1a{'\u3001'.join(item['reasonTags'])}\\n"
            f"\u5efa\u8bae\u52a8\u4f5c\uff1a{'\uff1b'.join(item['recommendedActions'])}"
        ),
    }


def get_overview():
    try:
        emp_count = query_one("SELECT COUNT(*) AS cnt FROM employee_talent_data")
        high_risk = query_one(
            """
            SELECT COUNT(*) AS cnt
            FROM employee_talent_data
            WHERE attrition_risk LIKE '高%%'
               OR attrition_risk_score >= 60
            """
        )
        ready_now = query_one(
            """
            SELECT COUNT(*) AS cnt
            FROM succession_candidates
            WHERE succession_level IN ('1', 'Ready Now', 'ready_now', 'ready')
            """
        )
        key_positions = query_one("SELECT COUNT(*) AS cnt FROM position_profile")
        trained = query_one(
            """
            SELECT COUNT(*) AS cnt
            FROM employee_ability
            WHERE training_completed IS NOT NULL
              AND TRIM(training_completed) <> ''
            """
        )

        total = int((emp_count or {}).get("cnt") or 0)
        trained_count = int((trained or {}).get("cnt") or 0)
        completion = min(round(trained_count / total, 2), 1.0) if total else 0

        return {
            "employeeCount": total,
            "keyPositions": int((key_positions or {}).get("cnt") or 0),
            "readyNowSuccessors": int((ready_now or {}).get("cnt") or 0),
            "highRiskEmployees": int((high_risk or {}).get("cnt") or 0),
            "completionRate": completion,
            "lastUpdated": date.today().isoformat(),
        }
    except Exception:
        from backend.mock_data import get_overview as mock

        return mock()


def get_nine_box():
    try:
        rows = query_all(
            "SELECT performance_score, potential_score FROM employee_talent_data"
        )
        counts = {}
        for row in rows:
            performance_score = _safe_float(row.get("performance_score"))
            potential_score = _safe_float(row.get("potential_score"))
            cell = _compute_nine_grid(performance_score, potential_score)
            counts[cell] = counts.get(cell, 0) + 1

        order = [
            "高潜-高绩效",
            "高潜-中绩效",
            "高潜-低绩效",
            "中潜-高绩效",
            "中潜-中绩效",
            "中潜-低绩效",
            "低潜-高绩效",
            "低潜-中绩效",
            "低潜-低绩效",
        ]
        level_map = {
            "高潜-高绩效": "A",
            "高潜-中绩效": "A",
            "高潜-低绩效": "B",
            "中潜-高绩效": "A",
            "中潜-中绩效": "B",
            "中潜-低绩效": "C",
            "低潜-高绩效": "B",
            "低潜-中绩效": "C",
            "低潜-低绩效": "C",
        }

        return [
            {"cell": cell, "count": counts.get(cell, 0), "level": level_map[cell]}
            for cell in order
            if counts.get(cell, 0) > 0
        ]
    except Exception:
        from backend.mock_data import get_nine_box as mock

        return mock()


def get_succession_candidates():
    try:
        rows = query_all(
            """
            SELECT
                target_position AS position,
                COALESCE(employee_name, candidate_employee_id) AS candidate,
                succession_level,
                ROUND(match_score, 0) AS matchScore
            FROM succession_candidates
            ORDER BY match_score DESC
            LIMIT 20
            """
        )
        for row in rows:
            row["readiness"] = _format_succession_level(row.pop("succession_level", None))
            row["risk"] = "待评估"
        return rows
    except Exception:
        from backend.mock_data import get_succession_candidates as mock

        return mock()


def get_risk_overview():
    try:
        items = _build_risk_dataset()
    except Exception as exc:
        _log_risk_error("get_risk_overview", exc)
        items = _mock_risk_dataset()
    return _build_risk_overview_payload(items)


def get_risk_employees(level=None, keyword=None, page=1, page_size=10):
    try:
        items = _build_risk_dataset()
    except Exception as exc:
        _log_risk_error("get_risk_employees", exc)
        items = _mock_risk_dataset()

    if level and level != "\u5168\u90e8":
        items = [item for item in items if item["riskLevel"] == level]

    return _paginate_risk_items(items, keyword=keyword, page=page, page_size=page_size)


def get_risk_employee_detail(employee_id):
    try:
        rows = _fetch_risk_employee_rows(employee_id=employee_id)
        if not rows:
            return None

        row = rows[0]
        position_name = str(row.get("position_name") or "").strip()
        position_risk_map = _load_position_risk_map()
        position_profile_map = _load_position_profile_map()
        succession_map = _load_succession_map()

        thresholds = get_risk_settings()
        risk_item = _build_risk_item(
            row,
            position_risk_map,
            position_profile_map,
            succession_map,
            thresholds=thresholds,
        )
        position_profile = position_profile_map.get(position_name, {})
        succession_info = succession_map.get(employee_id)

        training_completed = _split_text(row.get("training_completed"))
        required_training = _split_text(position_profile.get("required_training"))
        missing_training = [item for item in required_training if item not in training_completed]

        employee_input = _build_employee_input_payload(
            row,
            risk_item,
            risk_item["isKeyPosition"],
            succession_info,
        )
        intervention_context = _build_intervention_context(
            row,
            risk_item,
            risk_item["isKeyPosition"],
            succession_info,
            required_training,
        )

        return {
            "employeeId": risk_item["employeeId"],
            "employee": risk_item["employee"],
            "department": risk_item["department"],
            "positionName": risk_item["positionName"],
            "jobLevel": risk_item["jobLevel"],
            "rankName": risk_item["rankName"],
            "riskScore": risk_item["riskScore"],
            "riskLevel": risk_item["riskLevel"],
            "priorityLevel": risk_item["priorityLevel"],
            "reason": risk_item["reason"],
            "reasonTags": risk_item["reasonTags"],
            "recommendedActions": risk_item["recommendedActions"],
            "summary": (
                f"{risk_item['employee']}\u5f53\u524d\u4e3a{risk_item['riskLevel']}\uff0c"
                f"\u98ce\u9669\u5206\u4e3a{risk_item['riskScore']}\uff0c\u5e72\u9884\u4f18\u5148\u7ea7\u4e3a{risk_item['priorityLevel']}\u3002"
            ),
            "profile": {
                "age": row.get("age"),
                "gender": row.get("gender"),
                "tenureYears": risk_item["tenureYears"],
                "baseSalary": _safe_float(row.get("base_salary")),
                "compensationFactor": risk_item["compensationFactor"],
                "workMode": risk_item["workMode"],
                "talentTag": risk_item["talentTag"],
                "managerId": row.get("manager_id"),
            },
            "assessment": {
                "performanceScore": risk_item["performanceScore"],
                "potentialScore": risk_item["potentialScore"],
                "potentialLevel": risk_item["potentialLevel"],
            },
            "positionRisk": {
                "positionRiskLevel": risk_item["positionRiskLevel"],
                "positionRiskScore": risk_item["positionRiskScore"],
                "isKeyPosition": risk_item["isKeyPosition"],
                "positionType": position_profile.get("position_type"),
                "isManager": position_profile.get("is_manager"),
            },
            "development": {
                "trainingCompleted": training_completed,
                "requiredTraining": required_training,
                "missingTraining": missing_training,
                "skillTags": _split_text(row.get("skill_tags")),
            },
            "succession": {
                "isCandidate": succession_info is not None,
                "targetPosition": (succession_info or {}).get("target_position"),
                "matchScore": _safe_float((succession_info or {}).get("match_score")),
                "successionLevel": _format_succession_level((succession_info or {}).get("succession_level")),
            },
            "employeeInput": employee_input,
            "employeeInputText": str(employee_input),
            "interventionContext": intervention_context,
            "managerNote": get_employee_note(employee_id),
            "followUps": get_follow_ups(employee_id),
        }
    except Exception as exc:
        _log_risk_error("get_risk_employee_detail", exc)
        return _build_mock_risk_detail(employee_id)


def get_risk_alerts():
    items = get_risk_employees()["items"][:20]
    return [
        {
            "employeeId": item["employeeId"],
            "employee": item["employee"],
            "department": item["department"],
            "riskLevel": item["riskLevel"],
            "reason": item["reason"],
            "action": item["action"],
        }
        for item in items
    ]


def get_training_plans():
    try:
        rows = query_all(
            """
            SELECT
                plan_name AS name,
                target_position_name AS targetGroup,
                plan_status AS duration,
                0.5 AS progress
            FROM training_plans
            ORDER BY updated_at DESC
            LIMIT 10
            """
        )
        if rows:
            for row in rows:
                row["progress"] = min(_safe_float(row.get("progress"), 0.5), 1.0)
            return rows
    except Exception:
        pass

    from backend.mock_data import get_training_plans as mock

    return mock()


def get_employee_by_no(employee_no):
    employee = query_one(
        "SELECT * FROM employee_talent_data WHERE employee_id = %s",
        (employee_no,),
    )
    if employee is None:
        return None

    position_profile = None
    if employee.get("position_name"):
        try:
            position_profile = query_one(
                "SELECT * FROM position_profile WHERE position_name = %s",
                (employee["position_name"],),
            )
        except Exception:
            position_profile = None

    skills = _split_text(employee.get("skill_tags"))
    trainings_raw = _split_text(employee.get("training_completed"))
    trainings = [{"name": item, "completedAt": None} for item in trainings_raw]

    return {
        "employeeNo": employee["employee_id"],
        "name": employee["name"],
        "department": employee.get("department"),
        "position": employee.get("position_name"),
        "jobLevel": employee.get("job_level"),
        "rankName": employee.get("rank_name"),
        "managerNo": employee.get("manager_id"),
        "profile": {
            "age": employee.get("age"),
            "gender": employee.get("gender"),
            "tenureYears": _safe_float(employee.get("tenure_years"), None),
            "baseSalary": _safe_float(employee.get("base_salary"), None),
            "compensationFactor": _safe_float(employee.get("compensation_factor"), None),
            "workMode": employee.get("work_mode"),
        },
        "skills": skills,
        "trainings": trainings,
        "assessment": {
            "performanceScore": _safe_float(employee.get("performance_score"), None),
            "potentialScore": _safe_float(employee.get("potential_score"), None),
            "potentialLevel": employee.get("potential_level"),
            "talentTag": employee.get("talent_tag"),
        },
        "risk": {
            "riskScore": employee.get("attrition_risk_score"),
            "riskLevel": employee.get("attrition_risk"),
        },
        "positionProfile": {
            "positionType": position_profile.get("position_type") if position_profile else None,
            "coreSkills": _split_text(position_profile.get("core_skills")) if position_profile else [],
            "bonusSkills": _split_text(position_profile.get("bonus_skills")) if position_profile else [],
            "requiredTraining": _split_text(position_profile.get("required_training")) if position_profile else [],
            "performanceRequirement": position_profile.get("performance_requirement") if position_profile else None,
            "tenureRequirement": position_profile.get("tenure_requirement") if position_profile else None,
            "workModeRequirement": position_profile.get("work_mode_requirement") if position_profile else None,
            "isManager": position_profile.get("is_manager") if position_profile else None,
            "fitDescription": position_profile.get("fit_description") if position_profile else None,
        }
        if position_profile
        else None,
    }


def get_potential_list():
    try:
        return query_all(
            """
            SELECT employee_id, name, potential_score, potential_level, talent_tag
            FROM employee_potential
            ORDER BY potential_score DESC
            """
        )
    except Exception:
        return []


def get_potential_by_id(employee_id):
    try:
        return query_one(
            """
            SELECT employee_id, name, potential_score, potential_level, talent_tag
            FROM employee_potential
            WHERE employee_id = %s
            """,
            (employee_id,),
        )
    except Exception:
        return None


def update_potential(employee_id, potential_score, potential_level, talent_tag=None):
    try:
        sql = """
            UPDATE employee_potential
            SET potential_score = %s, potential_level = %s
        """
        params = [potential_score, potential_level]
        if talent_tag is not None:
            sql += ", talent_tag = %s"
            params.append(talent_tag)
        sql += " WHERE employee_id = %s"
        params.append(employee_id)

        execute(sql, params)
        execute(
            """
            UPDATE employee_talent_data
            SET potential_score = %s, potential_level = %s
            WHERE employee_id = %s
            """,
            (potential_score, potential_level, employee_id),
        )
        return True
    except Exception:
        return False
