USE talent_pipeline_platform;

CREATE TABLE IF NOT EXISTS succession_candidates (
    succession_id         INT AUTO_INCREMENT PRIMARY KEY COMMENT '继任ID',
    candidate_employee_id VARCHAR(20)  NOT NULL COMMENT '候选员工工号',
    target_position       VARCHAR(100) NOT NULL COMMENT '待继任岗位',
    match_score           DECIMAL(5,2)          COMMENT '岗位匹配度',
    succession_level      TINYINT               COMMENT '继任梯队(1/2/3)'
) COMMENT='继任候选表';
