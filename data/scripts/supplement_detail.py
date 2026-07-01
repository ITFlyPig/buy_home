"""
补采学校详情：对口初中 + 对口小区 + 地址等完整信息
只采缺失 direct_middle_school 的学校
"""
import json
import time
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.parse import urlencode

API_BASE = "https://rxyj.hzedu.gov.cn/hzjyAppServer/api/"

with open('/Users/yanxi/Downloads/0绿城/kiro-data/data-warehouse/杭州买房指南/data/raw/rxyj_all_schools.json') as f:
    schools = json.load(f)

with open('/Users/yanxi/Downloads/0绿城/kiro-data/data-warehouse/杭州买房指南/data/raw/rxyj_all_mappings.json') as f:
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

# 需要补采的学校（缺 direct_middle_school 且是小学/九年一贯制）
need_detail = [s for s in schools if not s.get("direct_middle_school")]
print(f"总学校: {len(schools)}")
print(f"需要补采详情: {len(need_detail)}")

# 构建中学名称集合（用于匹配）
middle_names = set(s["school_name"] for s in schools if s["school_type"] in ("初中", "九年一贯制"))
print(f"中学名称集合: {len(middle_names)} 个")

def api_get(path, params):
    url = API_BASE + path + "?" + urlencode(params)
    req = Request(url, headers={
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://rxyj.hzedu.gov.cn/",
    })
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

updated = 0
errors = 0

for i, s in enumerate(need_detail):
    code = s["campus_code"]
    if not code:
        continue

    try:
        result = api_get("AppSchoolInfo/getSchoolInfo", {
            "year": s.get("year", "2026"),
            "schoolName": code,
            "source": "undefined",
        })

        if not result.get("success"):
            errors += 1
            continue

        detail = result.get("result", {})
        entity = detail.get("appSchoolInfoEntity", {})

        if entity:
            # 更新字段
            s["direct_middle_school"] = entity.get("directMiddleSchoolName", "") or ""
            s["address"] = entity.get("address", "") or s.get("address", "")
            s["lng"] = entity.get("lng")
            s["lat"] = entity.get("lat")
            s["school_tel"] = entity.get("schoolTel", "") or s.get("school_tel", "")
            s["student_count"] = entity.get("xsrs", 0) or 0
            s["class_count"] = entity.get("classTotalNum", 0) or 0
            s["teacher_count"] = entity.get("workerNumber", 0) or 0
            s["school_scope"] = (entity.get("schoolScope") or "").strip()
            s["school_detail"] = (entity.get("schoolDetail") or "").strip()[:500]

        # 补充对口小区
        comm = school_communities.get(code, {"户籍生": [], "新杭州人": []})
        hj_list = []
        xhzr_list = []
        for item in (detail.get("appSchoolDistrictInfoEntityList") or []):
            name = item.get("name") or item.get("xqmc") or ""
            if name:
                hj_list.append(name)
        for item in (detail.get("appSchoolDistrictInfoEntityListNewHZR") or []):
            name = item.get("name") or item.get("xqmc") or ""
            if name:
                xhzr_list.append(name)

        s["communities_hj"] = hj_list
        s["communities_xhzr"] = xhzr_list
        s["community_count"] = len(hj_list) + len(xhzr_list)

        updated += 1

    except Exception as e:
        errors += 1
        if errors <= 3:
            print(f"  异常: {e}")

    time.sleep(0.15)

    if (i + 1) % 50 == 0:
        print(f"  进度: {i+1}/{len(need_detail)} (更新{updated}, 错误{errors})")

print(f"\n完成! 更新: {updated}, 错误: {errors}")

# 统计
has_middle = [s for s in schools if s.get("direct_middle_school")]
print(f"有对口初中的学校: {len(has_middle)}/{len(schools)}")

# 保存
out_path = Path('/Users/yanxi/Downloads/0绿城/kiro-data/data-warehouse/杭州买房指南/data/raw/rxyj_all_schools.json')
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(schools, f, ensure_ascii=False, indent=2)
print(f"[保存] {out_path}")

# 样例
print("\n--- 小学对口初中样例 ---")
primary_with_middle = [s for s in schools if s["school_type"] == "小学" and s.get("direct_middle_school")]
for s in primary_with_middle[:10]:
    print(f"  {s['school_name']} -> {s['direct_middle_school']} ({s['district']})")
