"""生成房价数据JS文件"""
import csv, json
from pathlib import Path

# 脚本路径: 杭州买房指南/data/scripts/build_price_data.py
# CSV路径:  data-warehouse/hangzhou_monthly_price.csv
# 可视化:   杭州买房指南/visualization/data/price_data.js

base = Path(__file__).parent.parent.parent  # 杭州买房指南/
dw_root = base.parent  # data-warehouse/

data = []
csv_path = dw_root / "hangzhou_monthly_price.csv"
with open(csv_path, "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        data.append({
            "year": int(row["year"]),
            "month": int(row["month"]),
            "price": int(row["price"]),
            "mom_pct": float(row["mom_pct"])
        })

# 统计信息
latest = data[-1]
first = data[0]
max_item = max(data, key=lambda d: d["price"])
min_item = min(data, key=lambda d: d["price"])

stats = {
    "latest_price": latest["price"],
    "latest_date": f'{latest["year"]}年{latest["month"]}月',
    "latest_mom": latest["mom_pct"],
    "first_price": first["price"],
    "total_records": len(data),
    "max_price": max_item["price"],
    "max_date": f'{max_item["year"]}年{max_item["month"]}月',
    "min_price": min_item["price"],
    "min_date": f'{min_item["year"]}年{min_item["month"]}月',
}

js_content = f"""// 自动生成，请勿手动编辑
// 生成时间：2026-06-29
// 数据来源：杭州二手房月度成交均价

window.priceStats = {json.dumps(stats, ensure_ascii=False, indent=2)};

window.priceData = {json.dumps(data, ensure_ascii=False)};
"""

out_path = base / "visualization" / "data" / "price_data.js"
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    f.write(js_content)

print(f"[OK] 生成: {out_path}")
print(f"  记录数: {len(data)}")
print(f"  最新: {stats['latest_date']} {stats['latest_price']}元/㎡")
print(f"  最高: {stats['max_date']} {stats['max_price']}元/㎡")
print(f"  最低: {stats['min_date']} {stats['min_price']}元/㎡")
