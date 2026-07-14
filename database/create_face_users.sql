USE talent_pipeline_platform;

CREATE TABLE IF NOT EXISTS face_users (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
  face_encoding LONGTEXT NOT NULL COMMENT '人脸特征编码(JSON数组)',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) COMMENT='人脸登录用户表';
