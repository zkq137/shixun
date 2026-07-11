"""检查数据库锁和创建 succession_candidates 表"""
import sys
sys.path.insert(0, 'D:/Shixun/shixun')
from backend.db import get_connection

c = get_connection()
cur = c.cursor()

cur.execute("SHOW OPEN TABLES WHERE In_use > 0")
locked = cur.fetchall()
print("被锁的表:", locked)

cur.execute("SHOW PROCESSLIST")
print("\n当前连接:")
for r in cur.fetchall():
    print(f"  {r['Id']:6} {r['User']:10} {r['db']:25} {r['Command']:10} {r['Time']:6} {r['State'] or '':20} {r['Info'] or ''}")

cur.close()
c.close()
