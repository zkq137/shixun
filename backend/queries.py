"""SQL queries that replace mock data — fetch from MySQL."""

from datetime import date

from backend.db import query_all, query_one, execute


# ── 辅助：根据绩效分和潜力分计算九宫格位置 ─────────────────


def _compute_nine_grid(perf, pot):
    """根据绩效分(1-5)和潜力分(0-100)映射到九宫格"""
    if perf >= 4.5:
        perf_level = "高绩效"
    elif perf >= 3.0:
        perf_level = "中绩效"
    else:
        perf_level = "低绩效"

    if pot >= 80:
        pot_level = "高潜"
    elif pot >= 60:
        pot_level = "中潜"
    else:
        pot_level = "低潜"

    return f"{pot_level}-{perf_level}"


# ── 概览 ───────────────────────────────────────────────


def get_overview():
    """首页概览卡片数据"""
    emp_count = query_one("SELECT COUNT(*) AS cnt FROM employees WHERE status = 'active'")
    # 从 turnover_risk_records 中统计高风险
    high_risk = query_one(
        "SELECT COUNT(DISTINCT employee_id) AS cnt FROM turnover_risk_records WHERE risk_level = '高风险'"
    )
    # 培训覆盖率
    trained = query_one("SELECT COUNT(DISTINCT employee_id) AS cnt FROM employee_trainings")
    total = emp_count["cnt"] or 1
    completion = min(round(trained["cnt"] / total, 2), 1.0) if total else 0

    return {
        "employeeCount": emp_count["cnt"] or 0,
        "keyPositions": 48,  # 静态值，可在后续版本中从关键岗位表读取
        "readyNowSuccessors": 36,
        "highRiskEmployees": high_risk["cnt"] or 0,
        "completionRate": completion,
        "lastUpdated": date.today().isoformat(),
    }


# ── 九宫格 ─────────────────────────────────────────────


def get_nine_box():
    """人才九宫格数据（根据绩效分+潜力分实时计算）"""
    rows = query_all(
        "SELECT performance_score, potential_score FROM talent_assessments"
    )
    grid = {}
    for r in rows:
        cell = _compute_nine_grid(
            float(r["performance_score"]), float(r["potential_score"])
        )
        grid[cell] = grid.get(cell, 0) + 1

    # 固定顺序
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
        "高潜-高绩效": "A", "高潜-中绩效": "A",
        "高潜-低绩效": "B", "中潜-高绩效": "A",
        "中潜-中绩效": "B", "中潜-低绩效": "C",
        "低潜-高绩效": "B", "低潜-中绩效": "C",
        "低潜-低绩效": "C",
    }
    result = []
    for cell in order:
        count = grid.get(cell, 0)
        if count > 0:
            result.append({"cell": cell, "count": count, "level": level_map[cell]})
    return result if result else []


# ── 继任候选人 ─────────────────────────────────────────


def get_succession_candidates():
    """关键岗位继任候选人"""
    rows = query_all(
        """
        SELECT
            sc.target_position_name AS position,
            e.name AS candidate,
            COALESCE(sc.readiness_level, '待评估') AS readiness,
            ROUND(sc.match_score, 0) AS matchScore,
            CASE
                WHEN tr.risk_level = '高风险' THEN '高'
                WHEN tr.risk_level = '中风险' THEN '中'
                ELSE '低'
            END AS risk
        FROM succession_candidates sc
        JOIN employees e ON e.id = sc.candidate_employee_id
        LEFT JOIN (
            SELECT employee_id, risk_level
            FROM turnover_risk_records
            WHERE (employee_id, assessment_time) IN (
                SELECT employee_id, MAX(assessment_time)
                FROM turnover_risk_records
                GROUP BY employee_id
            )
        ) tr ON tr.employee_id = sc.candidate_employee_id
        ORDER BY sc.match_score DESC
        LIMIT 20
        """
    )
    # 如果表为空，返回模拟数据
    if not rows:
        from backend.mock_data import get_succession_candidates as mock
        return mock()
    return rows


# ── 流失风险 ───────────────────────────────────────────


def get_risk_alerts():
    """流失风险预警"""
    rows = query_all(
        """
        SELECT
            e.name AS employee,
            e.department,
            CASE
                WHEN tr.risk_level = '高风险' THEN '高'
                WHEN tr.risk_level = '中风险' THEN '中'
                ELSE '低'
            END AS riskLevel,
            COALESCE(tr.risk_reason, '暂无详细原因') AS reason,
            COALESCE(tr.intervention_plan, '待制定干预方案') AS action
        FROM turnover_risk_records tr
        JOIN employees e ON e.id = tr.employee_id
        WHERE (tr.employee_id, tr.assessment_time) IN (
            SELECT employee_id, MAX(assessment_time)
            FROM turnover_risk_records
            GROUP BY employee_id
        )
        ORDER BY FIELD(tr.risk_level, '高风险', '中风险', '低风险')
        LIMIT 20
        """
    )
    return rows if rows else []


# ── 培训计划 ───────────────────────────────────────────


def get_training_plans():
    """培训计划概览（从员工培训记录中聚合热门培训）"""
    rows = query_all(
        """
        SELECT
            training_name AS name,
            '全体员工' AS targetGroup,
            '线上课程' AS duration,
            ROUND(COUNT(*) / (SELECT COUNT(*) FROM employees WHERE status = 'active'), 2) AS progress
        FROM employee_trainings
        GROUP BY training_name
        ORDER BY COUNT(*) DESC
        LIMIT 10
        """
    )
    if not rows:
        from backend.mock_data import get_training_plans as mock
        return mock()
    # progress 最大 1.0
    for r in rows:
        r["progress"] = min(float(r["progress"]), 1.0)
    return rows


# ── 员工查询 ───────────────────────────────────────────


def _split_text(val):
    """将逗号/顿号分隔的文本转为列表"""
    if not val:
        return []
    import re
    return [s.strip() for s in re.split(r"[、,，]", str(val)) if s.strip()]


def get_employee_by_no(employee_no):
    """
    根据工号从 employee_talent_data 表查询员工完整信息。
    """
    try:
        emp = query_one(
            "SELECT * FROM employee_talent_data WHERE employee_id = %s",
            (employee_no,),
        )
    except Exception:
        emp = None

    if emp is None:
        return None

    # 查询岗位画像
    position_profile = None
    if emp.get("position_name"):
        try:
            position_profile = query_one(
                "SELECT * FROM position_profile WHERE position_name = %s",
                (emp["position_name"],),
            )
        except Exception:
            pass

    skills = _split_text(emp.get("skill_tags"))
    trainings_raw = _split_text(emp.get("training_completed"))
    trainings = [{"name": t, "completedAt": None} for t in trainings_raw]

    return {
        "employeeNo": emp["employee_id"],
        "name": emp["name"],
        "department": emp["department"],
        "position": emp["position_name"],
        "jobLevel": emp["job_level"],
        "rankName": emp["rank_name"],
        "managerNo": emp.get("manager_id"),
        "profile": {
            "age": emp.get("age"),
            "gender": emp.get("gender"),
            "tenureYears": float(emp["tenure_years"]) if emp.get("tenure_years") else None,
            "baseSalary": float(emp["base_salary"]) if emp.get("base_salary") else None,
            "compensationFactor": float(emp["compensation_factor"]) if emp.get("compensation_factor") else None,
            "workMode": emp.get("work_mode"),
        },
        "skills": skills,
        "trainings": trainings,
        "assessment": {
            "performanceScore": float(emp["performance_score"]) if emp.get("performance_score") else None,
            "potentialScore": float(emp["potential_score"]) if emp.get("potential_score") else None,
            "potentialLevel": emp.get("potential_level"),
            "talentTag": emp.get("talent_tag"),
        },
        "risk": {
            "riskScore": emp.get("attrition_risk_score"),
            "riskLevel": emp.get("attrition_risk"),
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
        } if position_profile else None,
    }


# ── 员工潜力表 ─────────────────────────────────────────


def get_potential_list():
    """查询员工潜力表（全部记录）"""
    try:
        rows = query_all(
            "SELECT employee_id, name, potential_score, potential_level, talent_tag "
            "FROM employee_potential ORDER BY potential_score DESC"
        )
        return rows
    except Exception:
        return []


def get_potential_by_id(employee_id):
    """按工号查询员工潜力"""
    try:
        row = query_one(
            "SELECT employee_id, name, potential_score, potential_level, talent_tag "
            "FROM employee_potential WHERE employee_id = %s",
            (employee_id,),
        )
        return row
    except Exception:
        return None


def update_potential(employee_id, potential_score, potential_level, talent_tag=None):
    """更新员工潜力数据，同时同步到 employee_talent_data"""
    try:
        # 1. 更新 employee_potential 表
        sql_potential = """
            UPDATE employee_potential
            SET potential_score = %s, potential_level = %s
        """
        params = [potential_score, potential_level]
        if talent_tag is not None:
            sql_potential += ", talent_tag = %s"
            params.append(talent_tag)
        sql_potential += " WHERE employee_id = %s"
        params.append(employee_id)

        execute(sql_potential, params)

        # 2. 同步更新 employee_talent_data 表
        execute(
            "UPDATE employee_talent_data "
            "SET potential_score = %s, potential_level = %s "
            "WHERE employee_id = %s",
            (potential_score, potential_level, employee_id),
        )

        return True
    except Exception:
        return False
