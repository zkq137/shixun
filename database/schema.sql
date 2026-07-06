USE talent_pipeline_platform;

CREATE TABLE IF NOT EXISTS employees (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  employee_no VARCHAR(32) NOT NULL UNIQUE COMMENT '员工工号',
  name VARCHAR(50) NOT NULL COMMENT '姓名',
  department VARCHAR(100) COMMENT '所属部门',
  position_name VARCHAR(100) COMMENT '岗位名称',
  job_level_group VARCHAR(50) COMMENT '职级层级',
  job_level VARCHAR(50) COMMENT '职级',
  manager_employee_no VARCHAR(32) COMMENT '上级工号',
  status VARCHAR(20) DEFAULT 'active' COMMENT '员工状态',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_department (department),
  KEY idx_position_name (position_name),
  KEY idx_manager_employee_no (manager_employee_no)
) COMMENT='员工基础信息表';

CREATE TABLE IF NOT EXISTS employee_profiles (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  employee_id BIGINT NOT NULL,
  age INT COMMENT '年龄',
  gender VARCHAR(10) COMMENT '性别',
  tenure_years DECIMAL(5,2) COMMENT '司龄年数',
  base_salary DECIMAL(12,2) COMMENT '基本年薪',
  salary_coefficient DECIMAL(6,3) COMMENT '薪酬系数',
  work_mode VARCHAR(50) COMMENT '办公方式',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_employee_profile (employee_id),
  CONSTRAINT fk_profile_employee
    FOREIGN KEY (employee_id) REFERENCES employees(id)
    ON DELETE CASCADE
) COMMENT='员工画像扩展表';

CREATE TABLE IF NOT EXISTS employee_skills (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  employee_id BIGINT NOT NULL,
  skill_name VARCHAR(100) NOT NULL COMMENT '技能名称',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_employee_skill (employee_id, skill_name),
  KEY idx_skill_name (skill_name),
  CONSTRAINT fk_skill_employee
    FOREIGN KEY (employee_id) REFERENCES employees(id)
    ON DELETE CASCADE
) COMMENT='员工技能标签表';

CREATE TABLE IF NOT EXISTS employee_trainings (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  employee_id BIGINT NOT NULL,
  training_name VARCHAR(100) NOT NULL COMMENT '培训名称',
  completed_at DATE NULL COMMENT '完成日期',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_employee_training (employee_id, training_name),
  KEY idx_training_name (training_name),
  CONSTRAINT fk_training_employee
    FOREIGN KEY (employee_id) REFERENCES employees(id)
    ON DELETE CASCADE
) COMMENT='员工培训记录表';

CREATE TABLE IF NOT EXISTS talent_assessments (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  employee_id BIGINT NOT NULL,
  performance_score DECIMAL(5,2) COMMENT '绩效评分',
  potential_score DECIMAL(5,2) COMMENT '潜力评分',
  potential_level VARCHAR(50) COMMENT '潜力等级',
  talent_tag VARCHAR(50) COMMENT '人才标签',
  position_fit_score DECIMAL(5,2) COMMENT '岗位适配度',
  nine_grid_cell VARCHAR(50) COMMENT '人才九宫格位置',
  assessment_batch VARCHAR(50) COMMENT '评估批次',
  assessment_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_assessment_employee (employee_id),
  KEY idx_assessment_batch (assessment_batch),
  CONSTRAINT fk_assessment_employee
    FOREIGN KEY (employee_id) REFERENCES employees(id)
    ON DELETE CASCADE
) COMMENT='人才评估记录表';

CREATE TABLE IF NOT EXISTS turnover_risk_records (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  employee_id BIGINT NOT NULL,
  risk_score DECIMAL(5,2) COMMENT '流失风险分',
  risk_level VARCHAR(50) COMMENT '流失风险等级',
  risk_reason TEXT COMMENT '风险原因',
  intervention_plan TEXT COMMENT '干预方案',
  assessment_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_turnover_employee (employee_id),
  KEY idx_risk_level (risk_level),
  CONSTRAINT fk_turnover_employee
    FOREIGN KEY (employee_id) REFERENCES employees(id)
    ON DELETE CASCADE
) COMMENT='流失风险记录表';

CREATE TABLE IF NOT EXISTS succession_candidates (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  target_position_name VARCHAR(100) NOT NULL COMMENT '目标关键岗位',
  candidate_employee_id BIGINT NOT NULL COMMENT '继任候选人',
  succession_level TINYINT NOT NULL COMMENT '继任梯队级别：1/2/3',
  readiness_level VARCHAR(50) COMMENT '准备度',
  match_score DECIMAL(5,2) COMMENT '匹配分',
  gap_analysis TEXT COMMENT '能力差距',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_target_position (target_position_name),
  KEY idx_candidate_employee (candidate_employee_id),
  CONSTRAINT fk_successor_employee
    FOREIGN KEY (candidate_employee_id) REFERENCES employees(id)
    ON DELETE CASCADE
) COMMENT='关键岗位继任梯队表';

CREATE TABLE IF NOT EXISTS training_plans (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  employee_id BIGINT NOT NULL,
  plan_name VARCHAR(100) NOT NULL COMMENT '计划名称',
  target_position_name VARCHAR(100) COMMENT '目标岗位',
  weakness_summary TEXT COMMENT '短板总结',
  recommended_courses TEXT COMMENT '推荐课程',
  plan_status VARCHAR(30) DEFAULT 'pending' COMMENT '计划状态',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_training_plan_employee (employee_id),
  KEY idx_plan_status (plan_status),
  CONSTRAINT fk_plan_employee
    FOREIGN KEY (employee_id) REFERENCES employees(id)
    ON DELETE CASCADE
) COMMENT='个人发展计划表';

CREATE TABLE IF NOT EXISTS promotion_decisions (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  employee_id BIGINT NOT NULL,
  target_position_name VARCHAR(100) COMMENT '目标岗位',
  recommendation VARCHAR(50) COMMENT '晋升建议',
  reason TEXT COMMENT '建议理由',
  risk_warning TEXT COMMENT '风险提示',
  decision_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_promotion_employee (employee_id),
  CONSTRAINT fk_promotion_employee
    FOREIGN KEY (employee_id) REFERENCES employees(id)
    ON DELETE CASCADE
) COMMENT='晋升决策记录表';
