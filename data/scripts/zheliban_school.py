"""
浙里办「入学早知道」学区数据采集脚本

数据来源：浙里办 APP / 浙江政务服务网
功能：采集杭州各区学校-小区对应关系

使用方式：
    python zheliban_school.py --district 西湖区
    python zheliban_school.py --all

输出：
    ../raw/school_community_mapping.json
    ../processed/school_community_mapping.csv
"""

import json
import csv
import argparse
import time
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional

# ============================================================
# 数据模型
# ============================================================

@dataclass
class SchoolCommunityMapping:
    """学校-小区对应关系"""
    school_name: str           # 学校名称
    school_level: str          # 学校等级: 省重点/市重点/区重点/普通
    school_type: str           # 学段: 小学/初中/九年一贯制
    district: str              # 所属区
    community_name: str        # 对口小区/社区名称
    enrollment_year: int       # 招生年度
    address: Optional[str] = None        # 学校地址
    contact_phone: Optional[str] = None  # 联系电话
    remarks: Optional[str] = None        # 备注（如多校划片说明）


# ============================================================
# 杭州各区配置
# ============================================================

HANGZHOU_DISTRICTS = [
    "上城区", "拱墅区", "西湖区", "滨江区",
    "余杭区", "萧山区", "临平区", "钱塘区",
    "富阳区", "临安区"
]

# ============================================================
# 数据采集器（骨架）
# ============================================================

class ZhelibanSchoolCrawler:
    """
    浙里办学区数据采集器
    
    注意：实际使用需要：
    1. 抓包获取浙里办 API 的真实 URL 和认证参数
    2. 或使用浙江政务服务网的公开接口
    3. 遵守数据使用规范
    """
    
    BASE_URL = "https://mapi.zjzwfw.gov.cn/web/mgop/gov-open/zj"
    
    def __init__(self):
        self.session = None
        self.data: list[SchoolCommunityMapping] = []
    
    def init_session(self, token: Optional[str] = None):
        """
        初始化请求会话
        
        TODO: 需要配置认证信息
        - 浙里办 APP 抓包获取 token
        - 或使用浙江政务服务网登录态
        """
        print("[INFO] 会话初始化（需配置真实认证信息）")
    
    def fetch_schools_by_district(self, district: str) -> list[dict]:
        """
        获取指定区的学校列表
        
        TODO: 对接真实 API
        """
        print(f"[INFO] 正在获取 {district} 的学校列表...")
        return []
    
    def fetch_school_communities(self, school_id: str) -> list[str]:
        """
        获取指定学校的对口小区列表
        
        TODO: 对接真实 API
        """
        return []
    
    def crawl_district(self, district: str):
        """采集单个区的数据"""
        schools = self.fetch_schools_by_district(district)
        
        for school in schools:
            communities = self.fetch_school_communities(school.get("id", ""))
            
            for community in communities:
                mapping = SchoolCommunityMapping(
                    school_name=school.get("name", ""),
                    school_level=school.get("level", "普通"),
                    school_type=school.get("type", "小学"),
                    district=district,
                    community_name=community,
                    enrollment_year=2025,
                    address=school.get("address"),
                    remarks=school.get("remarks"),
                )
                self.data.append(mapping)
            
            time.sleep(1)  # 限速，避免被封
    
    def crawl_all(self):
        """采集所有区的数据"""
        for district in HANGZHOU_DISTRICTS:
            self.crawl_district(district)
            time.sleep(2)
    
    def save_json(self, output_path: str):
        """保存为 JSON"""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump([asdict(d) for d in self.data], f, ensure_ascii=False, indent=2)
        print(f"[INFO] JSON 已保存: {output_path} ({len(self.data)} 条)")
    
    def save_csv(self, output_path: str):
        """保存为 CSV"""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        if not self.data:
            print("[WARN] 无数据可保存")
            return
        
        fieldnames = list(asdict(self.data[0]).keys())
        with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for item in self.data:
                writer.writerow(asdict(item))
        print(f"[INFO] CSV 已保存: {output_path} ({len(self.data)} 条)")


# ============================================================
# 备选方案：从教育局公告 PDF 提取数据
# ============================================================

class EducationBureauParser:
    """
    从杭州各区教育局网站的招生公告中解析学区数据
    
    数据来源：
    - 西湖区教育局: http://www.xhqjy.com/
    - 上城区教育局: https://www.hzscjy.com/
    - ...
    """
    
    def parse_pdf(self, pdf_path: str) -> list[SchoolCommunityMapping]:
        """
        解析学区划分 PDF
        
        TODO: 使用 pdfplumber 或 PyPDF2 提取表格数据
        """
        return []


# ============================================================
# 主程序
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="浙里办学区数据采集")
    parser.add_argument("--district", type=str, help="指定区名（如：西湖区）")
    parser.add_argument("--all", action="store_true", help="采集所有区")
    parser.add_argument("--token", type=str, help="浙里办认证 token")
    args = parser.parse_args()
    
    crawler = ZhelibanSchoolCrawler()
    crawler.init_session(token=args.token)
    
    if args.all:
        crawler.crawl_all()
    elif args.district:
        if args.district not in HANGZHOU_DISTRICTS:
            print(f"[ERROR] 无效区名: {args.district}")
            print(f"可选: {', '.join(HANGZHOU_DISTRICTS)}")
            return
        crawler.crawl_district(args.district)
    else:
        print("[INFO] 请指定 --district 或 --all")
        print("[INFO] 当前为演示模式，生成示例数据...")
        
        # 生成示例数据
        sample_data = [
            SchoolCommunityMapping("杭州市学军小学(求智校区)", "省重点", "小学", "西湖区", "求智社区", 2025),
            SchoolCommunityMapping("杭州市学军小学(求智校区)", "省重点", "小学", "西湖区", "文三新村", 2025),
            SchoolCommunityMapping("杭州市文三教育集团文三街小学", "市重点", "小学", "西湖区", "文三街社区", 2025),
            SchoolCommunityMapping("杭州市十三中教育集团", "省重点", "初中", "西湖区", "文教社区", 2025),
            SchoolCommunityMapping("杭州市天长小学", "省重点", "小学", "上城区", "岳王路社区", 2025),
            SchoolCommunityMapping("杭州市胜利小学", "省重点", "小学", "上城区", "近江社区", 2025),
            SchoolCommunityMapping("杭州市卖鱼桥小学", "市重点", "小学", "拱墅区", "卖鱼桥社区", 2025),
            SchoolCommunityMapping("杭州市育才中学", "省重点", "初中", "拱墅区", "大关社区", 2025),
            SchoolCommunityMapping("杭州江南实验学校", "市重点", "九年一贯制", "滨江区", "月明社区", 2025),
            SchoolCommunityMapping("杭州市闻涛小学", "区重点", "小学", "滨江区", "闻涛社区", 2025),
        ]
        crawler.data = sample_data
    
    # 保存数据
    base_dir = Path(__file__).parent.parent
    crawler.save_json(str(base_dir / "raw" / "school_community_mapping.json"))
    crawler.save_csv(str(base_dir / "processed" / "school_community_mapping.csv"))


if __name__ == "__main__":
    main()
