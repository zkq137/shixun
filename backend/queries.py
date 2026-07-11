"""Database queries for the current talent pipeline schema."""

from datetime import date
import re

from backend.db import execute, query_all, query_one


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


def _normalize_risk_level(raw_level, raw_score):
    text = str(raw_level or "").strip()
    if "高" in text:
        return "高风险"
    if "中" in text:
        return "中风险"
    if "低" in text:
        return "低风险"

    score = _safe_float(raw_score)
    if score >= 60:
        return "高风险"
    if score >= 40:
        return "中风险"
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


def _fetch_risk_employee_rows(employee_id=None):
    sql = """
        SELECT
            employee_id,
            name,
            age,
            gender,
            position_name,
            job_level,
            rank_name,
            department,
            performance_score,
            tenure_years,
            base_salary,
            compensation_factor,
            skill_tags,
            training_completed,
            potential_score,
            potential_level,
            attrition_risk_score,
            attrition_risk,
            talent_tag,
            work_mode,
            manager_id
        FROM employee_talent_data
    """
    params = ()
    if employee_id:
        sql += " WHERE employee_id = %s"
        params = (employee_id,)
    else:
        sql += """
            WHERE attrition_risk IS NOT NULL
               OR attrition_risk_score IS NOT NULL
        """
    sql += " ORDER BY COALESCE(attrition_risk_score, 0) DESC, employee_id ASC"
    return query_all(sql, params)


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


def _build_risk_item(row, position_risk_map, position_profile_map, succession_map):
    position_name = str(row.get("position_name") or "").strip()
    employee_id = str(row.get("employee_id") or "").strip()

    position_risk_info = position_risk_map.get(position_name, {})
    position_profile = position_profile_map.get(position_name, {})
    succession_info = succession_map.get(employee_id)

    risk_score = _safe_int(row.get("attrition_risk_score"))
    risk_level = _normalize_risk_level(row.get("attrition_risk"), risk_score)
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

    items = [
        _build_risk_item(row, position_risk_map, position_profile_map, succession_map)
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
    items = _build_risk_dataset()
    total = len(items)
    high = len([item for item in items if item["riskLevel"] == "高风险"])
    medium = len([item for item in items if item["riskLevel"] == "中风险"])
    low = len([item for item in items if item["riskLevel"] == "低风险"])
    high_priority = len([item for item in items if item["priorityLevel"] == "high"])
    departments = len({item["department"] for item in items if item["department"]})

    department_counts = {}
    for item in items:
        department = item["department"]
        department_counts[department] = department_counts.get(department, 0) + 1

    department_distribution = [
        {"department": name, "count": count}
        for name, count in sorted(department_counts.items(), key=lambda pair: pair[1], reverse=True)[:6]
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
        "focusEmployees": items[:5],
        "departmentDistribution": department_distribution,
    }


def get_risk_employees(level=None):
    items = _build_risk_dataset()
    if level and level != "全部":
        items = [item for item in items if item["riskLevel"] == level]

    return {
        "total": len(items),
        "items": items,
    }


def get_risk_employee_detail(employee_id):
    rows = _fetch_risk_employee_rows(employee_id=employee_id)
    if not rows:
        return None

    row = rows[0]
    position_name = str(row.get("position_name") or "").strip()
    position_risk_map = _load_position_risk_map()
    position_profile_map = _load_position_profile_map()
    succession_map = _load_succession_map()

    risk_item = _build_risk_item(row, position_risk_map, position_profile_map, succession_map)
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
            f"{risk_item['employee']}当前为{risk_item['riskLevel']}，"
            f"风险分{risk_item['riskScore']}，干预优先级为{risk_item['priorityLevel']}。"
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
    }


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
