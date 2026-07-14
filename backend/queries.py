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
            sc.department,
            sc.target_position_level AS positionLevel,
            sc.target_position AS position,
            sc.employee_name AS candidate,
            COALESCE(sc.succession_level, '待评估') AS readiness,
            CAST(sc.match_score AS DECIMAL(10,0)) AS matchScore
        FROM succession_candidates sc
        ORDER BY CAST(sc.match_score AS DECIMAL(10,2)) DESC
        """
    )
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


def get_succession_candidates_filtered(position_name=None, candidate_name=None):
    """按岗位名称/员工姓名筛选继任候选人"""
    sql = """
        SELECT
            sc.department,
            sc.target_position_level AS positionLevel,
            sc.target_position AS position,
            sc.employee_name AS candidate,
            COALESCE(sc.succession_level, '待评估') AS readiness,
            CAST(sc.match_score AS DECIMAL(10,0)) AS matchScore
        FROM succession_candidates sc
    """
    conditions = []
    params = []
    if position_name:
        conditions.append(" sc.target_position LIKE %s")
        params.append(f"%{position_name}%")
    if candidate_name:
        conditions.append(" sc.employee_name LIKE %s")
        params.append(f"%{candidate_name}%")
    if conditions:
        sql += " WHERE" + " AND".join(conditions)
    sql += " ORDER BY CAST(sc.match_score AS DECIMAL(10,2)) DESC"

    rows = query_all(sql, params)
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
    """更新员工潜力数据（仅更新 employee_potential 表）"""
    try:
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
        return True
    except Exception:
        return False


# ── 岗位风险研判 ───────────────────────────────────────


def get_position_risk_list():
    """查询岗位风险列表"""
    try:
        rows = query_all(
            "SELECT position_name, total_risk_score, risk_level "
            "FROM position_risk ORDER BY total_risk_score DESC"
        )
        return rows
    except Exception:
        return []


def get_employee_risk_list():
    """查询员工流失风险"""
    try:
        rows = query_all(
            """
            SELECT
                employee_id,
                name,
                department,
                position_name AS current_position,
                attrition_risk_score,
                attrition_risk
            FROM employee_talent_data
            WHERE attrition_risk IS NOT NULL AND attrition_risk != ''
            ORDER BY attrition_risk_score DESC
            LIMIT 50
            """
        )
        return rows
    except Exception:
        return []


# ── 员工培训计划表 ─────────────────────────────────────


def get_training_list():
    """查询员工培训计划列表"""
    try:
        rows = query_all(
            "SELECT employee_id, name, training_plan, is_completed, created_at "
            "FROM employee_training_plan ORDER BY created_at DESC"
        )
        return rows
    except Exception:
        return []


def add_training(employee_id, name, training_plan):
    """添加员工培训计划"""
    try:
        execute(
            "INSERT INTO employee_training_plan (employee_id, name, training_plan) VALUES (%s, %s, %s)",
            (employee_id, name, training_plan),
        )
        return True
    except Exception:
        return False


def _split_training_names(text):
    """将逗号/顿号分隔的培训名称拆分为列表"""
    if not text:
        return []
    import re
    return [s.strip() for s in re.split(r"[、,，]", str(text)) if s.strip()]


def update_training_status(employee_id, training_plan, is_completed):
    """更新培训完成状态，同步更新 employee_ability.training_completed"""
    try:
        # 1. 更新培训计划表
        execute(
            "UPDATE employee_training_plan SET is_completed = %s WHERE employee_id = %s AND training_plan = %s",
            (is_completed, employee_id, training_plan),
        )

        # 2. 同步更新 employee_ability.training_completed
        ability = query_one(
            "SELECT training_completed FROM employee_ability WHERE employee_id = %s",
            (employee_id,),
        )

        if is_completed:
            # 标记完成 → 添加培训
            new_trainings = _split_training_names(training_plan)
            if not new_trainings:
                return True

            if ability:
                existing_set = set(_split_training_names(ability["training_completed"]))
                to_add = [t for t in new_trainings if t not in existing_set]
                if to_add:
                    separator = "、" if ability["training_completed"] else ""
                    new_value = ability["training_completed"] + separator + "、".join(to_add)
                    execute(
                        "UPDATE employee_ability SET training_completed = %s WHERE employee_id = %s",
                        (new_value, employee_id),
                    )
            else:
                name_row = query_one(
                    "SELECT name FROM employee_training_plan WHERE employee_id = %s LIMIT 1",
                    (employee_id,),
                )
                emp_name = name_row["name"] if name_row else ""
                execute(
                    "INSERT INTO employee_ability (employee_id, name, training_completed) VALUES (%s, %s, %s)",
                    (employee_id, emp_name, "、".join(new_trainings)),
                )
        else:
            # 撤销完成 → 从 ability 中移除这些培训
            if ability and ability["training_completed"]:
                remove_set = set(_split_training_names(training_plan))
                remaining = [t for t in _split_training_names(ability["training_completed"]) if t not in remove_set]
                new_value = "、".join(remaining) if remaining else ""
                execute(
                    "UPDATE employee_ability SET training_completed = %s WHERE employee_id = %s",
                    (new_value, employee_id),
                )
        return True
    except Exception:
        return False


def delete_training(employee_id, training_plan):
    """删除培训计划"""
    try:
        execute(
            "DELETE FROM employee_training_plan WHERE employee_id = %s AND training_plan = %s",
            (employee_id, training_plan),
        )
        return True
    except Exception:
        return False


# ── 部门列表 ───────────────────────────────────────────


def get_departments():
    """从员工表获取所有部门列表"""
    try:
        rows = query_all(
            "SELECT DISTINCT department FROM employee_talent_data "
            "WHERE department IS NOT NULL AND department != '' ORDER BY department"
        )
        return [r["department"] for r in rows]
    except Exception:
        return []
