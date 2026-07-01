"""
浙里办「入学早知道」全量数据采集脚本

自动采集杭州所有区的学校列表 + 每个学校的对口小区数据

使用:
    python crawl_zheliban_all.py --sid YOUR_SID
    python crawl_zheliban_all.py --sid YOUR_SID --district 西湖区
    python crawl_zheliban_all.py --sid YOUR_SID --detail  # 含对口小区
"""

import json, csv, gzip, time, argparse, hashlib
from pathlib import Path
from dataclasses import dataclass, asdict
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

API_URL = "https://mapi.zjzwfw.gov.cn/app/mgop"
DISTRICT_CODES = {"上城区":"330102","拱墅区":"330105","西湖区":"330106","滨江区":"330108","萧山区":"330109","余杭区":"330110","富阳区":"330111","临安区":"330112","临平区":"330113","钱塘区":"330114"}
SCHOOL_TYPE_MAP = {"2":"小学","3":"初中","4":"高中","5":"九年一贯制","6":"十二年一贯制","7":"完全中学"}

@dataclass
class SchoolRecord:
    school_name: str; campus_name: str; school_code: str; district: str
    school_type: str; address: str; lng: str; lat: str
    student_count: int; class_count: int; teacher_count: int
    school_scope: str; direct_middle_school: str; school_nature: str
    forecast_class: int; forecast_person: int; school_tel: str; visit_times: int

@dataclass
class CommunityMapping:
    community_name: str; school_name: str; street_name: str
    social_community: str; district: str; student_type: str; year: str; school_code: str

class ZhelibanCrawler:
    def __init__(self, sid):
        self.sid = sid
        self.schools, self.mappings, self.req_count, self.errors = [], [], 0, []

    def _headers(self, api, dc):
        return {"Host":"mapi.zjzwfw.gov.cn","Content-Type":"application/json;charset=utf-8",
            "Accept":"*/*","User-Agent":"000001@ZLB_iphone_7.35.0","X-App-Id":"2001936641",
            "X-Site-Code":dc,"guc-accountType":"person","guc-platform":"app","guc-endpoint":"C",
            "v":"1.0","token":"abcdefg","extra-ak":"pa1307y0+2001936641+rsisvm",
            "ttid":"zj_jl9vupjh+200100201+nytcfro_iOS_7.35.0",
            "uuid":"d19828bc-ceb3-4023-8127-49a01b2b94ba","api":api,"sid":self.sid,
            "ts":str(int(time.time()*1000)),"sign":hashlib.md5(f"{time.time()}".encode()).hexdigest(),
            "Cookie":f"C_zj_accountType=person; C_zj_gsid={self.sid}; C_zj_platform=h5"}

    def _post(self, api, dc, body):
        req = Request(API_URL, json.dumps(body,ensure_ascii=False).encode("utf-8"),
                      self._headers(api,dc), method="POST")
        try:
            with urlopen(req, timeout=20) as r:
                raw = r.read()
                if "gzip" in (r.headers.get("Content-Encoding") or ""):
                    raw = gzip.decompress(raw)
                res = json.loads(raw.decode("utf-8"))
            self.req_count += 1
            if not res.get("success"):
                self.errors.append(res.get("message",""))
                return {}
            return res.get("result",{})
        except Exception as e:
            self.errors.append(str(e)); return {}

    def fetch_school_list(self, district):
        dc = DISTRICT_CODES[district]
        all_records = []
        for label, st_values, flag_xx, flag_cz in [
            ("小学",[2,5,6,7],"1",""), ("初中",[3,5,6,7],"","1")]:
            print(f"  获取{label}列表...")
            page, fetched = 0, 0
            while True:
                body = {"limit":50,"start":page*50,
                    "orderByExpressions":[{"orderByType":"asc","column":"gmblxSort"},
                                          {"orderByType":"desc","column":"visitTimes"}],
                    "expressions":{"active":{"op":"eq","value":"1"},
                        "gmblx":{"op":"eq","value":"非民办"},
                        "szqdm":{"op":"lk","value":dc},
                        "schoolName":{"op":"lk","value":""},
                        "schoolType":{"op":"in","value":st_values},
                        "hideFlagJnxx":{"op":"eq","value":flag_xx},
                        "hideFlagJncz":{"op":"eq","value":flag_cz},
                        "hideFlag":{"op":"eq","value":"true","column":"hideFlag"}}}
                result = self._post("mgop.zjhcsoft.hzjysjrtpt.AppSchoolInfocustompaginatechild",dc,body)
                recs = result.get("records",[])
                all_records.extend(recs)
                fetched += len(recs)
                total = result.get("total",0)
                print(f"    {fetched}/{total}")
                if fetched >= total or not recs: break
                page += 1; time.sleep(0.3)
        # 去重
        seen, unique = set(), []
        for r in all_records:
            k = r.get("xqbsm","")
            if k and k not in seen: seen.add(k); unique.append(r)
        print(f"  {district}: {len(unique)} 所学校")
        return unique

    def fetch_detail(self, district, code):
        return self._post("mgop.zjhcsoft.hzjysjrtpt.AppSchoolInfogetSchoolInfo",
                          DISTRICT_CODES[district], {"year":"2026","source":"undefined","schoolName":code})

    def parse_list(self, records, district):
        for r in records:
            ents = r.get("appSchoolInfoEntityList",[])
            if ents:
                for e in ents:
                    self.schools.append(SchoolRecord(
                        e.get("schoolName","") or r.get("schoolShowName",""),
                        e.get("xqmc",""), e.get("xqbsm",""), district,
                        SCHOOL_TYPE_MAP.get(str(e.get("schoolType","")),""),
                        e.get("address",""), str(e.get("lng","")), str(e.get("lat","")),
                        e.get("xsrs",0) or 0, e.get("classTotalNum",0) or 0,
                        e.get("workerNumber",0) or 0, e.get("schoolScope",""),
                        e.get("directMiddleSchoolName","") or "", e.get("gmblx",""),
                        e.get("forecastClassNum1",0) or 0, e.get("forecastClassPerson1",0) or 0,
                        e.get("schoolTel",""), e.get("visitTimes",0) or 0))
            else:
                self.schools.append(SchoolRecord(
                    r.get("schoolShowName",""), "", r.get("xqbsm",""), district,
                    SCHOOL_TYPE_MAP.get(str(r.get("schoolType","")),""),
                    "","","",0,0,0,"","",r.get("gmblx",""),0,0,"",
                    int(r.get("visitTimes",0) or 0)))

    def parse_detail(self, result, district):
        for key, stype in [("appSchoolDistrictInfoEntityList","户籍生"),
                           ("appSchoolDistrictInfoEntityListNewHZR","新杭州人")]:
            for item in (result.get(key) or []):
                self.mappings.append(CommunityMapping(
                    item.get("name","") or item.get("xqmc",""),
                    item.get("schoolName",""),
                    item.get("jdmc","") or item.get("streetName",""),
                    item.get("communityName","") or item.get("sqmc",""),
                    district, stype, item.get("year","2026"), item.get("xqbsm","")))

    def save(self):
        base = Path(__file__).parent.parent
        (base/"raw").mkdir(parents=True,exist_ok=True)
        (base/"processed").mkdir(parents=True,exist_ok=True)
        if self.schools:
            with open(base/"raw"/"zheliban_all_schools.json","w",encoding="utf-8") as f:
                json.dump([asdict(s) for s in self.schools],f,ensure_ascii=False,indent=2)
            with open(base/"processed"/"zheliban_all_schools.csv","w",encoding="utf-8-sig",newline="") as f:
                w=csv.DictWriter(f,list(asdict(self.schools[0]).keys())); w.writeheader()
                for s in self.schools: w.writerow(asdict(s))
            print(f"[保存] 学校: {len(self.schools)} 条")
        if self.mappings:
            with open(base/"raw"/"zheliban_all_mappings.json","w",encoding="utf-8") as f:
                json.dump([asdict(m) for m in self.mappings],f,ensure_ascii=False,indent=2)
            with open(base/"processed"/"zheliban_all_mappings.csv","w",encoding="utf-8-sig",newline="") as f:
                w=csv.DictWriter(f,list(asdict(self.mappings[0]).keys())); w.writeheader()
                for m in self.mappings: w.writerow(asdict(m))
            print(f"[保存] 小区映射: {len(self.mappings)} 条")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sid",required=True)
    ap.add_argument("--district")
    ap.add_argument("--detail",action="store_true",help="同时采集对口小区详情")
    args = ap.parse_args()

    c = ZhelibanCrawler(args.sid)
    districts = [args.district] if args.district else list(DISTRICT_CODES.keys())

    for d in districts:
        if d not in DISTRICT_CODES: continue
        print(f"\n{'='*50}\n[{d}]\n{'='*50}")
        recs = c.fetch_school_list(d)
        c.parse_list(recs, d)
        if args.detail:
            codes = set()
            for r in recs:
                for e in r.get("appSchoolInfoEntityList",[]):
                    codes.add(e.get("xqbsm",""))
                if not r.get("appSchoolInfoEntityList"):
                    codes.add(r.get("xqbsm",""))
            codes.discard("")
            print(f"  采集 {len(codes)} 个校区对口小区...")
            for i,code in enumerate(sorted(codes)):
                res = c.fetch_detail(d, code)
                if res: c.parse_detail(res, d)
                if (i+1)%5==0: print(f"    {i+1}/{len(codes)} 映射:{len(c.mappings)}")
                time.sleep(1)
        time.sleep(0.5)

    print(f"\n{'='*50}")
    print(f"完成! 学校:{len(c.schools)} 映射:{len(c.mappings)} 请求:{c.req_count} 错误:{len(c.errors)}")
    if c.errors[:3]: print(f"  前3个错误: {c.errors[:3]}")
    c.save()

if __name__=="__main__":
    main()
