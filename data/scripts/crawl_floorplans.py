#!/usr/bin/env python3
"""贝壳户型图爬取脚本

从贝壳网爬取小区真实户型图图片，下载到本地供前端展示。

使用方法：
  python3 data/scripts/crawl_floorplans.py --district 西湖区 --limit 50
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
OUTPUT_DIR = BASE_DIR / "visualization" / "data" / "floorplans"
PRICE_PATH = BASE_DIR / "data" / "processed" / "community_prices.json"
FLOORPLAN_MAP_PATH = OUTPUT_DIR / "floorplan_map.json"

KE_SEARCH_API = "https://hz.ke.com/xiaoqu/rs{}/"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

def get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Referer": "https://hz.ke.com/xiaoqu/",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

def find_community_id(community_name):
    """搜索小区获取贝壳小区ID"""
    url = KE_SEARCH_API.format(requests.utils.quote(community_name))
    try:
        resp = requests.get(url, headers=get_headers(), timeout=15)
        resp.encoding = "utf-8"
        # 从搜索结果页提取小区ID
        match = re.search(r'href="/xiaoqu/(\d+)/"', resp.text)
        if match:
            return match.group(1)
    except Exception:
        pass
    return None

def fetch_floorplans(community_id, max_count=3):
    """从贝壳小区户型页爬取户型图图片URL"""
    url = f"https://hz.ke.com/xiaoqu/{community_id}/huxing/"
    floorplans = []
    try:
        resp = requests.get(url, headers=get_headers(), timeout=15)
        resp.encoding = "utf-8"
        html = resp.text
        # 提取户型图图片和户型名称
        # 贝壳户型图格式：<img ... src="https://...jpg" ...> + 户型名称
        pattern = re.compile(
            r'<img[^>]*src="(https://[^"]*\.(?:jpg|png|webp)[^"]*)"[^>]*>.*?'
            r'(?:<span[^>]*>([\d室]+.*?)</span>|alt="([^"]*)")',
            re.S
        )
        # 更简单的提取方式
        img_pattern = re.compile(r'src="(https://image1\.ke\.com/[^"]*huxing[^"]*\.(?:jpg|png|webp))"', re.S)
        name_pattern = re.compile(r'>([\d]+室[^<{]*)<', re.S)

        img_matches = img_pattern.findall(html)
        name_matches = name_pattern.findall(html)

        seen = set()
        for i, img_url in enumerate(img_matches):
            if img_url in seen:
                continue
            seen.add(img_url)
            # 替换缩略图为大图
            big_url = img_url.replace(".210x146.jpg", "").replace(".240x180.jpg", "")
            name = name_matches[i] if i < len(name_matches) else f"户型{i+1}"
            floorplans.append({"url": big_url, "name": name.strip()})
            if len(floorplans) >= max_count:
                break
    except Exception:
        pass
    return floorplans

def download_image(url, save_path):
    """下载图片到本地"""
    try:
        resp = requests.get(url, headers=get_headers(), timeout=20)
        if resp.status_code == 200 and len(resp.content) > 5000:
            with open(save_path, "wb") as f:
                f.write(resp.content)
            return True
    except Exception:
        pass
    return False

def load_communities(filter_district=None, limit=None):
    """从价格数据加载小区列表"""
    if not PRICE_PATH.exists():
        print(f"价格数据不存在: {PRICE_PATH}")
        return []
    with open(PRICE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    if filter_district:
        data = [c for c in data if filter_district in (c.get("districts") or [])]
    if limit:
        data = data[:limit]
    return data

def main():
    parser = argparse.ArgumentParser(description='爬取贝壳户型图')
    parser.add_argument('--district', type=str, help='区域过滤')
    parser.add_argument('--limit', type=int, default=50, help='数量限制')
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 加载已爬取的映射
    floorplan_map = {}
    if FLOORPLAN_MAP_PATH.exists():
        with open(FLOORPLAN_MAP_PATH, "r", encoding="utf-8") as f:
            floorplan_map = json.load(f)
    print(f"已爬取户型图: {len(floorplan_map)} 个小区")

    communities = load_communities(args.district, args.limit)
    print(f"待处理小区: {len(communities)} 个")

    success = 0
    for i, c in enumerate(communities):
        name = c["name"]
        if name in floorplan_map and floorplan_map[name]:
            continue

        print(f"[{i+1}/{len(communities)}] {name} ...", end=" ")

        # 搜索小区ID
        cid = find_community_id(name)
        if not cid:
            print("未找到")
            time.sleep(random.uniform(1, 2))
            continue

        time.sleep(random.uniform(0.5, 1))

        # 爬取户型图
        floorplans = fetch_floorplans(cid, max_count=3)
        if not floorplans:
            print("无户型图")
            floorplan_map[name] = []
            time.sleep(random.uniform(1, 2))
            continue

        # 下载图片
        local_paths = []
        for j, fp in enumerate(floorplans):
            safe_name = re.sub(r'[^\w\u4e00-\u9fff]', '_', name)
            save_path = OUTPUT_DIR / f"{safe_name}_{j+1}.jpg"
            if download_image(fp["url"], save_path):
                local_paths.append({
                    "path": f"data/floorplans/{safe_name}_{j+1}.jpg",
                    "name": fp["name"],
                })

        if local_paths:
            floorplan_map[name] = local_paths
            print(f"下载 {len(local_paths)} 张")
            success += 1
        else:
            floorplan_map[name] = []
            print("下载失败")

        # 定期保存
        if (i + 1) % 10 == 0:
            with open(FLOORPLAN_MAP_PATH, "w", encoding="utf-8") as f:
                json.dump(floorplan_map, f, ensure_ascii=False, indent=2)

        time.sleep(random.uniform(2, 4))

    # 最终保存
    with open(FLOORPLAN_MAP_PATH, "w", encoding="utf-8") as f:
        json.dump(floorplan_map, f, ensure_ascii=False, indent=2)

    print(f"\n完成！成功爬取 {success}/{len(communities)} 个小区户型图")
    print(f"映射文件: {FLOORPLAN_MAP_PATH}")

if __name__ == "__main__":
    main()
