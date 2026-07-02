"""数据迁移脚本 - 将现有JSON数据导入SQLite数据库

迁移内容：
1. rxyj_all_schools.json -> schools 表
2. rxyj_all_mappings.json -> school_community_mapping 表
3. community_prices.json -> communities + community_prices 表
"""

import json
from pathlib import Path
from db_manager import get_db

BASE_DIR = Path(__file__).parent.parent
RAW_DIR = BASE_DIR / "raw"
PROCESSED_DIR = BASE_DIR / "processed"


def migrate_schools(db):
    print("\n=== 迁移学校数据 ===")
    schools_path = RAW_DIR / "rxyj_all_schools.json"
    if not schools_path.exists():
        print(f"  [跳过] 文件不存在: {schools_path}")
        return

    with open(schools_path, "r", encoding="utf-8") as f:
        schools = json.load(f)

    count = 0
    for school in schools:
        db.upsert_school(school)
        count += 1
        if count % 50 == 0:
            print(f"  已迁移: {count}/{len(schools)}")

    print(f"  完成: {count} 所学校")


def migrate_mappings(db):
    print("\n=== 迁移学区映射数据 ===")
    mappings_path = RAW_DIR / "rxyj_all_mappings.json"
    if not mappings_path.exists():
        print(f"  [跳过] 文件不存在: {mappings_path}")
        return

    with open(mappings_path, "r", encoding="utf-8") as f:
        mappings = json.load(f)

    count = 0
    for mapping in mappings:
        db.upsert_school_community_mapping(mapping)
        count += 1
        if count % 100 == 0:
            print(f"  已迁移: {count}/{len(mappings)}")

    print(f"  完成: {count} 条映射")


def migrate_communities(db):
    print("\n=== 迁移小区和价格数据 ===")
    prices_path = PROCESSED_DIR / "community_prices.json"
    if not prices_path.exists():
        print(f"  [跳过] 文件不存在: {prices_path}")
        return

    with open(prices_path, "r", encoding="utf-8") as f:
        prices = json.load(f)

    comm_count = 0
    price_count = 0
    for item in prices:
        community_data = {
            "name": item["name"],
            "districts": item.get("districts", []),
            "schools": item.get("schools", []),
        }
        db.upsert_community(community_data)
        comm_count += 1

        price_data = {
            "name": item["name"],
            "avg_price": item.get("avg_price"),
            "min_total": item.get("min_total"),
            "max_total": item.get("max_total"),
            "layout": item.get("layout", ""),
            "year": item.get("year"),
            "data_source": item.get("data_source", ""),
        }
        db.upsert_community_price(price_data)
        price_count += 1

        if comm_count % 100 == 0:
            print(f"  已迁移: {comm_count}/{len(prices)} 小区")

    print(f"  完成: {comm_count} 个小区, {price_count} 条价格")


def main():
    print("=" * 60)
    print("  数据迁移脚本 - 将JSON数据导入SQLite")
    print("=" * 60)

    db = get_db()
    db.init_db()

    migrate_schools(db)
    migrate_mappings(db)
    migrate_communities(db)

    stats = db.get_stats()
    print("\n" + "=" * 60)
    print("  迁移完成! 数据库统计:")
    print(f"    学校: {stats['schools']}")
    print(f"    小区: {stats['communities']}")
    print(f"    学区映射: {stats['mappings']}")
    print(f"    价格记录: {stats['prices']}")
    print(f"    成交记录: {stats['transactions']}")
    print("=" * 60)

    db.close()


if __name__ == "__main__":
    main()