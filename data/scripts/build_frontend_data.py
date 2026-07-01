"""
将采集的 JSON 数据转为前端可用的 JS 文件（ES Module）
"""
import json
from pathlib import Path

base_dir = Path(__file__).parent.parent

# 读取数据
with open(base_dir / "raw" / "rxyj_all_schools.json", "r", encoding="utf-8") as f:
    schools = json.load(f)

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
