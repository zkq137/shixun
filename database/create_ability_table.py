"""创建 employee_ability 表并从 employee_talent_data 导入数据"""
import sys
sys.path.insert(0, 'D:/Shixun/shixun')

from backend.db import get_connection

conn = get_connection()
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS employee_ability (
        employee_id       VARCHAR(20) PRIMARY KEY,
        name              VARCHAR(50) NOT NULL,
        skill_tags        TEXT,
        training_completed TEXT
    )
""")

cursor.execute("""
    INSERT IGNORE INTO employee_ability (employee_id, name, skill_tags, training_completed)
    SELECT employee_id, name, skill_tags, training_completed
    FROM employee_talent_data
""")
conn.commit()
print("表 employee_ability 创建成功，导入", cursor.rowcount, "条记录")

cursor.execute("SELECT COUNT(*) AS cnt FROM employee_ability")
print("总行数:", cursor.fetchone()["cnt"])

print("\n前3条示例：")
cursor.execute("SELECT * FROM employee_ability LIMIT 3")
for r in cursor.fetchall():
    print(" ", r["employee_id"], "|", r["name"], "|",
          (r["skill_tags"] or "")[:30], "|",
          (r["training_completed"] or "")[:30])

cursor.close()
conn.close()
