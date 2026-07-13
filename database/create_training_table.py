"""创建 employee_training_plan 表（仅建表，不导入数据）"""
import sys
sys.path.insert(0, 'D:/Shixun/shixun')

from backend.db import get_connection

conn = get_connection()
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS employee_training_plan (
        id              BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
        employee_id     VARCHAR(20)  NOT NULL COMMENT '员工ID',
        name            VARCHAR(50)  NOT NULL COMMENT '员工姓名',
        training_plan   VARCHAR(200) NOT NULL COMMENT '培训计划',
        is_completed    TINYINT(1)   DEFAULT 0 COMMENT '是否完成(0-未完成, 1-已完成)',
        created_at      DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
        updated_at      DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
    ) COMMENT='员工培训计划表'
""")
conn.commit()
print("表 employee_training_plan 创建成功")

cursor.execute("DESCRIBE employee_training_plan")
print(f"{'字段':20} {'类型':20} {'键':6} {'备注'}")
print("-" * 60)
for r in cursor.fetchall():
    print(f"{r['Field']:20} {r['Type']:20} {r['Key']:6} {r.get('Extra', '')}")

cursor.close()
conn.close()
