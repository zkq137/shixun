"""杀掉卡住的连接释放元数据锁"""
import sys
sys.path.insert(0, 'D:/Shixun/shixun')
from backend.db import get_connection

c = get_connection()
cur = c.cursor()

# 杀掉等待 metadata lock 的连接
cur.execute("SELECT Id FROM information_schema.processlist WHERE State LIKE '%metadata lock%'")
ids = [str(r["Id"]) for r in cur.fetchall()]
for i in ids:
    cur.execute(f"KILL {i}")
    print(f"KILL {i}")

# 杀掉 Sleep > 100 秒的连接
cur.execute("SELECT Id FROM information_schema.processlist WHERE Command='Sleep' AND Time > 100 AND Id != CONNECTION_ID()")
ids2 = [str(r["Id"]) for r in cur.fetchall()]
for i in ids2:
    cur.execute(f"KILL {i}")
    print(f"KILL sleep {i}")

c.commit()
print("清理完成，可以建表了")
cur.close()
c.close()
