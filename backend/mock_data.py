from datetime import date


def get_overview():
    return {
        "employeeCount": 1000,
        "keyPositions": 48,
        "readyNowSuccessors": 36,
        "highRiskEmployees": 29,
        "completionRate": 0.73,
        "lastUpdated": date.today().isoformat(),
    }


def get_nine_box():
    return [
        {"cell": "高潜-高绩效", "count": 96, "level": "A"},
        {"cell": "高潜-中绩效", "count": 122, "level": "A"},
        {"cell": "高潜-低绩效", "count": 31, "level": "B"},
        {"cell": "中潜-高绩效", "count": 141, "level": "A"},
        {"cell": "中潜-中绩效", "count": 287, "level": "B"},
        {"cell": "中潜-低绩效", "count": 88, "level": "C"},
        {"cell": "低潜-高绩效", "count": 61, "level": "B"},
        {"cell": "低潜-中绩效", "count": 116, "level": "C"},
        {"cell": "低潜-低绩效", "count": 58, "level": "C"},
    ]


def get_succession_candidates():
    return [
        {
            "position": "华东大区销售总监",
            "candidate": "周子昂",
            "readiness": "Ready Now",
            "matchScore": 92,
            "risk": "低",
        },
        {
            "position": "算法平台负责人",
            "candidate": "赵亦凡",
            "readiness": "1-2年",
            "matchScore": 86,
            "risk": "中",
        },
        {
            "position": "供应链运营经理",
            "candidate": "宋嘉禾",
            "readiness": "Ready Now",
            "matchScore": 89,
            "risk": "低",
        },
        {
            "position": "海外市场负责人",
            "candidate": "陈书宁",
            "readiness": "2-3年",
            "matchScore": 78,
            "risk": "中",
        },
    ]


def get_risk_alerts():
    return [
        {
            "employee": "李辰",
            "department": "技术中心",
            "riskLevel": "高",
            "reason": "近30天出勤波动 + 绩效下滑",
            "action": "安排一对一访谈并制定保留方案",
        },
        {
            "employee": "王悦",
            "department": "销售中心",
            "riskLevel": "中",
            "reason": "关键岗位替补不足",
            "action": "启动跨团队轮岗培养",
        },
        {
            "employee": "林涛",
            "department": "供应链",
            "riskLevel": "高",
            "reason": "技能断层，岗位依赖度高",
            "action": "双人备份 + 导师制带教",
        },
    ]


def get_training_plans():
    return [
        {
            "name": "战略领导力提升计划",
            "targetGroup": "高潜经理",
            "duration": "12周",
            "progress": 0.45,
        },
        {
            "name": "关键岗位继任加速营",
            "targetGroup": "一级继任候选人",
            "duration": "8周",
            "progress": 0.62,
        },
        {
            "name": "数据化管理实战课",
            "targetGroup": "业务中层",
            "duration": "6周",
            "progress": 0.33,
        },
    ]
