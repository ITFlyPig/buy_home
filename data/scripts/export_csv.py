#!/usr/bin/env python3
"""将学校、学区等JSON数据导出为CSV格式"""

import json
import csv
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "processed")


def load_json(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def write_csv(filepath, data, fieldnames=None):
    if not data:
        print(f"  跳过（无数据）: {filepath}")
        return
    if fieldnames is None:
        fieldnames = list(data[0].keys())
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(data)
    print(f"  已生成: {filepath} ({len(data)} 行)")


def export_schools():
    """导出学校基础信息（含对口小区）"""
    print("[1] 导出学校基础信息 rxyj_all_schools")
    data = load_json(os.path.join(RAW_DIR, "rxyj_all_schools.json"))
    rows = []
    for item in data:
        row = dict(item)
        # 数组字段用分号分隔
        if isinstance(row.get("communities_hj"), list):
            row["communities_hj"] = ";".join(row["communities_hj"])
        if isinstance(row.get("communities_xhzr"), list):
            row["communities_xhzr"] = ";".join(row["communities_xhzr"])
        rows.append(row)
    fieldnames = [
        "school_name", "campus_name", "school_code", "campus_code",
        "district", "district_code", "school_type", "school_nature",
        "address", "lng", "lat", "school_tel",
        "student_count", "class_count", "teacher_count",
        "school_scope", "direct_middle_school", "school_detail",
        "communities_hj", "communities_xhzr", "community_count",
        "year", "visit_times",
    ]
    write_csv(os.path.join(PROCESSED_DIR, "rxyj_all_schools.csv"), rows, fieldnames)


def build_school_index(schools):
    """以 school_name 为键建立学校信息索引，用于关联补充字段"""
    idx = {}
    for s in schools:
        idx[s["school_name"]] = s
    return idx


def export_mappings():
    """导出学校-小区对口映射，关联补充 school_type 等字段"""
    print("[2] 导出学校-小区对口映射 rxyj_all_mappings")
    data = load_json(os.path.join(RAW_DIR, "rxyj_all_mappings.json"))
    schools = load_json(os.path.join(RAW_DIR, "rxyj_all_schools.json"))
    idx = build_school_index(schools)
    rows = []
    for item in data:
        row = dict(item)
        s = idx.get(item.get("school_name"))
        if s:
            row["campus_name"] = s.get("campus_name", "")
            row["school_code"] = s.get("school_code", "")
            row["school_type"] = s.get("school_type", "")
            row["school_nature"] = s.get("school_nature", "")
            row["address"] = s.get("address", "")
            row["lng"] = s.get("lng", "")
            row["lat"] = s.get("lat", "")
            row["school_tel"] = s.get("school_tel", "")
            row["direct_middle_school"] = s.get("direct_middle_school", "")
        else:
            for k in ("campus_name", "school_code", "school_type",
                      "school_nature", "address", "lng", "lat",
                      "school_tel", "direct_middle_school"):
                row.setdefault(k, "")
        rows.append(row)
    fieldnames = [
        "school_name", "campus_name", "school_code", "campus_code",
        "school_type", "school_nature", "district", "address",
        "lng", "lat", "school_tel", "direct_middle_school",
        "community_name", "street_name", "student_type", "year",
    ]
    write_csv(os.path.join(PROCESSED_DIR, "rxyj_all_mappings.csv"), rows, fieldnames)


def export_school_district():
    """导出学区房映射（含价格信息），关联补充 school_type"""
    print("[3] 导出学区房映射 school_district_mapping")
    data = load_json(os.path.join(RAW_DIR, "school_district_mapping.json"))
    schools = load_json(os.path.join(RAW_DIR, "rxyj_all_schools.json"))
    idx = build_school_index(schools)
    rows = []
    for item in data:
        row = dict(item)
        s = idx.get(item.get("school_name"))
        row["school_type"] = s.get("school_type", "") if s else item.get("school_type", "")
        row["school_nature"] = s.get("school_nature", "") if s else ""
        rows.append(row)
    fieldnames = [
        "school_name", "school_level", "school_type", "school_nature",
        "district", "plate", "service_communities", "key_communities",
        "avg_price_range", "enrollment_year", "remarks",
    ]
    write_csv(os.path.join(PROCESSED_DIR, "school_district_mapping.csv"), rows, fieldnames)


def export_school_detail():
    """导出学校详情（493所全量，基于 rxyj_all_schools.json）"""
    print("[4] 导出学校详情 school_detail")
    data = load_json(os.path.join(RAW_DIR, "rxyj_all_schools.json"))
    rows = []
    for item in data:
        row = {
            "school_name": item.get("school_name", ""),
            "campus_name": item.get("campus_name", ""),
            "school_code": item.get("school_code", ""),
            "campus_code": item.get("campus_code", ""),
            "district": item.get("district", ""),
            "district_code": item.get("district_code", ""),
            "school_type": item.get("school_type", ""),
            "school_nature": item.get("school_nature", ""),
            "address": item.get("address", ""),
            "lng": item.get("lng", ""),
            "lat": item.get("lat", ""),
            "school_tel": item.get("school_tel", ""),
            "student_count": item.get("student_count", 0),
            "class_count": item.get("class_count", 0),
            "teacher_count": item.get("teacher_count", 0),
            "school_scope": item.get("school_scope", ""),
            "direct_middle_school": item.get("direct_middle_school", ""),
            "school_detail": item.get("school_detail", ""),
            "communities_hj": ";".join(item.get("communities_hj") or []),
            "communities_xhzr": ";".join(item.get("communities_xhzr") or []),
            "community_count": item.get("community_count", 0),
            "year": item.get("year", ""),
            "visit_times": item.get("visit_times", 0),
        }
        rows.append(row)
    fieldnames = [
        "school_name", "campus_name", "school_code", "campus_code",
        "district", "district_code", "school_type", "school_nature",
        "address", "lng", "lat", "school_tel",
        "student_count", "class_count", "teacher_count",
        "school_scope", "direct_middle_school", "school_detail",
        "communities_hj", "communities_xhzr", "community_count",
        "year", "visit_times",
    ]
    write_csv(os.path.join(PROCESSED_DIR, "school_detail.csv"), rows, fieldnames)


def export_transactions():
    """从数据库导出小区成交记录"""
    print("[5] 导出小区成交记录 community_transactions")
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from db_manager import get_db
    except ImportError:
        print("  跳过（db_manager 不可用）")
        return
    db = get_db()
    rows_raw = db.query("SELECT * FROM community_transactions ORDER BY trade_date DESC")
    rows = [dict(r) for r in rows_raw]
    db.close()
    fieldnames = [
        "id", "community_name", "trade_date", "area", "price",
        "total_price", "building", "floor", "orientation", "crawl_date",
    ]
    write_csv(os.path.join(PROCESSED_DIR, "community_transactions.csv"), rows, fieldnames)


def export_prices():
    """从数据库导出小区价格记录"""
    print("[6] 导出小区价格记录 community_prices")
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from db_manager import get_db
    except ImportError:
        print("  跳过（db_manager 不可用）")
        return
    db = get_db()
    rows_raw = db.query("SELECT * FROM community_prices ORDER BY community_name, crawl_date DESC")
    rows = [dict(r) for r in rows_raw]
    db.close()
    fieldnames = [
        "id", "community_name", "avg_price", "min_total", "max_total",
        "layout", "year", "data_source", "crawl_date",
    ]
    write_csv(os.path.join(PROCESSED_DIR, "community_prices.csv"), rows, fieldnames)


def main():
    print("=" * 60)
    print("将学校、学区JSON数据导出为CSV")
    print("=" * 60)
    export_schools()
    export_mappings()
    export_school_district()
    export_school_detail()
    export_transactions()
    export_prices()
    print("=" * 60)
    print("全部完成！CSV文件保存在 data/processed/ 目录下")


if __name__ == "__main__":
    main()
