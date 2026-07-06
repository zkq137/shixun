import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "员工人才梯队数据集_增强版（1000人21字段）.csv"
SQL_PATH = ROOT / "database" / "import_employee_dataset.sql"
BATCH = "initial_csv_20260706"


def sql_value(value):
    if value is None:
        return "NULL"
    text = str(value).strip()
    if text == "":
        return "NULL"
    return "'" + text.replace("\\", "\\\\").replace("'", "''") + "'"


def sql_number(value):
    if value is None:
        return "NULL"
    text = str(value).strip()
    if text == "":
        return "NULL"
    return text


def split_tags(value):
    if not value:
        return []
    return [item.strip() for item in str(value).split("、") if item.strip()]


def main():
    statements = [
        "USE talent_pipeline_platform;",
        "SET NAMES utf8mb4;",
        "START TRANSACTION;",
    ]

    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    for row in rows:
        employee_no = row["员工工号"].strip()
        statements.append(
            "INSERT INTO employees "
            "(employee_no, name, department, position_name, job_level_group, job_level, manager_employee_no) "
            "VALUES "
            f"({sql_value(employee_no)}, {sql_value(row['姓名'])}, {sql_value(row['所属部门'])}, "
            f"{sql_value(row['岗位名称'])}, {sql_value(row['职级层级'])}, {sql_value(row['职级'])}, "
            f"{sql_value(row['上级工号'])}) "
            "ON DUPLICATE KEY UPDATE "
            "name = VALUES(name), department = VALUES(department), position_name = VALUES(position_name), "
            "job_level_group = VALUES(job_level_group), job_level = VALUES(job_level), "
            "manager_employee_no = VALUES(manager_employee_no);"
        )
        statements.append(f"SET @employee_id = (SELECT id FROM employees WHERE employee_no = {sql_value(employee_no)});")

        statements.append(
            "INSERT INTO employee_profiles "
            "(employee_id, age, gender, tenure_years, base_salary, salary_coefficient, work_mode) "
            "VALUES "
            f"(@employee_id, {sql_number(row['年龄'])}, {sql_value(row['性别'])}, "
            f"{sql_number(row['司龄(年)'])}, {sql_number(row['基本年薪(元)'])}, "
            f"{sql_number(row['薪酬系数'])}, {sql_value(row['办公方式'])}) "
            "ON DUPLICATE KEY UPDATE "
            "age = VALUES(age), gender = VALUES(gender), tenure_years = VALUES(tenure_years), "
            "base_salary = VALUES(base_salary), salary_coefficient = VALUES(salary_coefficient), "
            "work_mode = VALUES(work_mode);"
        )

        for skill in split_tags(row["技能标签"]):
            statements.append(
                "INSERT IGNORE INTO employee_skills (employee_id, skill_name) "
                f"VALUES (@employee_id, {sql_value(skill)});"
            )

        for training in split_tags(row["已完成培训"]):
            statements.append(
                "INSERT IGNORE INTO employee_trainings (employee_id, training_name) "
                f"VALUES (@employee_id, {sql_value(training)});"
            )

        statements.append(
            "INSERT INTO talent_assessments "
            "(employee_id, performance_score, potential_score, potential_level, talent_tag, assessment_batch) "
            "VALUES "
            f"(@employee_id, {sql_number(row['绩效评分'])}, {sql_number(row['潜力评分'])}, "
            f"{sql_value(row['潜力等级'])}, {sql_value(row['人才标签'])}, {sql_value(BATCH)});"
        )

        statements.append(
            "INSERT INTO turnover_risk_records "
            "(employee_id, risk_score, risk_level) "
            "VALUES "
            f"(@employee_id, {sql_number(row['流失风险分'])}, {sql_value(row['流失风险'])});"
        )

    statements.append("COMMIT;")
    SQL_PATH.write_text("\n".join(statements) + "\n", encoding="utf-8")
    print(f"Generated {SQL_PATH}")
    print(f"Rows: {len(rows)}")


if __name__ == "__main__":
    main()
