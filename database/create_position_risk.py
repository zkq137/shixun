"""创建岗位风险表 position_risk 并导入数据"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql.cursors
from backend.db import get_connection, execute

conn = get_connection()
cursor = conn.cursor(pymysql.cursors.DictCursor)

# 1. 创建表
cursor.execute("""
    CREATE TABLE IF NOT EXISTS position_risk (
        id              INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
        position_name   VARCHAR(100) NOT NULL UNIQUE COMMENT '岗位名称',
        total_risk_score DECIMAL(5,2) COMMENT '岗位风险总分(0-100)',
        risk_level      VARCHAR(20) COMMENT '岗位风险等级: 高风险/低风险',
        created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        KEY idx_risk_level (risk_level)
    ) COMMENT='岗位风险研判表'
""")
print("✅ 表 position_risk 创建成功")

# 2. 查询各岗位聚合数据
cursor.execute("""
    SELECT 
        etd.position_name,
        COUNT(*) AS cnt,
        ROUND(AVG(etd.attrition_risk_score), 2) AS avg_risk_score,
        ROUND(AVG(etd.potential_score), 2) AS avg_potential,
        ROUND(AVG(etd.performance_score), 2) AS avg_perf
    FROM employee_talent_data etd
    GROUP BY etd.position_name
    ORDER BY etd.position_name
""")
rows = cursor.fetchall()

# 3. 获取每个岗位对应的职级层级
cursor.execute("""
    SELECT DISTINCT position_name, job_level
    FROM employee_talent_data
""")
level_map = {}
for r in cursor.fetchall():
    level_map[r["position_name"]] = r["job_level"]

# 4. 层级关键性得分
level_scores = {
    "决策层": 25,
    "高管层": 20,
    "总监层": 16,
    "经理层": 10,
    "主管层": 5,
    "员工层": 0,
}

# 5. 计算每个岗位的风险分
insert_sql = """
    INSERT INTO position_risk (position_name, total_risk_score, risk_level)
    VALUES (%s, %s, %s)
    ON DUPLICATE KEY UPDATE
        total_risk_score = VALUES(total_risk_score),
        risk_level = VALUES(risk_level)
"""

print("\n=== 岗位风险评分详情 ===")
print(f"{'岗位名称':25} {'人数':5} {'流失风险':10} {'关键性':8} {'替代难度':10} {'潜力损失':10} {'总分':8} {'等级':8}")
print("-" * 90)

inserted = 0
for r in rows:
    name = r["position_name"]
    cnt = int(r["cnt"])
    avg_risk = float(r["avg_risk_score"] or 0)
    avg_pot = float(r["avg_potential"] or 0)
    avg_perf = float(r["avg_perf"] or 0)

    # 获取岗位层级
    level = level_map.get(name, "员工层")
    level_score = level_scores.get(level, 0)

    # --- 计算各维度得分 (总分100) ---

    # 维度1: 流失风险贡献 (0-40分)
    # 平均流失风险分 0-100 映射到 0-40
    risk_dim = min(40, avg_risk * 1.2)

    # 维度2: 关键性 (0-25分)
    critical_dim = level_score

    # 维度3: 替代难度 - 人数越少越难替代 (0-20分)
    if cnt == 1:
        replace_dim = 20
    elif cnt <= 3:
        replace_dim = 15
    elif cnt <= 6:
        replace_dim = 10
    elif cnt <= 15:
        replace_dim = 5
    else:
        replace_dim = 0

    # 维度4: 潜力损失风险 (0-15分)
    # 岗位平均潜力越高，人才流失的损失越大
    if avg_pot >= 80:
        potential_loss = 15
    elif avg_pot >= 70:
        potential_loss = 10
    elif avg_pot >= 60:
        potential_loss = 5
    else:
        potential_loss = 0

    # 综合评分 (0-100)
    total_score = round(risk_dim + critical_dim + replace_dim + potential_loss, 2)

    # 风险等级：>= 60 高风险，否则低风险
    risk_level = "高风险" if total_score >= 60 else "低风险"

    print(f"{name:25} {cnt:5} {avg_risk:<10.2f} {critical_dim:<8} {replace_dim:<10} {potential_loss:<10} {total_score:<8.2f} {risk_level:8}")

    cursor.execute(insert_sql, (name, total_score, risk_level))
    inserted += cursor.rowcount

conn.commit()
print(f"\n✅ 成功导入 {inserted} 条岗位风险数据")

# 验证
cursor.execute("SELECT COUNT(*) AS cnt FROM position_risk")
cnt = cursor.fetchone()["cnt"]
print(f"📊 position_risk 表总记录数: {cnt}")

# 分等级统计
cursor.execute("""
    SELECT risk_level, COUNT(*) AS cnt, ROUND(AVG(total_risk_score), 2) AS avg_score
    FROM position_risk
    GROUP BY risk_level
    ORDER BY FIELD(risk_level, '高风险', '低风险')
""")
print("\n=== 风险等级分布 ===")
for r in cursor.fetchall():
    print(f"  {r['risk_level']}: {r['cnt']} 个岗位, 平均分 {r['avg_score']}")

# 高风险岗位TOP10
cursor.execute("""
    SELECT position_name, total_risk_score, risk_level
    FROM position_risk
    WHERE risk_level = '高风险'
    ORDER BY total_risk_score DESC
    LIMIT 15
""")
high_risk = cursor.fetchall()
if high_risk:
    print("\n=== 高风险岗位TOP15 ===")
    for r in high_risk:
        print(f"  {r['position_name']:25} {r['total_risk_score']:>8.2f}")

cursor.close()
conn.close()
print("\n✅ 完成！")
