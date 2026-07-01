#!/usr/bin/env python3
"""贝壳小区价格采集脚本 - 用户可独立运行版

使用方法：
1. cd /Users/yanxi/Downloads/0绿城/kiro-data/data-warehouse/杭州买房指南
2. pip install requests
3. python3 data/scripts/crawl_community_prices.py
4. 等待完成后，将 data/processed/community_prices.json 保留即可

进度说明：
- 共 9712 个小区，每次请求间隔 3-5 秒
- 预计耗时：8-10 小时（建议先跑主城区）
- 支持断点续爬，中断后重新运行即可

可选参数：
  --district 西湖区    只采集指定区域（如：西湖区、上城区、拱墅区、滨江区）
  --limit 500          限制采集数量（用于测试）
"""

import json
import re
import time
import random
import argparse
from pathlib import Path

try:
    import requests
except ImportError:
    print("请先安装 requests: pip install requests")
    exit(1)

BASE_DIR = Path(__file__).parent.parent.parent
RAW_DATA_PATH = BASE_DIR / "data" / "raw" / "rxyj_all_schools.json"
OUTPUT_PATH = BASE_DIR / "data" / "processed" / "community_prices.json"

KE_SEARCH_API = "https://hz.ke.com/xiaoqu/rs{}/"
KE_API_V2 = "https://m.ke.com/search/result?q={}&city=hz"

USER_AGENTS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

def load_communities(filter_district=None):
    """从浙里办数据提取所有小区"""
    with open(RAW_DATA_PATH, "r", encoding="utf-8") as f:
        schools = json.load(f)
    
    communities = {}
    for s in schools:
        if filter_district and s["district"] != filter_district:
            continue
        for c in s.get("communities_hj", []):
            if c not in communities:
                communities[c] = {"schools": [], "districts": []}
            communities[c]["schools"].append(s["school_name"])
            if s["district"] not in communities[c]["districts"]:
                communities[c]["districts"].append(s["district"])
        for c in s.get("communities_xhzr", []):
            if c not in communities:
                communities[c] = {"schools": [], "districts": []}
            communities[c]["schools"].append(s["school_name"])
            if s["district"] not in communities[c]["districts"]:
                communities[c]["districts"].append(s["district"])
    
    return communities

def fetch_community_price(community_name):
    """从贝壳获取小区价格"""
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Referer": "https://hz.ke.com/xiaoqu/",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    # 尝试 PC 端搜索
    url = KE_SEARCH_API.format(requests.utils.quote(community_name))
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.encoding = "utf-8"
        html = resp.text
        
        # 提取价格
        price_match = re.search(r'<span class="price">(\d+)</span>', html)
        if price_match:
            avg_price = int(price_match.group(1))
            # 提取小区名和总价
            item_match = re.search(r'<div class="info">([\s\S]*?)</div>', html)
            if item_match:
                item_html = item_match.group(1)
                min_price_match = re.search(r'<span class="totalPrice">(\d+)-(\d+)万', item_html)
                min_total = int(min_price_match.group(1)) if min_price_match else 0
                max_total = int(min_price_match.group(2)) if min_price_match else 0
                
                layout_match = re.search(r'<span class="houseType">(.*?)</span>', item_html)
                layout = layout_match.group(1).strip() if layout_match else ""
                
                return {
                    "name": community_name,
                    "avg_price": avg_price,
                    "min_total": min_total,
                    "max_total": max_total,
                    "layout": layout,
                }
            return {"name": community_name, "avg_price": avg_price, "min_total": 0, "max_total": 0, "layout": ""}
    except Exception as e:
        pass

    # 尝试移动端搜索
    url = KE_API_V2.format(requests.utils.quote(community_name))
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.encoding = "utf-8"
        html = resp.text
        
        match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});', html)
        if match:
            data = json.loads(match.group(1))
            search_result = data.get("searchResult", {})
            list_data = search_result.get("list", [])
            if list_data:
                item = list_data[0]
                return {
                    "name": item.get("name", community_name),
                    "avg_price": item.get("price", 0),
                    "min_total": item.get("minPrice", 0),
                    "max_total": item.get("maxPrice", 0),
                    "layout": item.get("layout", ""),
                }
    except Exception as e:
        pass

    return None

def main():
    parser = argparse.ArgumentParser(description='采集小区价格')
    parser.add_argument('--district', type=str, help='只采集指定区域')
    parser.add_argument('--limit', type=int, help='限制采集数量')
    args = parser.parse_args()

    communities = load_communities(args.district)
    print(f"待采集小区数: {len(communities)}")
    if args.district:
        print(f"区域过滤: {args.district}")
    if args.limit:
        print(f"数量限制: {args.limit}")

    # 加载已采集数据（断点续爬）
    if OUTPUT_PATH.exists():
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            existing = json.load(f)
        existing_names = {c["name"] for c in existing}
        print(f"已采集: {len(existing)} 个")
    else:
        existing = []
        existing_names = set()

    to_fetch = [c for c in communities.keys() if c not in existing_names]
    if args.limit:
        to_fetch = to_fetch[:args.limit]
    print(f"本次待采集: {len(to_fetch)} 个")

    # 开始采集
    results = []
    total = len(to_fetch)
    start_time = time.time()

    for i, name in enumerate(to_fetch, 1):
        info = communities[name]
        print(f"\r{i}/{total}: {name} ...", end="", flush=True)

        price = fetch_community_price(name)
        if price and price["avg_price"] > 0:
            results.append({
                "name": name,
                "avg_price": price["avg_price"],
                "min_total": price["min_total"],
                "max_total": price["max_total"],
                "layout": price["layout"],
                "schools": info["schools"],
                "districts": info["districts"],
                "data_source": "ke.com",
            })
            print(f"\r{i}/{total}: {name} -> ¥{(price['avg_price']/10000):.1f}万/㎡", flush=True)
        else:
            print(f"\r{i}/{total}: {name} -> [未找到]", flush=True)

        # 保存进度（每10个保存一次）
        if i % 10 == 0:
            output = existing + results
            with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
                json.dump(output, f, ensure_ascii=False, indent=2)

        # 随机延迟
        time.sleep(random.uniform(3, 5))

    # 最终保存
    output = existing + results
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # 统计
    elapsed = time.time() - start_time
    print(f"\n\n[完成] 本次采集 {len(results)} 个，总计 {len(output)} 个")
    print(f"耗时: {elapsed/60:.1f} 分钟")
    print(f"输出文件: {OUTPUT_PATH}")

    # 生成 JS 文件
    js_content = f"""// 自动生成，请勿手动编辑
// 数据来源：贝壳 ke.com
// 总计: {len(output)} 个小区

window.communityPrices = {json.dumps(output, ensure_ascii=False)};
"""
    js_path = BASE_DIR / "visualization" / "data" / "community_prices.js"
    with open(js_path, "w", encoding="utf-8") as f:
        f.write(js_content)
    print(f"JS 文件: {js_path}")

if __name__ == "__main__":
    main()
