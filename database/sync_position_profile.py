"""
从1000人CSV中提取缺失的岗位信息，
1) 插入到数据库 position_profile 表
2) 同步更新 岗位画像表.csv
不增加也不减少字段，只添加新岗位。
"""
import csv
import sys
from collections import defaultdict

sys.path.insert(0, 'D:/Shixun/shixun')
from backend.db import get_connection

# ── 1. 读取现有岗位画像CSV ───────────────────────────────
CSV_PATH = 'D:/Shixun/shixun/岗位画像表.csv'

existing_rows = []
with open(CSV_PATH, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    for row in reader:
        existing_rows.append(row)

existing_positions = {r['岗位名称'] for r in existing_rows}
print(f"现有岗位画像CSV中岗位数: {len(existing_positions)}")

# ── 2. 从1000人CSV收集缺失岗位的聚合数据 ─────────────
missing_data = defaultdict(lambda: {
    'depts': set(), 'levels': set(), 'ranks': set(),
    'skills': set(), 'trainings': set(), 'work_modes': set(),
    'count': 0,
})

with open('D:/Shixun/shixun/员工人才梯队数据集_增强版（1000人21字段）.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        pos = row['岗位名称']
        if pos not in existing_positions:
            d = missing_data[pos]
            d['depts'].add(row['所属部门'])
            d['levels'].add(row['职级层级'])
            d['ranks'].add(row['职级'])
            d['work_modes'].add(row['办公方式'])
            for s in row['技能标签'].split('、'):
                if s.strip():
                    d['skills'].add(s.strip())
            for t in row['已完成培训'].split('、'):
                if t.strip():
                    d['trainings'].add(t.strip())
            d['count'] += 1

print(f"需新增的岗位数: {len(missing_data)}")

# ── 3. 辅助函数 ───────────────────────────────────────────

def is_manager_position(pos_name):
    """判断是否为管理岗"""
    mgr = ['总裁', '总监', '经理', '主管', '首席执行官', '首席', '执行官']
    return any(k in pos_name for k in mgr)


def infer_position_type(pos_name):
    """推断岗位类型"""
    mgmt_keywords = ['总裁', '总监', '经理', '主管', '首席执行官', '首席', '执行官']
    tech_keywords = ['工程师', '开发', '运维', '安全', '分析', '技术', '网络', '系统']
    design_keywords = ['设计', 'UI', 'UX']
    support_keywords = ['专员', '助理', '会计', '销售', '客服', '市场', '内容', '运营', '文档', '代表', '招聘']

    if any(k in pos_name for k in mgmt_keywords):
        return '管理岗'
    if any(k in pos_name for k in tech_keywords):
        return '技术岗'
    if any(k in pos_name for k in design_keywords):
        return '设计岗'
    if any(k in pos_name for k in support_keywords):
        return '支撑岗'
    return '支撑岗'


# ── 4. 生成新行并插入数据库 ────────────────────────────
conn = get_connection()
cursor = conn.cursor()

new_rows = []

for pos in sorted(missing_data.keys()):
    d = missing_data[pos]

    # 取出现最多的值
    level = max(d['levels'], key=lambda x: sum(1 for _ in d['levels'])) if d['levels'] else ''
    rank = max(d['ranks'], key=lambda x: sum(1 for _ in d['ranks'])) if d['ranks'] else ''
    dept = max(d['depts'], key=lambda x: sum(1 for _ in d['depts'])) if d['depts'] else ''

    is_mgr = '是' if is_manager_position(pos) else '否'
    pos_type = infer_position_type(pos)

    core_skills = '、'.join(sorted(d['skills'])) if d['skills'] else ''
    trainings = '、'.join(sorted(d['trainings'])) if d['trainings'] else ''

    # 绩效要求
    perf_req = '绩效3分以上' if level in ('员工层', '主管层') else '绩效4分以上'
    # 司龄要求
    if level == '员工层':
        tenure_req = '1年以上'
    elif level == '主管层':
        tenure_req = '2年以上'
    else:
        tenure_req = '3年以上'
    # 办公方式要求
    wm = d['work_modes']
    if '混合办公' in wm and '现场办公' in wm:
        work_mode_req = '现场或混合办公'
    elif '混合办公' in wm and '远程办公' in wm:
        work_mode_req = '远程或混合办公'
    elif len(wm) == 1:
        work_mode_req = next(iter(wm))
    else:
        work_mode_req = '、'.join(sorted(wm))

    # 加分技能 = 培训 - 核心技能
    bonus_set = d['trainings'] - d['skills']
    bonus_skills = '、'.join(sorted(bonus_set)) if bonus_set else ''

    # 适配说明
    fit_desc = f"适合{pos}岗位要求的人才" if not is_manager_position(pos) else f"适合{pos}管理岗位的人才"

    # ── 插入数据库 ──
    sql = """INSERT IGNORE INTO position_profile
(position_name, department, job_level, rank_name, position_type,
 core_skills, bonus_skills, required_training,
 performance_requirement, tenure_requirement, work_mode_requirement,
 is_manager, fit_description)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
    params = (
        pos, dept, level, rank, pos_type,
        core_skills, bonus_skills, trainings,
        perf_req, tenure_req, work_mode_req,
        is_mgr, fit_desc,
    )
    try:
        cursor.execute(sql, params)
        if cursor.rowcount > 0:
            print(f"  ✅ 已插入: {pos}")
        else:
            print(f"  ⏭️  已存在跳过: {pos}")
    except Exception as e:
        print(f"  ❌ 插入失败 {pos}: {e}")

    # ── 构建CSV行 ──
    new_rows.append({
        '岗位名称': pos,
        '所属部门': dept,
        '职级层级': level,
        '职级': rank,
        '岗位类型': pos_type,
        '核心技能': core_skills,
        '加分技能': bonus_skills,
        '必备培训': trainings,
        '绩效要求': perf_req,
        '司龄要求': tenure_req,
        '办公方式要求': work_mode_req,
        '是否管理岗': is_mgr,
        '适配说明': fit_desc,
    })

conn.commit()
cursor.close()
conn.close()

# ── 5. 更新CSV文件 ─────────────────────────────────────
all_rows = existing_rows + new_rows
with open(CSV_PATH, 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(all_rows)

print(f"\n✅ 全部完成！")
print(f"   原岗位画像数: {len(existing_rows)}")
print(f"   新增岗位数: {len(new_rows)}")
print(f"   更新后总数: {len(all_rows)}")
print(f"   已同步更新 {CSV_PATH}")
