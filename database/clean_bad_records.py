"""清理包含模板变量的脏数据"""
import sys
sys.path.insert(0, '.')
from backend.db import query_all, execute

rows = query_all(
    "SELECT id, employee_id, name FROM potential_assessment_records "
    "WHERE name LIKE '%{{%' OR employee_id LIKE '%{{%' "
    "OR name = '' OR employee_id = ''"
)
print(f'脏数据: {len(rows)} 条')
for r in rows:
    print(f'  id={r["id"]} emp={r["employee_id"]} name={r["name"]}')
    execute('DELETE FROM potential_assessment_records WHERE id = %s', (r['id'],))

if not rows:
    print('没有脏数据，数据库已干净')
else:
    print(f'已清理 {len(rows)} 条脏数据')
