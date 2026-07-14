"""创建 employee_potential 表并从 employee_talent_data 导入数据"""
from backend.db import get_connection

conn = get_connection()
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS employee_potential (
        employee_id     VARCHAR(20) PRIMARY KEY,
        name            VARCHAR(50) NOT NULL,
        potential_score DECIMAL(5,2),
        potential_level VARCHAR(30),
        talent_tag      VARCHAR(20)
    )
""")

# 注意：employee_talent_data 中的 potential_score/potential_level 已被删除，
# 因此从 talent_assessments 表获取潜力数据
cursor.execute("""
    INSERT IGNORE INTO employee_potential (employee_id, name, potential_score, potential_level, talent_tag)
    SELECT e.employee_no, e.name, ta.potential_score, ta.potential_level, ta.talent_tag
    FROM employees e
    JOIN talent_assessments ta ON ta.employee_id = e.id
""")
conn.commit()
print(f"表创建成功，导入 {cursor.rowcount} 条记录")

cursor.execute("SELECT COUNT(*) AS cnt FROM employee_potential")
print(f"employee_potential 总行数: {cursor.fetchone()['cnt']}")

print("\n前5条示例：")
cursor.execute("SELECT * FROM employee_potential LIMIT 5")
for r in cursor.fetchall():
    print(f"  {r['employee_id']} | {r['name']} | {r['potential_score']} | {r['potential_level']} | {r['talent_tag']}")

cursor.close()
conn.close()
