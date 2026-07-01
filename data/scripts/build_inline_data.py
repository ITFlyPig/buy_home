"""生成可内嵌到 index.html 的小学数据 JS 变量"""
import json

with open('/Users/yanxi/Downloads/0绿城/kiro-data/data-warehouse/杭州买房指南/data/raw/rxyj_all_schools.json') as f:
    schools = json.load(f)

# 小学列表（有对口初中的优先）
primary_list = []
for s in schools:
    if s['school_type'] in ('小学', '九年一贯制'):
        primary_list.append({
            'name': s['school_name'],
            'district': s['district'],
            'type': s['school_type'],
            'nature': s['school_nature'],
            'address': s.get('address', ''),
            'middle': s.get('direct_middle_school', ''),
            'communities': s.get('communities_hj', []),
            'community_count': s.get('community_count', 0),
            'student_count': s.get('student_count', 0),
            'class_count': s.get('class_count', 0),
            'teacher_count': s.get('teacher_count', 0),
        })

# 区域列表
districts = sorted(set(s['district'] for s in primary_list))

# 生成压缩 JSON
js_code = f"""// === 浙里办「入学早知道」爬取数据 (493所学校, 2026年) ===
const rxyjPrimarySchools = {json.dumps(primary_list, ensure_ascii=False, separators=(',',':'))};
const rxyjDistricts = {json.dumps(districts, ensure_ascii=False)};"""

out_path = '/Users/yanxi/Downloads/0绿城/kiro-data/data-warehouse/杭州买房指南/visualization/data/primary_inline.js'
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(js_code)
print(f"[OK] {out_path}")
print(f"  小学: {len(primary_list)} 所")
print(f"  有对口初中: {len([s for s in primary_list if s['middle']])} 所")
print(f"  区域: {districts}")
print(f"  文件大小: {len(js_code)/1024:.0f} KB")
