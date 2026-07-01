"""
浙里办「入学早知道」学区数据采集脚本

接口来源: mapi.zjzwfw.gov.cn
API: mgop.zjhcsoft.hzjysjrtpt.AppSchoolInfogetSchoolInfo

采集内容:
- 学校基本信息（名称、地址、经纬度、招生班数、对口初中等）
- 户籍生对口小区列表
- 新杭州人对口小区列表

使用方式:
    python fetch_zheliban_schools.py --sid YOUR_SID --school-code 2133000225001
    python fetch_zheliban_schools.py --sid YOUR_SID --all-known

注意:
    需要有效的 session (sid)，从浙里办 APP 抓包获取
    session 有效期有限，过期需重新获取
"""

import json
import csv
import time
import gzip
import argparse
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError


# ============================================================
# 配置
# ============================================================

API_URL = "https://mapi.zjzwfw.gov.cn"

DISTRICT_CODES = {
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

DEFAULT_HEADERS = {
    "Host": "mapi.zjzwfw.gov.cn",
    "Content-Type": "application/json;charset=utf-8",
    "Accept": "*/*",
    "Accept-Language": "zh-Hans-CN;q=1",
    "Connection": "Keep-Alive",
    "User-Agent": "000001@ZLB_iphone_7.35.0",
    "X-App-Id": "2001936641",
    "guc-accountType": "person",
    "guc-platform": "app",
    "guc-endpoint": "C",
    "v": "1.0",
    "token": "abcdefg",
    "extra-ak": "pa1307y0+2001936641+rsivsm",
    "ttid": "zj_jl9vupjh+200100201+nytcfro_iOS_7.35.0",
    "api": "mgop.zjhcsoft.hzjysjrtpt.AppSchoolInfogetSchoolInfo",
}


# ============================================================
# 数据模型
# ============================================================

@dataclass
class SchoolDetail:
    school_name: str
    school_short_name: str
    campus_name: str
    district: str
    address: str
    lng: float
    lat: float
    school_code: str
    school_type: str
    school_nature: str
    school_scope: str
    direct_middle_school: str
    student_count: int
    class_count: int
    teacher_count: int
    forecast_class_num: int
    forecast_class_person: int
    school_tel: str
    school_detail: str
    enroll_file_url: str
    year: str


@dataclass
class CommunitySchoolMapping:
    community_name: str
    school_name: str
    street_name: str
    social_community: str
    district: str
    student_type: str
    year: str
    community_code: str
    street_code: str
    is_show: str
    school_code: str


# ============================================================
# 采集器
# ============================================================

class ZhelibanFetcher:

    def __init__(self, sid: str, uuid: str = "d19828bc-ceb3-4023-8127-49a01b2b94ba"):
        self.sid = sid
        self.uuid = uuid
        self.schools: list[SchoolDetail] = []
        self.mappings: list[CommunitySchoolMapping] = []
        self.request_count = 0

    def _build_headers(self, district_code: str) -> dict:
        headers = DEFAULT_HEADERS.copy()
        headers["X-Site-Code"] = district_code
        headers["sid"] = self.sid
        headers["uuid"] = self.uuid
        headers["ts"] = str(int(time.time() * 1000))
        headers["Cookie"] = (
            f"C_zj_accountType=person; "
            f"C_zj_gsid={self.sid}; "
            f"C_zj_platform=h5"
        )
        return headers

    def _request(self, district_code: str, body: dict) -> dict:
        headers = self._build_headers(district_code)
        data = json.dumps(body).encode("utf-8")
        req = Request(API_URL, data=data, headers=headers, method="POST")

        try:
            with urlopen(req, timeout=15) as response:
                raw = response.read()
                if response.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                result = json.loads(raw.decode("utf-8"))

            self.request_count += 1

            if not result.get("success"):
                print(f"  [ERROR] API错误: {result.get('message', '未知')}")
                return {}

            return result.get("result", {})

        except (HTTPError, URLError) as e:
            print(f"  [ERROR] 请求失败: {e}")
            return {}
        except Exception as e:
            print(f"  [ERROR] 解析失败: {e}")
            return {}

    def fetch_school_detail(self, district_name: str, school_code: str) -> dict:
        district_code = DISTRICT_CODES.get(district_name, "330106")
        body = {"xqbsm": school_code, "year": "2026"}
        print(f"  正在获取: {school_code} ...")
        return self._request(district_code, body)

    def parse_school_result(self, result: dict, district_name: str):
        school_info = result.get("appSchoolInfoEntity", {})
        if school_info:
            school = SchoolDetail(
                school_name=school_info.get("showSchoolName", ""),
                school_short_name=school_info.get("xxmc", ""),
                campus_name=school_info.get("xqmc", ""),
                district=school_info.get("szqmc", district_name),
                address=school_info.get("address", ""),
                lng=float(school_info.get("lng", 0) or 0),
                lat=float(school_info.get("lat", 0) or 0),
                school_code=school_info.get("xqbsm", ""),
                school_type=self._parse_school_type(school_info.get("schoolType", "")),
                school_nature=school_info.get("gmblx", ""),
                school_scope=school_info.get("schoolScope", ""),
                direct_middle_school=school_info.get("directMiddleSchoolName", "") or "",
                student_count=school_info.get("xsrs", 0) or 0,
                class_count=school_info.get("classTotalNum", 0) or 0,
                teacher_count=school_info.get("workerNumber", 0) or 0,
                forecast_class_num=school_info.get("forecastClassNum1", 0) or 0,
                forecast_class_person=school_info.get("forecastClassPerson1", 0) or 0,
                school_tel=school_info.get("schoolTel", ""),
                school_detail=(school_info.get("schoolDetail", "") or "")[:200],
                enroll_file_url=school_info.get("enrollFileUrl", "") or "",
                year=school_info.get("year", "2026"),
            )
            self.schools.append(school)
            print(f"    ✓ {school.school_name} | {school.address} | 对口初中: {school.direct_middle_school}")

        # 户籍生对口小区
        for item in (result.get("appSchoolDistrictInfoEntityList") or []):
            self.mappings.append(CommunitySchoolMapping(
                community_name=item.get("name", "") or item.get("xqmc", ""),
                school_name=item.get("schoolName", ""),
                street_name=item.get("jdmc", "") or item.get("streetName", ""),
                social_community=item.get("communityName", "") or item.get("sqmc", ""),
                district=district_name,
                student_type="户籍生",
                year=item.get("year", "2026"),
                community_code=item.get("xqbm", "") or "",
                street_code=item.get("streetCode", ""),
                is_show=item.get("isShow", "1"),
                school_code=item.get("xqbsm", ""),
            ))

        # 新杭州人对口小区
        for item in (result.get("appSchoolDistrictInfoEntityListNewHZR") or []):
            self.mappings.append(CommunitySchoolMapping(
                community_name=item.get("name", "") or item.get("xqmc", ""),
                school_name=item.get("schoolName", ""),
                street_name=item.get("jdmc", "") or item.get("streetName", ""),
                social_community=item.get("communityName", "") or item.get("sqmc", ""),
                district=district_name,
                student_type="新杭州人",
                year=item.get("year", "2026"),
                community_code="",
                street_code=item.get("streetCode", ""),
                is_show=item.get("isShow", "1"),
                school_code=item.get("xqbsm", ""),
            ))

    def _parse_school_type(self, type_code) -> str:
        return {"1": "幼儿园", "2": "小学", "3": "初中", "4": "九年一贯制", "5": "高中"
                }.get(str(type_code), f"未知({type_code})")

    def save_all(self):
        base_dir = Path(__file__).parent.parent

        if self.schools:
            path = base_dir / "raw" / "zheliban_schools.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump([asdict(s) for s in self.schools], f, ensure_ascii=False, indent=2)
            print(f"[INFO] 学校信息: {path} ({len(self.schools)} 所)")

        if self.mappings:
            path_json = base_dir / "raw" / "zheliban_community_school_mapping.json"
            with open(path_json, "w", encoding="utf-8") as f:
                json.dump([asdict(m) for m in self.mappings], f, ensure_ascii=False, indent=2)
            print(f"[INFO] 小区映射 JSON: {path_json} ({len(self.mappings)} 条)")

            path_csv = base_dir / "processed" / "zheliban_community_school_mapping.csv"
            path_csv.parent.mkdir(parents=True, exist_ok=True)
            fieldnames = list(asdict(self.mappings[0]).keys())
            with open(path_csv, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for m in self.mappings:
                    writer.writerow(asdict(m))
            print(f"[INFO] 小区映射 CSV: {path_csv} ({len(self.mappings)} 条)")

    def print_summary(self):
        print(f"\n{'='*60}")
        print(f"学校: {len(self.schools)} 所 | 小区映射: {len(self.mappings)} 条 | 请求: {self.request_count} 次")
        if self.mappings:
            school_count = {}
            for m in self.mappings:
                school_count[m.school_name] = school_count.get(m.school_name, 0) + 1
            print(f"\n对口小区数 Top 10:")
            for name, count in sorted(school_count.items(), key=lambda x: -x[1])[:10]:
                print(f"  {name}: {count} 个小区")


# ============================================================
# 已知学校编码 (从抓包逐步补充)
# ============================================================

KNOWN_SCHOOL_CODES = {
    "西湖区": [
        "2133000225001",  # 杭州市竞舟小学（竞舟校区）
        # 在浙里办 APP 中查看其他学校时，抓包记录 xqbsm 值
        # 然后添加到这里
    ],
}


def main():
    parser = argparse.ArgumentParser(description="浙里办学区数据采集")
    parser.add_argument("--sid", type=str, required=True,
                        help="会话ID (抓包中的 sid 字段值)")
    parser.add_argument("--district", type=str, default="西湖区")
    parser.add_argument("--school-code", type=str,
                        help="学校编码 (xqbsm)")
    parser.add_argument("--all-known", action="store_true",
                        help="采集所有已知学校")
    args = parser.parse_args()

    fetcher = ZhelibanFetcher(sid=args.sid)

    if args.school_code:
        print(f"[INFO] 采集: {args.school_code} ({args.district})")
        result = fetcher.fetch_school_detail(args.district, args.school_code)
        if result:
            fetcher.parse_school_result(result, args.district)
    elif args.all_known:
        for district, codes in KNOWN_SCHOOL_CODES.items():
            print(f"\n[INFO] {district} ({len(codes)} 所)")
            for code in codes:
                result = fetcher.fetch_school_detail(district, code)
                if result:
                    fetcher.parse_school_result(result, district)
                time.sleep(1.5)
    else:
        print("用法:")
        print(f"  python {Path(__file__).name} --sid YOUR_SID --school-code 2133000225001")
        print(f"  python {Path(__file__).name} --sid YOUR_SID --all-known")
        print()
        print("你的 SID: nuc-session-app-4275ff19c6c34c44a7bd5c1a6357bdce")
        print("竞舟小学编码: 2133000225001")
        return

    fetcher.print_summary()
    fetcher.save_all()


if __name__ == "__main__":
    main()
