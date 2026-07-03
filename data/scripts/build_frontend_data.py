"""
将采集的 JSON 数据转为前端可用的 JS 文件（ES Module）

优先从数据库读取数据，若数据库不可用则回退到JSON文件
"""
import json
import csv
from pathlib import Path

base_dir = Path(__file__).parent.parent

try:
    from db_manager import get_db
    HAS_DB = True
except ImportError:
    HAS_DB = False

schools = []
mappings = []

if HAS_DB:
    try:
        db = get_db()
        schools_raw = db.get_all_schools()
        schools = [dict(row) for row in schools_raw]
        
        mappings_raw = db.get_school_community_mappings()
        mappings = [dict(row) for row in mappings_raw]
        db.close()
        print(f"[数据库] 读取成功: {len(schools)} 所学校, {len(mappings)} 条映射")
    except Exception as e:
        print(f"[数据库] 读取失败: {e}, 回退到JSON文件")
        HAS_DB = False

if not HAS_DB or not schools:
    with open(base_dir / "raw" / "rxyj_all_schools.json", "r", encoding="utf-8") as f:
        schools = json.load(f)

if not HAS_DB or not mappings:
    with open(base_dir / "raw" / "rxyj_all_mappings.json", "r", encoding="utf-8") as f:
        mappings = json.load(f)

# 按学校分组对口小区
school_communities = {}
for m in mappings:
    key = m["campus_code"]
    if key not in school_communities:
        school_communities[key] = {"户籍生": [], "新杭州人": []}
    student_type = m["student_type"]
    if student_type in school_communities[key]:
        school_communities[key][student_type].append(m["community_name"])

# 给学校数据补充对口小区
for s in schools:
    code = s["campus_code"]
    comm = school_communities.get(code, {"户籍生": [], "新杭州人": []})
    s["communities_hj"] = comm["户籍生"]
    s["communities_xhzr"] = comm["新杭州人"]
    s["community_count"] = len(comm["户籍生"]) + len(comm["新杭州人"])

# 从 school_detail.csv 补充 direct_middle_school（列表接口不返回该字段）
detail_csv = base_dir / "processed" / "school_detail.csv"
if detail_csv.exists():
    dms_map = {}
    with open(detail_csv, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            code = row.get("campus_code", "").strip()
            dms = row.get("direct_middle_school", "").strip()
            if code and dms:
                dms_map[code] = dms
    filled = 0
    for s in schools:
        if not s.get("direct_middle_school", "").strip():
            code = s.get("campus_code", "")
            if code in dms_map:
                s["direct_middle_school"] = dms_map[code]
                filled += 1
    print(f"[补充] 从 school_detail.csv 填充 direct_middle_school: {filled} 所学校")

# 从 direct_middle_school 字段提取缺失的初中学校
existing_school_names = set(s["school_name"] for s in schools)
middle_school_info = {}
for s in schools:
    if s.get("direct_middle_school"):
        mid_name = s["direct_middle_school"].strip()
        if mid_name and mid_name not in existing_school_names:
            if mid_name not in middle_school_info:
                middle_school_info[mid_name] = {
                    "district": s.get("district", "西湖区"),
                    "communities_hj": [],
                    "communities_xhzr": [],
                    "direct_primary_schools": [],
                }
            # 收集对口小区
            hj_comms = s.get("communities_hj", [])
            xhzr_comms = s.get("communities_xhzr", [])
            for c in hj_comms:
                if c not in middle_school_info[mid_name]["communities_hj"]:
                    middle_school_info[mid_name]["communities_hj"].append(c)
            for c in xhzr_comms:
                if c not in middle_school_info[mid_name]["communities_xhzr"]:
                    middle_school_info[mid_name]["communities_xhzr"].append(c)
            # 收集对口小学
            if s["school_name"] not in middle_school_info[mid_name]["direct_primary_schools"]:
                middle_school_info[mid_name]["direct_primary_schools"].append(s["school_name"])

# 添加缺失的初中学校到列表
for idx, (mid_name, info) in enumerate(middle_school_info.items()):
    new_school = {
        "school_name": mid_name,
        "campus_name": "",
        "school_code": f"MISSING_{idx}",
        "campus_code": f"MISSING_{idx}",
        "district": info["district"],
        "district_code": "",
        "school_type": "初中",
        "school_nature": "非民办",
        "address": "",
        "lng": "",
        "lat": "",
        "school_tel": "",
        "student_count": 0,
        "class_count": 0,
        "teacher_count": 0,
        "school_scope": "",
        "direct_middle_school": "",
        "direct_primary_schools": info["direct_primary_schools"],
        "school_detail": "",
        "year": "2026",
        "visit_times": 0,
        "communities_hj": info["communities_hj"],
        "communities_xhzr": info["communities_xhzr"],
        "community_count": len(info["communities_hj"]) + len(info["communities_xhzr"]),
    }
    schools.append(new_school)
    if '十三中' in mid_name:
        print(f"[DEBUG] Added: {mid_name}, primary_schools: {info['direct_primary_schools']}, communities: {len(info['communities_hj'])+len(info['communities_xhzr'])}")

# 统计信息
stats = {
    "total_schools": len(schools),
    "total_mappings": len(mappings),
    "district_stats": {},
}
for s in schools:
    d = s["district"]
    if d not in stats["district_stats"]:
        stats["district_stats"][d] = {"schools": 0, "mappings": 0}
    stats["district_stats"][d]["schools"] += 1
    stats["district_stats"][d]["mappings"] += s["community_count"]

# 生成 JS 文件
out_dir = base_dir.parent / "visualization" / "data"
out_dir.mkdir(parents=True, exist_ok=True)

js_content = f"""// 自动生成，请勿手动编辑
// 生成时间：2026-06-27
// 数据来源：杭州教育局「入学早知道」https://rxyj.hzedu.gov.cn

window.schoolStats = {json.dumps(stats, ensure_ascii=False, indent=2)};

window.schools = {json.dumps(schools, ensure_ascii=False)};
"""

out_path = out_dir / "school_data.js"
with open(out_path, "w", encoding="utf-8") as f:
    f.write(js_content)

print(f"[OK] 生成: {out_path}")
print(f"  学校: {len(schools)} 所")
print(f"  对口小区: {len(mappings)} 条")
print(f"  文件大小: {out_path.stat().st_size / 1024:.0f} KB")
