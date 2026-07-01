"""
解析浙里办学校详情 JSON 响应，提取关键字段并保存为结构化数据。

输入: ../school.json  (浙里办 API 原始响应)
输出:
    ../processed/school_detail.json   # 学校详情(结构化)
    ../processed/school_communities.csv # 学校-对口小区映射
"""

import json
import csv
from pathlib import Path


# 学校类型编码映射
SCHOOL_TYPE_MAP = {
    "1": "幼儿园",
    "2": "小学",
    "3": "初中",
    "4": "高中",
    "5": "初中",
    "6": "九年一贯制",
    "7": "完全中学",
}


def parse_school_entity(entity: dict) -> dict:
    """从 appSchoolInfoEntity 提取关键字段"""
    return {
        # 标识
        "school_name": entity.get("showSchoolName") or entity.get("schoolName", ""),
        "short_name": entity.get("xxmc", ""),
        "campus_name": entity.get("xqmc", ""),
        "school_code": entity.get("schoolCode", ""),
        "campus_code": entity.get("xqbsm", ""),
        "id": entity.get("id", ""),
        # 分类
        "district": entity.get("szqmc", ""),
        "district_code": entity.get("szqdm", ""),
        "school_type": SCHOOL_TYPE_MAP.get(str(entity.get("schoolType", "")), ""),
        "school_type_code": str(entity.get("schoolType", "")),
        "school_nature": entity.get("gmblx", ""),  # 公办/民办
        # 联系与位置
        "address": entity.get("address", ""),
        "lng": entity.get("lng"),
        "lat": entity.get("lat"),
        "school_tel": entity.get("schoolTel", ""),
        "school_way": entity.get("schoolWay", ""),  # 交通指引
        # 规模
        "student_count": entity.get("xsrs", 0) or 0,
        "class_count": entity.get("classTotalNum", 0) or 0,
        "teacher_count": entity.get("workerNumber", 0) or 0,
        "building_area": entity.get("buildingAreaNum", 0) or 0,  # 建筑面积㎡
        "school_area": entity.get("schoolAreaNum", 0) or 0,      # 占地面积㎡
        "absent_number": entity.get("absentNumber", 0) or 0,
        # 招生计划(1=户籍生 2=新杭州人 3=摸底)
        "forecast_class_num_1": entity.get("forecastClassNum1", 0) or 0,
        "forecast_person_num_1": entity.get("forecastClassPerson1", 0) or 0,
        "forecast_class_num_2": entity.get("forecastClassNum2", 0) or 0,
        "forecast_person_num_2": entity.get("forecastClassPerson2", 0) or 0,
        "forecast_class_num_3": entity.get("forecastClassNum3", 0) or 0,
        "forecast_person_num_3": entity.get("forecastClassPerson3", 0) or 0,
        "recruit_type": entity.get("recruitType", ""),  # 户籍生/...
        "authorized_number": entity.get("authorizedNumber", 0) or 0,
        "register_count": entity.get("registerCount", 0) or 0,
        "recruit_count": entity.get("recruitCount", 0) or 0,
        # 学区与升学
        "school_scope": (entity.get("schoolScope") or "").strip(),
        "direct_middle_school": entity.get("directMiddleSchoolName", "") or "",
        "direct_middle_school_code": entity.get("directMiddleSchoolCode") or "",
        "direct_primary_school": entity.get("directPrimarySchoolName") or "",
        # 预警
        "warning_level": entity.get("warningLevel"),
        "warning_year": entity.get("warningYear"),
        "warning_percent": entity.get("warningPercent"),
        "publish_warning_date": entity.get("publishWarningDate"),
        # 状态与媒体
        "year": entity.get("year", ""),
        "active": entity.get("active", False),
        "hide_flag": entity.get("hideFlag", ""),
        "visit_times": entity.get("visitTimes", 0) or 0,
        "school_logo": entity.get("schoolLogo", "") or "",
        "school_pic": entity.get("xqdt", "") or "",
        "school_detail": (entity.get("schoolDetail") or "").strip(),
        "enroll_file_url": entity.get("enrollFileUrl", "") or "",
        "enroll_file_name": entity.get("enrollFileName", "") or "",
        "forecast_publish_time": entity.get("yjfbsj", "") or "",  # 预计发布时间
        # 审计
        "create_time": entity.get("createTime", ""),
        "update_time": entity.get("updateTime", ""),
        "update_user": entity.get("updateUser", ""),
    }


def parse_communities(district_list: list, school_name: str, campus_code: str,
                      district: str, year: str, student_type: str) -> list:
    """解析对口小区列表，提取有效记录"""
    rows = []
    for item in (district_list or []):
        community_name = item.get("name") or item.get("xqmc") or ""
        if not community_name:
            continue
        rows.append({
            "school_name": school_name,
            "campus_code": campus_code,
            "community_name": community_name,
            "street_name": item.get("jdmc") or item.get("streetName") or "",
            "social_community": item.get("communityName") or item.get("sqmc") or "",
            "community_code": item.get("xqbm") or item.get("communityCode") or "",
            "street_code": item.get("streetCode") or "",
            "district": district,
            "student_type": student_type,
            "year": item.get("year") or year,
            "is_show": item.get("isShow", ""),
            "active": item.get("active", True),
        })
    return rows


def main():
    base_dir = Path(__file__).parent.parent
    src = base_dir / "school.json"
    out_detail = base_dir / "processed" / "school_detail.json"
    out_communities = base_dir / "processed" / "school_communities.csv"

    with open(src, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not data.get("success"):
        print(f"[ERROR] 接口返回失败: {data.get('message')}")
        return

    results = data.get("result", [])
    schools = []
    community_rows = []

    for item in results:
        entity = item.get("appSchoolInfoEntity") or {}
        school = parse_school_entity(entity)
        school["year"] = item.get("year", school.get("year", ""))
        schools.append(school)

        # 户籍生对口小区
        community_rows.extend(parse_communities(
            item.get("appSchoolDistrictInfoEntityList"),
            school["school_name"], school["campus_code"],
            school["district"], school["year"], "户籍生"))

        # 新杭州人对口小区
        community_rows.extend(parse_communities(
            item.get("appSchoolDistrictInfoEntityListNewHZR"),
            school["school_name"], school["campus_code"],
            school["district"], school["year"], "新杭州人"))

    # 保存学校详情 JSON
    out_detail.parent.mkdir(parents=True, exist_ok=True)
    with open(out_detail, "w", encoding="utf-8") as f:
        json.dump(schools, f, ensure_ascii=False, indent=2)
    print(f"[INFO] 学校详情: {out_detail} ({len(schools)} 所)")

    # 保存对口小区 CSV
    if community_rows:
        with open(out_communities, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(community_rows[0].keys()))
            writer.writeheader()
            writer.writerows(community_rows)
        print(f"[INFO] 对口小区: {out_communities} ({len(community_rows)} 条)")

    # 控制台概览
    for s in schools:
        print(f"\n学校: {s['school_name']} ({s['campus_name']})")
        print(f"  区域: {s['district']} | 类型: {s['school_type']} | 性质: {s['school_nature']}")
        print(f"  地址: {s['address']}")
        print(f"  对口初中: {s['direct_middle_school']}")
        print(f"  规模: 学生{s['student_count']}人 / 班级{s['class_count']}个 / 教师{s['teacher_count']}人")
        print(f"  招生计划(户籍生): {s['forecast_class_num_1']}班 × {s['forecast_person_num_1']}人")
        print(f"  学区范围: {s['school_scope'][:80]}...")
    print(f"\n对口小区列表:")
    for c in community_rows:
        print(f"  [{c['student_type']}] {c['community_name']}")


if __name__ == "__main__":
    main()
