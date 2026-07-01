"""
杭州中小学数据采集脚本 - 基于高德地图 POI API

高德地图 POI 分类编码：
- 141200: 中小学校（大类）
  - 141201: 小学
  - 141202: 中学
- 141100: 幼儿园

使用前准备：
1. 注册高德开放平台: https://lbs.amap.com/
2. 创建应用获取 Web服务 API Key
3. 设置环境变量: export AMAP_KEY=你的key

使用方式：
    python fetch_hangzhou_schools.py
    python fetch_hangzhou_schools.py --type 小学
    python fetch_hangzhou_schools.py --district 西湖区

输出：
    ../raw/hangzhou_schools.json
    ../processed/hangzhou_schools.csv
"""

import json
import csv
import time
import os
import argparse
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError


# ============================================================
# 配置
# ============================================================

AMAP_KEY = os.environ.get("AMAP_KEY", "")

# 杭州市行政区划编码(高德)
HANGZHOU_DISTRICTS = {
    "上城区": "330102",
    "拱墅区": "330105",
    "西湖区": "330106",
    "滨江区": "330108",
    "萧山区": "330109",
    "余杭区": "330110",
    "富阳区": "330111",
    "临安区": "330112",
    "临平区": "330113",
    "钱塘区": "330114",
}

# POI 类型编码
POI_TYPES = {
    "小学": "141201",
    "中学": "141202",
    "中小学校": "141200",
    "幼儿园": "141100",
}


# ============================================================
# 数据模型
# ============================================================

@dataclass
class SchoolInfo:
    """学校信息"""
    name: str
    school_type: str
    district: str
    address: str
    location_lng: float
    location_lat: float
    tel: str = ""
    pname: str = ""
    cityname: str = ""
    adname: str = ""
    poi_id: str = ""
    business_area: str = ""


# ============================================================
# 高德地图 POI 采集器
# ============================================================

class AmapSchoolFetcher:
    """高德地图学校 POI 数据采集器"""

    BASE_URL = "https://restapi.amap.com/v3/place/text"

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError(
                "请设置高德地图 API Key!\n"
                "1. 注册: https://lbs.amap.com/\n"
                "2. 创建应用获取 Key\n"
                "3. export AMAP_KEY=你的key"
            )
        self.api_key = api_key
        self.schools: list[SchoolInfo] = []
        self.request_count = 0

    def _request(self, params: dict) -> dict:
        """发送 API 请求"""
        params["key"] = self.api_key
        params["output"] = "json"

        url = f"{self.BASE_URL}?{urlencode(params)}"

        try:
            req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))

            self.request_count += 1

            if data.get("status") != "1":
                print(f"[ERROR] API 错误: {data.get('info', '未知错误')}")
                return {"pois": [], "count": "0"}

            return data
        except (HTTPError, URLError) as e:
            print(f"[ERROR] 网络请求失败: {e}")
            return {"pois": [], "count": "0"}

    def fetch_by_district(self, district_name: str, poi_type: str = "141200", school_type_label: str = "中小学校"):
        """获取指定区的学校列表（分页）"""
        district_code = HANGZHOU_DISTRICTS.get(district_name)
        if not district_code:
            print(f"[WARN] 未知区域: {district_name}")
            return

        print(f"[INFO] 正在获取 {district_name} 的 {school_type_label} 数据...")

        page = 1
        page_size = 25
        total_fetched = 0

        while True:
            params = {
                "types": poi_type,
                "city": "330100",
                "citylimit": "true",
                "district": district_code,
                "page": str(page),
                "offset": str(page_size),
                "extensions": "all",
            }

            data = self._request(params)
            pois = data.get("pois", [])
            total_count = int(data.get("count", "0"))

            if not pois:
                break

            for poi in pois:
                location = poi.get("location", "0,0").split(",")
                lng = float(location[0]) if len(location) == 2 else 0
                lat = float(location[1]) if len(location) == 2 else 0

                school = SchoolInfo(
                    name=poi.get("name", ""),
                    school_type=school_type_label,
                    district=district_name,
                    address=poi.get("address", "") if isinstance(poi.get("address"), str) else "",
                    location_lng=lng,
                    location_lat=lat,
                    tel=poi.get("tel", "") if isinstance(poi.get("tel"), str) else "",
                    pname=poi.get("pname", ""),
                    cityname=poi.get("cityname", ""),
                    adname=poi.get("adname", ""),
                    poi_id=poi.get("id", ""),
                    business_area=poi.get("business_area", "") if isinstance(poi.get("business_area"), str) else "",
                )
                self.schools.append(school)

            total_fetched += len(pois)
            print(f"  第{page}页: 获取{len(pois)}条, 累计{total_fetched}/{total_count}")

            if total_fetched >= total_count or page * page_size >= 1000:
                break

            page += 1
            time.sleep(0.3)

        print(f"  {district_name} {school_type_label} 完成: {total_fetched} 条")

    def fetch_all_districts(self, school_types: list[str] = None):
        """获取所有区的学校数据"""
        if school_types is None:
            school_types = ["小学", "中学"]

        for school_type in school_types:
            poi_type = POI_TYPES.get(school_type, "141200")
            print(f"\n{'='*50}")
            print(f"开始采集: {school_type} (POI类型: {poi_type})")
            print(f"{'='*50}")

            for district_name in HANGZHOU_DISTRICTS:
                self.fetch_by_district(district_name, poi_type, school_type)
                time.sleep(0.5)

        print(f"\n[INFO] 采集完成! 总计 {len(self.schools)} 所学校, API请求 {self.request_count} 次")

    def deduplicate(self):
        """去重"""
        seen = set()
        unique_schools = []
        for school in self.schools:
            key = (school.name, school.district)
            if key not in seen:
                seen.add(key)
                unique_schools.append(school)

        removed = len(self.schools) - len(unique_schools)
        self.schools = unique_schools
        if removed > 0:
            print(f"[INFO] 去重: 移除 {removed} 条重复记录, 剩余 {len(self.schools)} 条")

    def save_json(self, output_path: str):
        """保存为 JSON"""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump([asdict(s) for s in self.schools], f, ensure_ascii=False, indent=2)
        print(f"[INFO] JSON 已保存: {output_path} ({len(self.schools)} 条)")

    def save_csv(self, output_path: str):
        """保存为 CSV"""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        if not self.schools:
            print("[WARN] 无数据可保存")
            return

        fieldnames = list(asdict(self.schools[0]).keys())
        with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for school in self.schools:
                writer.writerow(asdict(school))
        print(f"[INFO] CSV 已保存: {output_path} ({len(self.schools)} 条)")

    def print_summary(self):
        """打印统计摘要"""
        print(f"\n{'='*50}")
        print("采集结果统计")
        print(f"{'='*50}")

        district_count = {}
        type_count = {}
        for s in self.schools:
            district_count[s.district] = district_count.get(s.district, 0) + 1
            type_count[s.school_type] = type_count.get(s.school_type, 0) + 1

        print("\n按区域:")
        for d, c in sorted(district_count.items(), key=lambda x: -x[1]):
            print(f"  {d}: {c} 所")

        print("\n按类型:")
        for t, c in sorted(type_count.items(), key=lambda x: -x[1]):
            print(f"  {t}: {c} 所")

        print(f"\n总计: {len(self.schools)} 所学校")


# ============================================================
# 主程序
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="杭州中小学数据采集（高德地图POI）")
    parser.add_argument("--type", type=str, choices=["小学", "中学", "幼儿园", "全部"],
                        default="全部", help="学校类型")
    parser.add_argument("--district", type=str, help="指定区名（如：西湖区）")
    parser.add_argument("--key", type=str, help="高德地图 API Key")
    args = parser.parse_args()

    api_key = args.key or AMAP_KEY

    if not api_key:
        print("=" * 60)
        print("错误: 未设置高德地图 API Key!")
        print("=" * 60)
        print()
        print("请按以下步骤获取 Key:")
        print("1. 访问 https://lbs.amap.com/ 注册账号")
        print("2. 进入控制台 -> 应用管理 -> 创建新应用")
        print("3. 添加 Key, 服务平台选择 'Web服务'")
        print("4. 获取 Key 后通过以下方式使用:")
        print()
        print("   方式1: 环境变量")
        print("   export AMAP_KEY=你的key")
        print("   python fetch_hangzhou_schools.py")
        print()
        print("   方式2: 命令行参数")
        print("   python fetch_hangzhou_schools.py --key 你的key")
        print()
        print("高德地图个人开发者每天 5000 次免费配额，足够采集全杭州学校数据。")
        return

    fetcher = AmapSchoolFetcher(api_key)

    if args.type == "全部":
        school_types = ["小学", "中学"]
    else:
        school_types = [args.type]

    if args.district:
        if args.district not in HANGZHOU_DISTRICTS:
            print(f"[ERROR] 无效区名: {args.district}")
            print(f"可选: {', '.join(HANGZHOU_DISTRICTS.keys())}")
            return
        for st in school_types:
            poi_type = POI_TYPES.get(st, "141200")
            fetcher.fetch_by_district(args.district, poi_type, st)
    else:
        fetcher.fetch_all_districts(school_types)

    fetcher.deduplicate()
    fetcher.print_summary()

    base_dir = Path(__file__).parent.parent
    fetcher.save_json(str(base_dir / "raw" / "hangzhou_schools.json"))
    fetcher.save_csv(str(base_dir / "processed" / "hangzhou_schools.csv"))

    print("\n[DONE] 采集完成!")


if __name__ == "__main__":
    main()
