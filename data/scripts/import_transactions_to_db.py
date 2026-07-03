#!/usr/bin/env python3
"""一次性脚本：将前端JS中的成交数据导入SQLite数据库"""

import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from db_manager import get_db

BASE_DIR = Path(__file__).parent.parent.parent
JS_PATH = BASE_DIR / "visualization" / "data" / "transaction_data.js"

content = JS_PATH.read_text(encoding="utf-8")
start = content.index("[")
end = content.rindex("]") + 1
transactions = json.loads(content[start:end])
print(f"读取前端成交数据: {len(transactions)} 条")

db = get_db()
db.init_db()
crawl_date = datetime.now().strftime("%Y-%m-%d")

for item in transactions:
    db.insert_community_transaction({
        "community_name": item["community_name"],
        "trade_date": item.get("trade_date", ""),
        "area": item.get("area", 0),
        "price": item.get("price", 0),
        "total_price": item.get("total_price", 0),
        "building": item.get("building", ""),
        "floor": item.get("floor", ""),
        "orientation": item.get("orientation", ""),
        "crawl_date": crawl_date,
    })

count = db.query_one("SELECT COUNT(*) FROM community_transactions")[0]
print(f"数据库成交记录: {count} 条")
db.close()
