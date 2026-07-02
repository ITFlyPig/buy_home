"""生成小学导航页数据 JS 文件

优先从数据库读取数据，若数据库不可用则回退到JSON文件
"""
import json
from pathlib import Path

try:
    from db_manager import get_db
    HAS_DB = True
except ImportError:
    HAS_DB = False

BASE_DIR = Path(__file__).parent.parent.parent
RAW_DATA_PATH = BASE_DIR / "data" / "raw" / "rxyj_all_schools.json"

schools = []

if HAS_DB:
    try:
        db = get_db()
        schools_raw = db.get_all_schools()
        schools = [dict(row) for row in schools_raw]
        db.close()
        print(f"[数据库] 读取学校数据: {len(schools)} 所")
    except Exception as e:
        print(f"[数据库] 读取失败: {e}, 回退到JSON文件")

if not schools:
    with open(RAW_DATA_PATH, "r", encoding="utf-8") as f:
        schools = json.load(f)

# 小学列表（有对口初中的）
primary_schools = []
for s in schools:
    if s['school_type'] in ('小学', '九年一贯制'):
        primary_schools.append({
            'name': s['school_name'],
            'district': s['district'],
            'type': s['school_type'],
            'nature': s['school_nature'],
            'address': s.get('address', ''),
            'direct_middle_school': s.get('direct_middle_school', ''),
            'communities_hj': s.get('communities_hj', []),
            'communities_xhzr': s.get('communities_xhzr', []),
            'community_count': s.get('community_count', 0),
            'student_count': s.get('student_count', 0),
            'class_count': s.get('class_count', 0),
            'teacher_count': s.get('teacher_count', 0),
        })

# 中学列表
middle_schools = {}
for s in schools:
    if s['school_type'] in ('初中', '九年一贯制'):
        middle_schools[s['school_name']] = {
            'name': s['school_name'],
            'district': s['district'],
            'type': s['school_type'],
            'nature': s['school_nature'],
            'address': s.get('address', ''),
        }

# 区域列表
districts = sorted(set(s['district'] for s in primary_schools))

print(f"小学: {len(primary_schools)} 所")
print(f"中学: {len(middle_schools)} 所")
print(f"有对口初中的小学: {len([s for s in primary_schools if s['direct_middle_school']])}")
print(f"区域: {districts}")

# 生成 JS
js = f"""// 自动生成 - 杭州小学导航数据
// 数据来源：浙里办「入学早知道」https://rxyj.hzedu.gov.cn
// 生成时间：2026-06-27

export const primarySchools = {json.dumps(primary_schools, ensure_ascii=False)};

export const middleSchools = {json.dumps(middle_schools, ensure_ascii=False)};

export const primaryDistricts = {json.dumps(districts, ensure_ascii=False)};
"""

out_path = Path('/Users/yanxi/Downloads/0绿城/kiro-data/data-warehouse/杭州买房指南/visualization/data/primary_data.js')
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(js)
print(f"\n[保存] {out_path} ({out_path.stat().st_size / 1024:.0f} KB)")
