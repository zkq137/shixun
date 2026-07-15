"""创建 potential_assessment_records 表 - 存储人才潜力评估记录"""
from backend.db import get_connection

conn = get_connection()
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS potential_assessment_records (
        id              INT PRIMARY KEY AUTO_INCREMENT,
        employee_id     VARCHAR(20) NOT NULL,
        name            VARCHAR(50) NOT NULL,
        assessment_detail TEXT COMMENT '评估详情',
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE INDEX uq_employee_id (employee_id),
        INDEX idx_created (created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
""")

print("✅ potential_assessment_records 表创建/已存在")

cursor.execute("SELECT COUNT(*) AS cnt FROM potential_assessment_records")
count = cursor.fetchone()["cnt"]
print(f"📋 当前记录数: {count}")

cursor.close()
conn.close()
