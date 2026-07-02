"""
通过杭州教育局「入学早知道」网站 API 批量采集学校数据
无需浙里办 APP，无需签名验证

API 基础地址: https://rxyj.hzedu.gov.cn/hzjyAppServer/api/

采集内容:
1. 各区学校列表（基本信息）
2. 每所学校详情（含对口小区/学区划分）

使用:
    python fetch_rxyj_schools.py              # 全量采集（含详情）
    python fetch_rxyj_schools.py --skip-detail # 仅列表，不采集对口小区
    python fetch_rxyj_schools.py --district 西湖区

采集完成后自动写入SQLite数据库和JSON文件
"""

import json
import csv
import time
import argparse
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.parse import urlencode

try:
    from db_manager import get_db
    HAS_DB = True
except ImportError:
    HAS_DB = False

# ============================================================
# 配置
# ============================================================

API_BASE = "https://rxyj.hzedu.gov.cn/hzjyAppServer/api/"

# 入学早知道网站区码（注意：与标准行政区划编码不同！）
DISTRICT_CODES = {
    "上城区": "330102",
    "拱墅区": "330105",
    "西湖区": "330106",
    "滨江区": "330108",
    "钱塘区": "330109",
    "余杭区": "330110",
    "临平区": "330111",
    "临安区": "330112",
    "桐庐县": "330122",
    "淳安县": "330127",
    "建德市": "330182",
}

SCHOOL_TYPE_MAP = {
    "1": "幼儿园", "2": "小学", "3": "初中",
    "4": "高中", "5": "初中", "6": "九年一贯制", "7": "完全中学",
}

CURRENT_YEAR = "2026"


# ============================================================
# HTTP 请求
# ============================================================

def api_post(path: str, body: dict) -> dict:
    """发送 POST 请求"""
    url = API_BASE + path
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = Request(url, data=data, method="POST", headers={
        "Content-Type": "application/json;charset=UTF-8",
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://rxyj.hzedu.gov.cn",
        "Referer": "https://rxyj.hzedu.gov.cn/",
    })
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def api_get(path: str, params: dict = None) -> dict:
    """发送 GET 请求"""
    url = API_BASE + path
    if params:
        url += "?" + urlencode(params)
    req = Request(url, headers={
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://rxyj.hzedu.gov.cn/",
    })
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def build_school_list_params(district_code: str, school_types: list = None,
                              nature: str = "非民办") -> dict:
    """构建学校列表查询参数"""
    if school_types is None:
        school_types = [2, 5, 6, 7]  # 小学+初中+九年一贯制+完全中学
    return {
        "expressions": {
            "active": {"op": "eq", "value": "1"},
            "schoolType": {"op": "in", "value": school_types},
            "schoolName": {"op": "lk", "value": ""},
            "hideFlagJnxx": {"op": "eq", "value": "1"},
            "hideFlagJncz": {"op": "eq", "value": ""},
            "gmblx": {"op": "eq", "value": nature},
            "szqdm": {"op": "lk", "value": district_code},
            "hideFlag": {"column": "hideFlag", "op": "eq", "value": "true"},
        },
        "start": 0,
        "limit": 1000,
        "orderByExpressions": [{"column": "id", "orderByType": "desc"}],
    }


# ============================================================
# 采集器
# ============================================================

def fetch_school_list(district_name: str, district_code: str) -> list:
    """获取一个区的所有学校列表"""
    body = build_school_list_params(district_code)
    print(f"  学校列表...", end=" ", flush=True)

    try:
        result = api_post("AppSchoolInfo/custom/paginate", body)
        if not result.get("success"):
            print(f"失败: {result.get('message')}")
            return []
        records = result.get("result", {}).get("records", [])
        print(f"{len(records)} 所")
        return records
    except Exception as e:
        print(f"异常: {e}")
        return []


def fetch_school_detail(campus_code: str, year: str = CURRENT_YEAR) -> dict:
    """获取学校详情（含对口小区）— GET 请求"""
    try:
        result = api_get("AppSchoolInfo/getSchoolInfo", {
            "year": year,
            "schoolName": campus_code,
            "source": "undefined",
        })
        if result.get("success"):
            return result.get("result", {})
    except Exception as e:
        print(f"\n  详情异常: {e}")
    return {}


def parse_school_from_list(rec: dict, district_name: str, district_code: str) -> dict:
    """从列表记录中提取学校信息"""
    entity = rec.get("appSchoolInfoEntity", rec)
    return {
        "school_name": entity.get("showSchoolName") or entity.get("schoolName", ""),
        "campus_name": entity.get("xqmc", ""),
        "school_code": entity.get("schoolCode", ""),
        "campus_code": entity.get("xqbsm", ""),
        "district": district_name,
        "district_code": district_code,
        "school_type": SCHOOL_TYPE_MAP.get(str(entity.get("schoolType", "")), ""),
        "school_nature": entity.get("gmblx", ""),
        "address": entity.get("address", ""),
        "lng": entity.get("lng"),
        "lat": entity.get("lat"),
        "school_tel": entity.get("schoolTel", ""),
        "student_count": entity.get("xsrs", 0) or 0,
        "class_count": entity.get("classTotalNum", 0) or 0,
        "teacher_count": entity.get("workerNumber", 0) or 0,
        "school_scope": (entity.get("schoolScope") or "").strip(),
        "direct_middle_school": entity.get("directMiddleSchoolName", "") or "",
        "school_detail": (entity.get("schoolDetail") or "").strip()[:500],
        "year": entity.get("year", CURRENT_YEAR),
        "visit_times": entity.get("visitTimes", 0) or 0,
    }


def extract_communities(detail: dict, school_name: str, campus_code: str,
                        district: str, year: str) -> list:
    """从详情中提取对口小区"""
    mappings = []

    # 户籍生
    for item in (detail.get("appSchoolDistrictInfoEntityList") or []):
        name = item.get("name") or item.get("xqmc") or ""
        if name:
            mappings.append({
                "school_name": school_name,
                "campus_code": campus_code,
                "community_name": name,
                "street_name": item.get("jdmc") or item.get("streetName") or "",
                "district": district,
                "student_type": "户籍生",
                "year": year,
            })

    # 新杭州人
    for item in (detail.get("appSchoolDistrictInfoEntityListNewHZR") or []):
        name = item.get("name") or item.get("xqmc") or ""
        if name:
            mappings.append({
                "school_name": school_name,
                "campus_code": campus_code,
                "community_name": name,
                "street_name": item.get("jdmc") or item.get("streetName") or "",
                "district": district,
                "student_type": "新杭州人",
                "year": year,
            })

    return mappings


# ============================================================
# 主程序
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="入学早知道数据采集")
    parser.add_argument("--district", help="指定区名")
    parser.add_argument("--skip-detail", action="store_true", help="跳过对口小区采集")
    parser.add_argument("--year", default=CURRENT_YEAR, help=f"年份（默认{CURRENT_YEAR}）")
    args = parser.parse_args()

    base_dir = Path(__file__).parent.parent
    raw_dir = base_dir / "raw"
    processed_dir = base_dir / "processed"
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    districts = {args.district: DISTRICT_CODES[args.district]} if args.district else DISTRICT_CODES

    all_schools = []
    all_mappings = []

    for district_name, district_code in districts.items():
        print(f"\n{'='*50}")
        print(f"  {district_name} ({district_code})")
        print(f"{'='*50}")

        records = fetch_school_list(district_name, district_code)
        if not records:
            continue

        for rec in records:
            school = parse_school_from_list(rec, district_name, district_code)
            all_schools.append(school)

        # 采集对口小区详情
        if not args.skip_detail:
            print(f"  采集对口小区 ({len(records)} 所)...", end=" ", flush=True)
            detail_count = 0
            for i, rec in enumerate(records):
                school = all_schools[-(len(records) - i)]
                code = school["campus_code"]
                if not code:
                    continue

                detail = fetch_school_detail(code, args.year)
                if detail:
                    mappings = extract_communities(
                        detail, school["school_name"], code,
                        district_name, school["year"]
                    )
                    all_mappings.extend(mappings)
                    if mappings:
                        detail_count += 1

                time.sleep(0.2)  # 限速
                if (i + 1) % 20 == 0:
                    print(f"{i+1}/{len(records)}", end=" ", flush=True)

            print(f"完成 ({detail_count} 所有对口小区)")

        time.sleep(0.3)

    # 保存到数据库
    if HAS_DB:
        print("\n  [数据库] 写入学校数据...")
        db = get_db()
        db.init_db()
        
        for school in all_schools:
            db.upsert_school(school)
        print(f"    学校: {len(all_schools)} 条")
        
        for mapping in all_mappings:
            db.upsert_school_community_mapping(mapping)
        print(f"    学区映射: {len(all_mappings)} 条")
        
        db.close()
        print(f"    [完成]")

    # 保存
    print(f"\n{'='*50}")
    print(f"  采集完成!")
    print(f"{'='*50}")
    print(f"  学校总数: {len(all_schools)}")
    print(f"  学区映射: {len(all_mappings)}")

    district_count = {}
    for s in all_schools:
        district_count[s["district"]] = district_count.get(s["district"], 0) + 1
    print(f"\n  按区统计:")
    for d, c in sorted(district_count.items(), key=lambda x: -x[1]):
        mappings_in_d = len([m for m in all_mappings if m["district"] == d])
        print(f"    {d}: {c} 所学校, {mappings_in_d} 条对口小区")

    # 保存学校数据
    with open(raw_dir / "rxyj_all_schools.json", "w", encoding="utf-8") as f:
        json.dump(all_schools, f, ensure_ascii=False, indent=2)
    print(f"\n  [保存] {raw_dir / 'rxyj_all_schools.json'}")

    if all_schools:
        with open(processed_dir / "rxyj_all_schools.csv", "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(all_schools[0].keys()))
            writer.writeheader()
            writer.writerows(all_schools)
        print(f"  [保存] {processed_dir / 'rxyj_all_schools.csv'}")

    # 保存对口小区数据
    if all_mappings:
        with open(raw_dir / "rxyj_all_mappings.json", "w", encoding="utf-8") as f:
            json.dump(all_mappings, f, ensure_ascii=False, indent=2)
        with open(processed_dir / "rxyj_all_mappings.csv", "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(all_mappings[0].keys()))
            writer.writeheader()
            writer.writerows(all_mappings)
        print(f"  [保存] {processed_dir / 'rxyj_all_mappings.csv'}")


if __name__ == "__main__":
    main()
