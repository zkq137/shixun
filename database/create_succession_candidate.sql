-- 创建继任候选表
CREATE TABLE IF NOT EXISTS succession_candidate (
  succession_id INT AUTO_INCREMENT COMMENT '继任ID',
  candidate_employee_id VARCHAR(20) NOT NULL COMMENT '候选员工工号',
  employee_name VARCHAR(50) DEFAULT NULL COMMENT '员工姓名',
  department VARCHAR(50) DEFAULT NULL COMMENT '所属部门',
  target_position VARCHAR(100) NOT NULL COMMENT '待继任岗位',
  match_score DECIMAL(5,2) DEFAULT NULL COMMENT '员工和岗位匹配评分',
  succession_level VARCHAR(20) DEFAULT NULL COMMENT '继任梯队',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (succession_id),
  KEY idx_candidate (candidate_employee_id),
  KEY idx_target_position (target_position),
  CONSTRAINT fk_succession_candidate FOREIGN KEY (candidate_employee_id) REFERENCES employee_talent_data(employee_id) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_succession_position FOREIGN KEY (target_position) REFERENCES position_profile(position_name) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='继任候选表';
