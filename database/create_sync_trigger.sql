-- 创建触发器：更新employee_potential时自动同步到employee_talent_data
-- 先删除已存在的同名触发器
DROP TRIGGER IF EXISTS trg_employee_potential_update;

-- 修改分隔符，避免触发体中的分号被误执行
DELIMITER $$

CREATE TRIGGER trg_employee_potential_update
AFTER UPDATE ON employee_potential
FOR EACH ROW
BEGIN
    UPDATE employee_talent_data
    SET potential_score = NEW.potential_score,
        potential_level = NEW.potential_level
    WHERE employee_id = NEW.employee_id;
END$$

DELIMITER ;
