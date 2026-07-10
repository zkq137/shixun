"""创建 succession_candidates 表（仅建表，不导入数据）"""
import sys
sys.path.insert(0, 'D:/Shixun/shixun')

from backend.db import get_connection

conn = get_connection()
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS succession_candidates (
        succession_id         INT AUTO_INCREMENT PRIMARY KEY COMMENT '继任ID',
        candidate_employee_id VARCHAR(20)  NOT NULL COMMENT '候选员工工号',
        target_position       VARCHAR(100) NOT NULL COMMENT '待继任岗位',
        match_score           DECIMAL(5,2)          COMMENT '岗位匹配度',
        succession_level      TINYINT               COMMENT '继任梯队(1/2/3)',
        FOREIGN KEY (candidate_employee_id) REFERENCES employee_talent_data(employee_id)
    )
""")
conn.commit()
print("表 succession_candidates 创建成功")

cursor.execute("DESCRIBE succession_candidates")
print(f"{'字段':20} {'类型':20} {'键':6} {'备注'}")
print("-" * 60)
for r in cursor.fetchall():
    print(f"{r['Field']:20} {r['Type']:20} {r['Key']:6} {r.get('Extra', '')}")

cursor.close()
conn.close()
