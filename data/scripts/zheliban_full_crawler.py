"""
浙里办「入学早知道」全维度数据采集脚本

覆盖数据维度:
1. 学校列表（公办/民办，小学/初中/九年一贯制）
2. 学校详情（地址、经纬度、师资、规模等）
3. 学区划分（户籍生/新杭州人对口小区）
4. 招生预警（红/黄/绿预警等级）
5. 招生计划（预计班数、人数）
6. 毕业去向 / 对口直升初中
7. 学校简介、招生简章

使用:
    python zheliban_full_crawler.py --sid YOUR_SID
    python zheliban_full_crawler.py --sid YOUR_SID --district 西湖区
    python zheliban_full_crawler.py --sid YOUR_SID --skip-detail   # 仅列表不采详情
    python zheliban_full_crawler.py --sid YOUR_SID --民办            # 含民办学校

获取 SID:
    1. 手机打开浙里办 APP → 搜索「入学早知道」
    2. 使用抓包工具(Charles/Stream)获取请求头中的 sid 值
    3. sid 格式: nuc-session-app-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

注意:
    - SID 有时效性，过期后需重新获取
    - 建议采集间隔 1-2 秒，避免触发风控
    - 全量采集约需 30-60 分钟（10个区 × 每区约50-100所学校）
"""

import json
import csv
import gzip
import time
import hashlib
import argparse
import traceback
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from datetime import datetime


# ============================================================
# 配置常量
# ============================================================

# API 入口 - 根据抓包结果可能是以下之一:
#   https://mapi.zjzwfw.gov.cn/web/mgop
#   https://mapi.zjzwfw.gov.cn/app/mgop
# 如果请求失败，尝试切换另一个
API_URL = "https://mapi.zjzwfw.gov.cn/web/mgop"

# 杭州各区行政编码
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

# API 名称
API_SCHOOL_LIST = "mgop.zjhcsoft.hzjysjrtpt.AppSchoolInfocustompaginatechild"
API_SCHOOL_DETAIL = "mgop.zjhcsoft.hzjysjrtpt.AppSchoolInfogetSchoolInfo"
API_SCHOOL_WARNING = "mgop.zjhcsoft.hzjysjrtpt.AppSchoolWarningInfo"
API_SCHOOL_GRADUATE = "mgop.zjhcsoft.hzjysjrtpt.AppSchoolGraduateInfo"

# 当前年份
CURRENT_YEAR = str(datetime.now().year)


# ============================================================
# 数据模型
# ============================================================

@dataclass
class SchoolBasic:
    """学校基本信息"""
    school_name: str = ""
    school_show_name: str = ""
    campus_name: str = ""
    school_code: str = ""
    district: str = ""
    district_code: str = ""
    school_type: str = ""
    school_type_code: str = ""
    school_nature: str = ""
    address: str = ""
    lng: str = ""
    lat: str = ""
    student_count: int = 0
    class_count: int = 0
    teacher_count: int = 0
    forecast_class_num: int = 0
    forecast_person_num: int = 0
    school_scope: str = ""
    direct_middle_school: str = ""
    school_tel: str = ""
    school_detail: str = ""
    enroll_file_url: str = ""
    school_logo: str = ""
    visit_times: int = 0
    year: str = CURRENT_YEAR
    has_child_campus: bool = False
    crawl_time: str = ""


@dataclass
class DistrictMapping:
    """学区划分 - 小区/社区与学校的对应关系"""
    community_name: str = ""
    community_code: str = ""
    school_name: str = ""
    school_code: str = ""
    street_name: str = ""
    street_code: str = ""
    social_community: str = ""
    district: str = ""
    student_type: str = ""
    is_show: str = "1"
    year: str = CURRENT_YEAR


@dataclass
class WarningInfo:
    """招生预警信息"""
    school_name: str = ""
    school_code: str = ""
    district: str = ""
    warning_level: str = ""
    warning_year: str = ""
    warning_desc: str = ""
    hj_warning: str = ""
    xhzr_warning: str = ""
    forecast_exceed: str = ""
    year: str = CURRENT_YEAR


@dataclass
class GraduateInfo:
    """毕业去向"""
    school_name: str = ""
    school_code: str = ""
    district: str = ""
    graduate_year: str = ""
    destination_school: str = ""
    destination_type: str = ""
    student_count: int = 0
    percentage: str = ""
    year: str = CURRENT_YEAR


# ============================================================
# HTTP 客户端
# ============================================================

class ZhelibanClient:
    """浙里办 API 请求客户端"""

    def __init__(self, sid: str, delay: float = 1.0):
        self.sid = sid
        self.delay = delay
        self.request_count = 0
        self.error_count = 0
        self.errors: list[str] = []
        self._last_request_time = 0

    def _build_headers(self, api: str, district_code: str) -> dict:
        ts = str(int(time.time() * 1000))
        sign = hashlib.md5(f"{ts}{self.sid}".encode()).hexdigest()
        return {
            "Host": "mapi.zjzwfw.gov.cn",
            "Content-Type": "application/json;charset=utf-8",
            "Content-Encoding": "gzip",
            "Accept": "*/*",
            "Accept-Language": "zh-Hans-CN;q=1",
            "Connection": "Keep-Alive",
            "User-Agent": "000001@ZLB_iphone_7.36.0",
            "X-App-Id": "2001936641",
            "X-Site-Code": district_code,
            "guc-accountType": "person",
            "guc-accountSource": "isv",
            "guc-platform": "app",
            "guc-endpoint": "C",
            "v": "1.0",
            "token": "abcdefg",
            "extra-ak": "pa1307y0+2001936641+rsisvm",
            "ttid": "zj_jl9vupjh+200100201+nytcfro_iOS_7.36.0",
            "uuid": "31a10520-67e0-4b24-bbef-4974cd7c19fa",
            "api": api,
            "sid": self.sid,
            "ts": ts,
            "sign": sign,
            "Cookie": (
                f"C_zj_accountType=person; "
                f"C_zj_gsid={self.sid}; "
                f"C_zj_platform=h5; "
                f"aliyungf_tc=b3981052de4d7813480c8190bc71a1e8d1f92a1f4261b1795ec44b8512033059; "
                f"cna=StXEIhovunEBASQOBHOk8Azt"
            ),
        }

    def _throttle(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self._last_request_time = time.time()

    def post(self, api: str, district_code: str, body: dict, retries: int = 3) -> dict:
        """发送请求，失败自动重试（指数退避）"""
        last_err = ""
        for attempt in range(retries):
            self._throttle()
            headers = self._build_headers(api, district_code)
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            req = Request(API_URL, data=data, headers=headers, method="POST")

            try:
                with urlopen(req, timeout=30) as response:
                    raw = response.read()
                    content_encoding = response.headers.get("Content-Encoding", "")
                    if "gzip" in content_encoding:
                        raw = gzip.decompress(raw)
                    result = json.loads(raw.decode("utf-8"))

                self.request_count += 1

                if not result.get("success"):
                    msg = result.get("message", "未知错误")
                    # 业务错误不重试
                    self.error_count += 1
                    self.errors.append(f"[{api}] {msg}")
                    return {}

                return result.get("result", {})

            except (HTTPError, URLError) as e:
                last_err = f"HTTP错误: {e}"
                if attempt < retries - 1:
                    wait = 2 ** attempt  # 1s, 2s, 4s
                    print(f"\n    [重试 {attempt+1}/{retries}] {last_err}，{wait}s后重试...", end="", flush=True)
                    time.sleep(wait)
                    continue
            except Exception as e:
                last_err = f"异常: {e}"
                if attempt < retries - 1:
                    wait = 2 ** attempt
                    time.sleep(wait)
                    continue

        self.error_count += 1
        self.errors.append(f"[{api}] {last_err}（重试{retries}次仍失败）")
        return {}


# ============================================================
# 全量采集器
# ============================================================

class ZhelibanFullCrawler:
    """浙里办全维度数据采集器"""

    def __init__(self, sid: str, delay: float = 1.0, year: str = CURRENT_YEAR):
        self.client = ZhelibanClient(sid, delay)
        self.year = year

        self.schools: list[SchoolBasic] = []
        self.district_mappings: list[DistrictMapping] = []
        self.warnings: list[WarningInfo] = []
        self.graduates: list[GraduateInfo] = []

        self.stats = {"districts": 0, "schools_fetched": 0, "details_fetched": 0}

    # ----------------------------------------------------------
    # 1. 学校列表采集
    # ----------------------------------------------------------

    def fetch_school_list(self, district: str, include_private: bool = False) -> list[dict]:
        dc = DISTRICT_CODES[district]
        all_records = []

        nature_list = ["非民办"]
        if include_private:
            nature_list.append("民办")

        combinations = []
        for nature in nature_list:
            combinations.append((f"{nature}-小学", [2, 5, 6, 7], "1", "", nature))
            combinations.append((f"{nature}-初中", [3, 5, 6, 7], "", "1", nature))

        for desc, st_values, flag_xx, flag_cz, gmblx in combinations:
            print(f"    [{desc}] ...", end=" ", flush=True)
            page, fetched, total = 0, 0, 0

            while True:
                body = {
                    "limit": 50,
                    "start": page * 50,
                    "orderByExpressions": [
                        {"orderByType": "asc", "column": "gmblxSort"},
                        {"orderByType": "desc", "column": "visitTimes"},
                    ],
                    "expressions": {
                        "active": {"op": "eq", "value": "1"},
                        "gmblx": {"op": "eq", "value": gmblx},
                        "szqdm": {"op": "lk", "value": dc},
                        "schoolName": {"op": "lk", "value": ""},
                        "schoolType": {"op": "in", "value": st_values},
                        "hideFlagJnxx": {"op": "eq", "value": flag_xx},
                        "hideFlagJncz": {"op": "eq", "value": flag_cz},
                        "hideFlag": {"op": "eq", "value": "true", "column": "hideFlag"},
                    },
                }

                result = self.client.post(API_SCHOOL_LIST, dc, body)
                if not result:
                    print("失败")
                    break

                records = result.get("records", [])
                total = result.get("total", 0)
                all_records.extend(records)
                fetched += len(records)

                if fetched >= total or not records:
                    break
                page += 1

            print(f"{fetched}/{total}")

        # 去重
        seen, unique = set(), []
        for r in all_records:
            key = r.get("xqbsm", "")
            if key and key not in seen:
                seen.add(key)
                unique.append(r)
            elif not key:
                unique.append(r)

        return unique

    def parse_list_records(self, records: list[dict], district: str):
        for r in records:
            sub_list = r.get("appSchoolInfoEntityList", [])
            if sub_list:
                for sub in sub_list:
                    school = self._parse_single_school(sub, district, parent=r)
                    school.has_child_campus = True
                    self.schools.append(school)
            else:
                school = self._parse_single_school(r, district)
                self.schools.append(school)

    def _parse_single_school(self, data: dict, district: str, parent: dict = None) -> SchoolBasic:
        type_code = str(data.get("schoolType", ""))
        return SchoolBasic(
            school_name=data.get("schoolName", "") or (parent or {}).get("schoolShowName", ""),
            school_show_name=data.get("schoolShowName", "") or data.get("schoolName", ""),
            campus_name=data.get("xqmc", ""),
            school_code=data.get("xqbsm", ""),
            district=district,
            district_code=DISTRICT_CODES.get(district, ""),
            school_type=SCHOOL_TYPE_MAP.get(type_code, f"未知({type_code})"),
            school_type_code=type_code,
            school_nature=data.get("gmblx", ""),
            address=data.get("address", ""),
            lng=str(data.get("lng", "")),
            lat=str(data.get("lat", "")),
            student_count=int(data.get("xsrs", 0) or 0),
            class_count=int(data.get("classTotalNum", 0) or 0),
            teacher_count=int(data.get("workerNumber", 0) or 0),
            forecast_class_num=int(data.get("forecastClassNum1", 0) or 0),
            forecast_person_num=int(data.get("forecastClassPerson1", 0) or 0),
            school_scope=data.get("schoolScope", ""),
            direct_middle_school=data.get("directMiddleSchoolName", "") or "",
            school_tel=data.get("schoolTel", ""),
            school_detail="",
            enroll_file_url=data.get("enrollFileUrl", "") or "",
            school_logo=data.get("schoolLogo", "") or "",
            visit_times=int(data.get("visitTimes", 0) or 0),
            year=data.get("year", self.year),
            has_child_campus=bool(data.get("child", False)),
            crawl_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    # ----------------------------------------------------------
    # 2. 学校详情采集（含学区划分）
    # ----------------------------------------------------------

    def fetch_school_detail(self, school_code: str, district: str) -> dict:
        dc = DISTRICT_CODES[district]
        body = {
            "xqbsm": school_code,
            "year": self.year,
            "source": "undefined",
            "schoolName": school_code,
        }
        return self.client.post(API_SCHOOL_DETAIL, dc, body)

    def parse_detail_result(self, result: dict, district: str):
        school_info = result.get("appSchoolInfoEntity", {})
        if school_info:
            code = school_info.get("xqbsm", "")
            for s in self.schools:
                if s.school_code == code:
                    s.address = school_info.get("address", "") or s.address
                    s.lng = str(school_info.get("lng", "")) or s.lng
                    s.lat = str(school_info.get("lat", "")) or s.lat
                    s.student_count = int(school_info.get("xsrs", 0) or 0) or s.student_count
                    s.class_count = int(school_info.get("classTotalNum", 0) or 0) or s.class_count
                    s.teacher_count = int(school_info.get("workerNumber", 0) or 0) or s.teacher_count
                    s.forecast_class_num = int(school_info.get("forecastClassNum1", 0) or 0) or s.forecast_class_num
                    s.forecast_person_num = int(school_info.get("forecastClassPerson1", 0) or 0) or s.forecast_person_num
                    s.school_scope = school_info.get("schoolScope", "") or s.school_scope
                    s.direct_middle_school = school_info.get("directMiddleSchoolName", "") or s.direct_middle_school
                    s.school_tel = school_info.get("schoolTel", "") or s.school_tel
                    s.school_detail = (school_info.get("schoolDetail", "") or "")[:500]
                    s.enroll_file_url = school_info.get("enrollFileUrl", "") or s.enroll_file_url
                    break

        # 户籍生对口小区
        for item in (result.get("appSchoolDistrictInfoEntityList") or []):
            self.district_mappings.append(DistrictMapping(
                community_name=item.get("name", "") or item.get("xqmc", ""),
                community_code=item.get("xqbm", "") or "",
                school_name=item.get("schoolName", ""),
                school_code=item.get("xqbsm", ""),
                street_name=item.get("jdmc", "") or item.get("streetName", ""),
                street_code=item.get("streetCode", "") or "",
                social_community=item.get("communityName", "") or item.get("sqmc", ""),
                district=district,
                student_type="户籍生",
                is_show=item.get("isShow", "1"),
                year=item.get("year", self.year),
            ))

        # 新杭州人对口小区
        for item in (result.get("appSchoolDistrictInfoEntityListNewHZR") or []):
            self.district_mappings.append(DistrictMapping(
                community_name=item.get("name", "") or item.get("xqmc", ""),
                community_code=item.get("xqbm", "") or "",
                school_name=item.get("schoolName", ""),
                school_code=item.get("xqbsm", ""),
                street_name=item.get("jdmc", "") or item.get("streetName", ""),
                street_code=item.get("streetCode", "") or "",
                social_community=item.get("communityName", "") or item.get("sqmc", ""),
                district=district,
                student_type="新杭州人",
                is_show=item.get("isShow", "1"),
                year=item.get("year", self.year),
            ))

        # 预警信息（如果详情接口包含）
        warning_data = result.get("warningInfo") or result.get("appSchoolWarningEntity")
        if warning_data:
            self.warnings.append(WarningInfo(
                school_name=school_info.get("schoolName", "") if school_info else "",
                school_code=school_info.get("xqbsm", "") if school_info else "",
                district=district,
                warning_level=warning_data.get("warningLevel", "") or warning_data.get("level", ""),
                warning_year=warning_data.get("year", self.year),
                warning_desc=warning_data.get("warningDesc", "") or warning_data.get("desc", ""),
                hj_warning=warning_data.get("hjWarning", ""),
                xhzr_warning=warning_data.get("xhzrWarning", ""),
                forecast_exceed=warning_data.get("forecastExceed", ""),
                year=self.year,
            ))

    # ----------------------------------------------------------
    # 3. 招生预警
    # ----------------------------------------------------------

    def fetch_warnings(self, district: str):
        dc = DISTRICT_CODES[district]
        body = {"year": self.year, "szqdm": dc}
        result = self.client.post(API_SCHOOL_WARNING, dc, body)
        if result:
            items = result if isinstance(result, list) else result.get("records", []) or result.get("list", [])
            for item in items:
                self.warnings.append(WarningInfo(
                    school_name=item.get("schoolName", "") or item.get("xxmc", ""),
                    school_code=item.get("xqbsm", "") or item.get("schoolCode", ""),
                    district=district,
                    warning_level=item.get("warningLevel", "") or item.get("level", ""),
                    warning_year=item.get("year", self.year),
                    warning_desc=item.get("warningDesc", "") or item.get("desc", ""),
                    hj_warning=item.get("hjWarning", "") or item.get("hjLevel", ""),
                    xhzr_warning=item.get("xhzrWarning", "") or item.get("xhzrLevel", ""),
                    forecast_exceed=item.get("forecastExceed", ""),
                    year=self.year,
                ))
            return len(items)
        return 0

    # ----------------------------------------------------------
    # 4. 毕业去向
    # ----------------------------------------------------------

    def fetch_graduate_info(self, school_code: str, district: str):
        dc = DISTRICT_CODES[district]
        body = {"xqbsm": school_code, "year": self.year}
        result = self.client.post(API_SCHOOL_GRADUATE, dc, body)
        if result:
            items = result if isinstance(result, list) else result.get("records", []) or result.get("list", [])
            for item in items:
                self.graduates.append(GraduateInfo(
                    school_name=item.get("schoolName", "") or item.get("xxmc", ""),
                    school_code=school_code,
                    district=district,
                    graduate_year=item.get("year", ""),
                    destination_school=item.get("destSchool", "") or item.get("middleSchool", ""),
                    destination_type=item.get("destType", "") or item.get("type", ""),
                    student_count=int(item.get("studentCount", 0) or 0),
                    percentage=item.get("percentage", "") or item.get("rate", ""),
                    year=self.year,
                ))

    # ----------------------------------------------------------
    # 主流程
    # ----------------------------------------------------------

    def crawl_district(self, district: str, include_private: bool = False,
                       fetch_detail: bool = True, fetch_warning: bool = True,
                       fetch_graduate: bool = True):
        print(f"\n{'='*60}")
        print(f"  {district} ({DISTRICT_CODES[district]})")
        print(f"{'='*60}")

        # Step 1: 学校列表
        print(f"\n  [1/4] 学校列表...")
        records = self.fetch_school_list(district, include_private)
        self.parse_list_records(records, district)
        school_count = len([s for s in self.schools if s.district == district])
        print(f"  => {school_count} 所学校")

        # Step 2: 详情和学区
        if fetch_detail:
            codes = list(set(
                s.school_code for s in self.schools
                if s.district == district and s.school_code
            ))
            print(f"\n  [2/4] 学校详情 + 学区划分 ({len(codes)} 所)...")
            for i, code in enumerate(codes):
                result = self.fetch_school_detail(code, district)
                if result:
                    self.parse_detail_result(result, district)
                    self.stats["details_fetched"] += 1
                if (i + 1) % 10 == 0:
                    mappings_count = len([m for m in self.district_mappings if m.district == district])
                    print(f"    进度: {i+1}/{len(codes)}, 学区映射: {mappings_count} 条")
        else:
            print(f"\n  [2/4] 跳过详情采集")

        # Step 3: 预警
        if fetch_warning:
            print(f"\n  [3/4] 招生预警...")
            warning_count = self.fetch_warnings(district)
            print(f"  => 预警信息: {warning_count} 条")
        else:
            print(f"\n  [3/4] 跳过预警采集")

        # Step 4: 毕业去向
        if fetch_graduate:
            primary_codes = list(set(
                s.school_code for s in self.schools
                if s.district == district and s.school_code
                and s.school_type in ("小学", "九年一贯制")
            ))
            print(f"\n  [4/4] 毕业去向 ({len(primary_codes)} 所小学)...")
            for i, code in enumerate(primary_codes):
                self.fetch_graduate_info(code, district)
                if (i + 1) % 10 == 0:
                    print(f"    进度: {i+1}/{len(primary_codes)}")
        else:
            print(f"\n  [4/4] 跳过毕业去向采集")

        self.stats["districts"] += 1

    def crawl_all(self, districts: list[str] = None, include_private: bool = False,
                  fetch_detail: bool = True, fetch_warning: bool = True,
                  fetch_graduate: bool = True):
        if districts is None:
            districts = list(DISTRICT_CODES.keys())

        print(f"\n{'#'*60}")
        print(f"  浙里办「入学早知道」全量采集")
        print(f"  区域: {', '.join(districts)}")
        print(f"  年份: {self.year}")
        print(f"  含民办: {'是' if include_private else '否'}")
        print(f"  采集详情: {'是' if fetch_detail else '否'}")
        print(f"{'#'*60}")

        for district in districts:
            if district not in DISTRICT_CODES:
                print(f"[WARN] 跳过无效区域: {district}")
                continue
            try:
                self.crawl_district(
                    district,
                    include_private=include_private,
                    fetch_detail=fetch_detail,
                    fetch_warning=fetch_warning,
                    fetch_graduate=fetch_graduate,
                )
            except KeyboardInterrupt:
                print("\n[中断] 用户取消，保存已采集数据...")
                break
            except Exception as e:
                print(f"\n[ERROR] {district} 采集失败: {e}")
                traceback.print_exc()
                continue

    # ----------------------------------------------------------
    # 数据保存
    # ----------------------------------------------------------

    def save_all(self, output_dir: Path = None):
        if output_dir is None:
            output_dir = Path(__file__).parent.parent

        raw_dir = output_dir / "raw"
        processed_dir = output_dir / "processed"
        raw_dir.mkdir(parents=True, exist_ok=True)
        processed_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d")

        if self.schools:
            self._save_json(self.schools, raw_dir / f"schools_{timestamp}.json")
            self._save_csv(self.schools, processed_dir / "schools.csv")
            print(f"  [OK] 学校: {len(self.schools)} 条")

        if self.district_mappings:
            self._save_json(self.district_mappings, raw_dir / f"district_mappings_{timestamp}.json")
            self._save_csv(self.district_mappings, processed_dir / "district_mappings.csv")
            print(f"  [OK] 学区映射: {len(self.district_mappings)} 条")

        if self.warnings:
            self._save_json(self.warnings, raw_dir / f"warnings_{timestamp}.json")
            self._save_csv(self.warnings, processed_dir / "warnings.csv")
            print(f"  [OK] 招生预警: {len(self.warnings)} 条")

        if self.graduates:
            self._save_json(self.graduates, raw_dir / f"graduates_{timestamp}.json")
            self._save_csv(self.graduates, processed_dir / "graduates.csv")
            print(f"  [OK] 毕业去向: {len(self.graduates)} 条")

        # 汇总
        summary = self._build_summary()
        with open(processed_dir / "crawl_summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f"  [OK] 采集汇总: crawl_summary.json")

    def _save_json(self, data: list, path: Path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump([asdict(d) for d in data], f, ensure_ascii=False, indent=2)

    def _save_csv(self, data: list, path: Path):
        if not data:
            return
        fieldnames = list(asdict(data[0]).keys())
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for item in data:
                writer.writerow(asdict(item))

    def _build_summary(self) -> dict:
        district_stats = {}
        for s in self.schools:
            d = s.district
            if d not in district_stats:
                district_stats[d] = {"公办小学": 0, "公办初中": 0, "民办": 0, "九年一贯制": 0, "total": 0}
            district_stats[d]["total"] += 1
            if "民办" in (s.school_nature or ""):
                district_stats[d]["民办"] += 1
            elif s.school_type == "小学":
                district_stats[d]["公办小学"] += 1
            elif s.school_type == "初中":
                district_stats[d]["公办初中"] += 1
            elif s.school_type == "九年一贯制":
                district_stats[d]["九年一贯制"] += 1

        return {
            "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "year": self.year,
            "total_schools": len(self.schools),
            "total_district_mappings": len(self.district_mappings),
            "total_warnings": len(self.warnings),
            "total_graduates": len(self.graduates),
            "requests": self.client.request_count,
            "errors": self.client.error_count,
            "district_stats": district_stats,
            "error_samples": self.client.errors[:10],
        }

    def print_summary(self):
        print(f"\n{'='*60}")
        print(f"  采集完成!")
        print(f"{'='*60}")
        print(f"  学校总数:     {len(self.schools)}")
        print(f"  学区映射:     {len(self.district_mappings)}")
        print(f"  招生预警:     {len(self.warnings)}")
        print(f"  毕业去向:     {len(self.graduates)}")
        print(f"  API 请求数:   {self.client.request_count}")
        print(f"  错误数:       {self.client.error_count}")

        print(f"\n  按区统计:")
        districts_in_data = sorted(set(s.district for s in self.schools))
        for d in districts_in_data:
            count = len([s for s in self.schools if s.district == d])
            mappings = len([m for m in self.district_mappings if m.district == d])
            print(f"    {d}: {count} 所学校, {mappings} 条学区映射")

        if self.client.errors:
            print(f"\n  前5个错误:")
            for err in self.client.errors[:5]:
                print(f"    - {err}")


# ============================================================
# 命令行入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="浙里办「入学早知道」全维度数据采集",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 全量采集（所有区、公办、含详情）
  python zheliban_full_crawler.py --sid nuc-session-app-xxx

  # 仅西湖区
  python zheliban_full_crawler.py --sid xxx --district 西湖区

  # 含民办学校
  python zheliban_full_crawler.py --sid xxx --民办

  # 仅列表，不采集详情（快速）
  python zheliban_full_crawler.py --sid xxx --skip-detail

  # 指定年份
  python zheliban_full_crawler.py --sid xxx --year 2025
        """,
    )
    parser.add_argument("--sid", required=True, help="浙里办会话ID (nuc-session-app-xxx)")
    parser.add_argument("--district", help="指定区名（如：西湖区），不指定则全量")
    parser.add_argument("--民办", action="store_true", dest="include_private", help="同时采集民办学校")
    parser.add_argument("--skip-detail", action="store_true", help="跳过详情采集（快速模式）")
    parser.add_argument("--skip-warning", action="store_true", help="跳过预警采集")
    parser.add_argument("--skip-graduate", action="store_true", help="跳过毕业去向采集")
    parser.add_argument("--year", default=CURRENT_YEAR, help=f"采集年份（默认 {CURRENT_YEAR}）")
    parser.add_argument("--delay", type=float, default=1.0, help="请求间隔秒数（默认 1.0）")
    parser.add_argument("--output", help="输出目录（默认为 data/）")

    args = parser.parse_args()

    districts = None
    if args.district:
        if args.district not in DISTRICT_CODES:
            print(f"[ERROR] 无效区名: {args.district}")
            print(f"可选: {', '.join(DISTRICT_CODES.keys())}")
            return
        districts = [args.district]

    output_dir = Path(args.output) if args.output else None

    crawler = ZhelibanFullCrawler(
        sid=args.sid,
        delay=args.delay,
        year=args.year,
    )

    start_time = time.time()

    crawler.crawl_all(
        districts=districts,
        include_private=args.include_private,
        fetch_detail=not args.skip_detail,
        fetch_warning=not args.skip_warning,
        fetch_graduate=not args.skip_graduate,
    )

    elapsed = time.time() - start_time
    print(f"\n  耗时: {elapsed:.1f} 秒 ({elapsed/60:.1f} 分钟)")

    print(f"\n  保存数据...")
    crawler.save_all(output_dir)

    crawler.print_summary()


if __name__ == "__main__":
    main()
