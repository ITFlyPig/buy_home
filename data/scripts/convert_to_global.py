"""将ES模块数据文件转为全局变量格式"""
from pathlib import Path

data_dir = Path(__file__).parent.parent.parent / "visualization" / "data"

# 转换 school_data.js
school_path = data_dir / "school_data.js"
content = school_path.read_text(encoding="utf-8")
content = content.replace("export const schoolStats", "window.schoolStats")
content = content.replace("export const schools", "window.schools")
school_path.write_text(content, encoding="utf-8")
print(f"[OK] 转换: {school_path}")

# 转换 price_data.js
price_path = data_dir / "price_data.js"
content = price_path.read_text(encoding="utf-8")
content = content.replace("export const priceStats", "window.priceStats")
content = content.replace("export const priceData", "window.priceData")
price_path.write_text(content, encoding="utf-8")
print(f"[OK] 转换: {price_path}")
