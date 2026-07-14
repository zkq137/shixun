"""提取CSV中缺失的岗位信息，用于填充position_profile表"""
import csv
from collections import defaultdict

# 现有岗位
existing = {
    '产品副总裁','产品管理总监','产品经理','产品设计师','人力资源经理','信息技术总监',
    '前端开发工程师','后端开发工程师','客户成功总监','客户成功经理','工程副总裁','市场副总裁',
    '技术项目经理','数据分析师','数据工程师','数据科学总监','数据科学经理','文档工程师',
    '测试工程师','用户体验设计师','研发经理','行政助理','设计经理','财务副总裁','财务经理',
    '软件工程师','运维工程师','销售副总裁','销售经理','首席产品官','首席信息官','首席执行官',
    '首席技术官','首席营收官','首席财务官','首席运营官',
}

# 收集缺失岗位的数据
missing_data = defaultdict(lambda: {
    'depts': set(), 'levels': set(), 'ranks': set(),
    'skills': set(), 'trainings': set(), 'work_modes': set(),
    'count': 0,
})

with open('D:/Shixun/shixun/员工人才梯队数据集_增强版（1000人21字段）.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        pos = row['岗位名称']
        if pos not in existing:
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

# 岗位类型映射
def infer_position_type(pos_name, level, is_mgr):
    mgmt_keywords = ['经理', '总监', '总裁', '官', '主管', '主任']
    tech_keywords = ['工程师', '开发', '运维', '安全', '数据', '分析']
    design_keywords = ['设计', 'UI', 'UX']
    support_keywords = ['专员', '助理', '会计', '客服', '销售']
    
    if is_mgr:
        return '管理岗'
    if any(k in pos_name for k in tech_keywords):
        return '技术岗'
    if any(k in pos_name for k in design_keywords):
        return '设计岗'
    if any(k in pos_name for k in support_keywords):
        return '支撑岗'
    return '支撑岗'

# 判断是否管理岗
def is_manager_position(pos_name, level, rank):
    mgr_keywords = ['总裁', '总监', '经理', '主管', '官']
    if any(k in pos_name for k in mgr_keywords):
        return '是'
    return '否'

# 生成插入SQL
print('-- 以下为缺失岗位的INSERT语句')
print()

for pos in sorted(missing_data.keys()):
    d = missing_data[pos]
    level = next(iter(d['levels'])) if d['levels'] else ''
    rank = next(iter(d['ranks'])) if d['ranks'] else ''
    dept = next(iter(d['depts'])) if d['depts'] else ''
    work_mode = next(iter(d['work_modes'])) if d['work_modes'] else ''
    is_mgr = is_manager_position(pos, level, rank)
    pos_type = infer_position_type(pos, level, is_mgr)
    
    core_skills = '、'.join(sorted(d['skills'])) if d['skills'] else ''
    trainings = '、'.join(sorted(d['trainings'])) if d['trainings'] else ''
    
    # 绩效要求
    perf_req = '绩效3分以上' if level in ('员工层', '主管层') else '绩效4分以上'
    # 司龄要求
    tenure_req = '1年以上' if level == '员工层' else ('2年以上' if level == '主管层' else '3年以上')
    # 办公方式要求
    if '混合办公' in d['work_modes'] and '现场办公' in d['work_modes']:
        work_mode_req = '现场或混合办公'
    elif '混合办公' in d['work_modes'] and '远程办公' in d['work_modes']:
        work_mode_req = '远程或混合办公'
    elif len(d['work_modes']) == 1:
        work_mode_req = next(iter(d['work_modes']))
    else:
        work_mode_req = '、'.join(sorted(d['work_modes']))
    
    # 加分技能（取培训中不包含在核心技能里的）
    bonus_set = d['trainings'] - d['skills']
    bonus_skills = '、'.join(sorted(bonus_set)) if bonus_set else ''
    
    # 适配说明
    fit_desc = f"适合{pos}岗位要求的人才"
    
    sql = f"""INSERT IGNORE INTO position_profile (position_name, department, job_level, rank_name, position_type, core_skills, bonus_skills, required_training, performance_requirement, tenure_requirement, work_mode_requirement, is_manager, fit_description)
VALUES ('{pos}', '{dept}', '{level}', '{rank}', '{pos_type}', '{core_skills}', '{bonus_skills}', '{trainings}', '{perf_req}', '{tenure_req}', '{work_mode_req}', '{is_mgr}', '{fit_desc}');"""
    
    print(sql)
    print()

print('-- 完成')
