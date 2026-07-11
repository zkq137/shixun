"""创建 position_match 表并从 employee_talent_data 导入数据"""
import sys
sys.path.insert(0, 'D:/Shixun/shixun')

from backend.db import get_connection

conn = get_connection()
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS position_match (
        employee_id   VARCHAR(20) PRIMARY KEY,
        name          VARCHAR(50) NOT NULL,
        position_name VARCHAR(100),
        match_score   DECIMAL(5,2)
    )
""")

cursor.execute("""
    INSERT IGNORE INTO position_match (employee_id, name, position_name, match_score)
    SELECT employee_id, name, position_name, NULL
    FROM employee_talent_data
""")
conn.commit()
print("表 position_match 创建成功，导入", cursor.rowcount, "条记录")

cursor.execute("SELECT COUNT(*) AS cnt FROM position_match")
print("总行数:", cursor.fetchone()["cnt"])

print("\n前5条示例：")
cursor.execute("SELECT * FROM position_match LIMIT 5")
for r in cursor.fetchall():
    print(f"  {r['employee_id']} | {r['name']} | {r['position_name']} | {r['match_score']}")

cursor.close()
conn.close()
