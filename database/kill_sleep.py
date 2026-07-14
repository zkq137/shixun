"""杀掉长时间睡眠的数据库连接"""
import sys
sys.path.insert(0, 'D:/Shixun/shixun')
from backend.db import get_connection

conn = get_connection()
cur = conn.cursor()

cur.execute("SELECT Id FROM information_schema.processlist WHERE Command='Sleep' AND Time > 10 AND Id != CONNECTION_ID()")
ids = [str(r['Id']) for r in cur.fetchall()]
print(f"找到 {len(ids)} 个睡眠连接")
for i in ids:
    try:
        cur.execute(f"KILL {i}")
        print(f"  KILL {i}")
    except Exception as e:
        print(f"  KILL {i} 失败: {e}")

conn.commit()
print("清理完成")

# 检查 employee_potential 表
cur.execute("SELECT COUNT(*) AS cnt FROM employee_potential")
print(f"employee_potential 行数: {cur.fetchone()['cnt']}")

cur.execute("SELECT employee_id, name, potential_score FROM employee_potential LIMIT 3")
for r in cur.fetchall():
    print(f"  {r['employee_id']} | {r['name']} | {r['potential_score']}")

cur.close()
conn.close()
