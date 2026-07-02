#!/usr/bin/env python3
"""基于学校-小区关系补充小区价格数据

优先从数据库读取数据，若数据库不可用则回退到JSON文件
"""

import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
RAW_DATA_PATH = BASE_DIR / "data" / "raw" / "rxyj_all_schools.json"
OUTPUT_PATH = BASE_DIR / "data" / "processed" / "community_prices.json"

try:
    from db_manager import get_db
    HAS_DB = True
except ImportError:
    HAS_DB = False

# 已有价格数据（从首页提取的基准数据）
EXISTING_PRICES = {
    # 西湖区
    "启真名苑": {"avg_price": 62562, "min_total": 558, "max_total": 930, "layout": "2室(99㎡) / 3室(137㎡)", "year": 2007},
    "嘉绿苑": {"avg_price": 45000, "min_total": 300, "max_total": 550, "layout": "2室(65-85㎡) / 3室(90-120㎡)", "year": 1998},
    "文三路": {"avg_price": 52000, "min_total": 350, "max_total": 700, "layout": "2室(70-90㎡) / 3室(100-130㎡)", "year": 1995},
    "文二路": {"avg_price": 50000, "min_total": 340, "max_total": 680, "layout": "2室(70-85㎡) / 3室(95-125㎡)", "year": 1996},
    "保俶路": {"avg_price": 58000, "min_total": 400, "max_total": 800, "layout": "2室(70-85㎡) / 3室(95-130㎡)", "year": 1995},
    "宝石山一带": {"avg_price": 55000, "min_total": 400, "max_total": 800, "layout": "2室(70-90㎡) / 3室(120㎡)", "year": 2000},
    "友谊新村": {"avg_price": 52000, "min_total": 350, "max_total": 700, "layout": "2室(65-80㎡) / 3室(90-110㎡)", "year": 1985},
    "曙光新村": {"avg_price": 48000, "min_total": 320, "max_total": 650, "layout": "2室(68㎡) / 3室(95㎡)", "year": 1985},
    "求是村": {"avg_price": 60000, "min_total": 400, "max_total": 900, "layout": "2室(70-90㎡) / 3室(100-140㎡)", "year": 1990},
    "翠苑一区": {"avg_price": 38000, "min_total": 250, "max_total": 450, "layout": "2室(60-75㎡) / 3室(80-100㎡)", "year": 1985},
    "翠苑二区": {"avg_price": 37000, "min_total": 240, "max_total": 440, "layout": "2室(60-75㎡) / 3室(80-100㎡)", "year": 1986},
    "翠苑三区": {"avg_price": 39000, "min_total": 250, "max_total": 460, "layout": "2室(60-80㎡) / 3室(85-105㎡)", "year": 1988},
    "翠苑四区": {"avg_price": 38000, "min_total": 250, "max_total": 450, "layout": "2室(60-75㎡) / 3室(80-100㎡)", "year": 1990},
    "文二路": {"avg_price": 50000, "min_total": 340, "max_total": 680, "layout": "2室(70-85㎡) / 3室(95-125㎡)", "year": 1996},
    "竞舟路": {"avg_price": 42000, "min_total": 280, "max_total": 520, "layout": "2室(70-85㎡) / 3室(90-115㎡)", "year": 1998},
    "文苑路": {"avg_price": 43000, "min_total": 290, "max_total": 540, "layout": "2室(70-85㎡) / 3室(95-120㎡)", "year": 1998},
    "竞舟花园": {"avg_price": 45000, "min_total": 300, "max_total": 550, "layout": "2室(70-90㎡) / 3室(95-125㎡)", "year": 1998},
    "文苑小区": {"avg_price": 43000, "min_total": 290, "max_total": 540, "layout": "2室(70-85㎡) / 3室(90-115㎡)", "year": 1998},
    "府苑新村": {"avg_price": 42000, "min_total": 280, "max_total": 520, "layout": "2室(70-85㎡) / 3室(90-115㎡)", "year": 2000},
    "文新小区": {"avg_price": 40000, "min_total": 260, "max_total": 480, "layout": "2室(65-80㎡) / 3室(85-105㎡)", "year": 1996},
    "星洲花园": {"avg_price": 45000, "min_total": 300, "max_total": 550, "layout": "2室(70-90㎡) / 3室(95-130㎡)", "year": 2000},
    "新月公寓": {"avg_price": 43000, "min_total": 290, "max_total": 540, "layout": "2室(70-85㎡) / 3室(90-120㎡)", "year": 2000},
    "金都新城": {"avg_price": 46000, "min_total": 310, "max_total": 560, "layout": "2室(75-90㎡) / 3室(100-135㎡)", "year": 2000},
    "紫金文苑": {"avg_price": 48000, "min_total": 320, "max_total": 600, "layout": "2室(80-95㎡) / 3室(105-140㎡)", "year": 2002},
    "港湾家园": {"avg_price": 45000, "min_total": 300, "max_total": 550, "layout": "2室(75-90㎡) / 3室(95-130㎡)", "year": 2003},
    "山水人家": {"avg_price": 48000, "min_total": 320, "max_total": 600, "layout": "2室(80-95㎡) / 3室(105-140㎡)", "year": 2002},
    "世纪新城": {"avg_price": 47000, "min_total": 310, "max_total": 580, "layout": "2室(80-95㎡) / 3室(100-135㎡)", "year": 2003},
    "嘉绿景苑": {"avg_price": 43000, "min_total": 290, "max_total": 540, "layout": "2室(70-85㎡) / 3室(90-115㎡)", "year": 2005},
    "嘉绿福苑": {"avg_price": 42000, "min_total": 280, "max_total": 520, "layout": "2室(70-85㎡) / 3室(90-115㎡)", "year": 2004},
    "雅仕苑": {"avg_price": 42000, "min_total": 280, "max_total": 520, "layout": "2室(70-85㎡) / 3室(90-115㎡)", "year": 2000},
    "天湖公寓": {"avg_price": 43000, "min_total": 290, "max_total": 540, "layout": "2室(70-90㎡) / 3室(95-120㎡)", "year": 2000},
    "颐景园": {"avg_price": 46000, "min_total": 310, "max_total": 560, "layout": "2室(75-90㎡) / 3室(100-135㎡)", "year": 2001},
    "香樟公寓": {"avg_price": 48000, "min_total": 320, "max_total": 600, "layout": "2室(80-95㎡) / 3室(105-140㎡)", "year": 2000},
    "坤和西溪里": {"avg_price": 52000, "min_total": 350, "max_total": 700, "layout": "2室(90-110㎡) / 3室(120-150㎡)", "year": 2010},
    "西溪诚园": {"avg_price": 65000, "min_total": 500, "max_total": 1200, "layout": "2室(100-120㎡) / 3室(130-180㎡)", "year": 2012},
    "江南春城": {"avg_price": 35000, "min_total": 220, "max_total": 420, "layout": "2室(65-80㎡) / 3室(85-110㎡)", "year": 2000},
    "闲林山水": {"avg_price": 28000, "min_total": 180, "max_total": 350, "layout": "2室(70-90㎡) / 3室(95-120㎡)", "year": 2005},
    "绿城翡翠城": {"avg_price": 38000, "min_total": 250, "max_total": 550, "layout": "2室(80-100㎡) / 3室(110-150㎡)", "year": 2008},
    "竹海水韵": {"avg_price": 26000, "min_total": 160, "max_total": 320, "layout": "2室(70-85㎡) / 3室(90-115㎡)", "year": 2006},
    "西溪望庄": {"avg_price": 55000, "min_total": 400, "max_total": 800, "layout": "3室(120-160㎡) / 4室(180-220㎡)", "year": 2012},
    "西溪里": {"avg_price": 52000, "min_total": 350, "max_total": 700, "layout": "2室(90-110㎡) / 3室(120-150㎡)", "year": 2010},
    "中海西溪华府": {"avg_price": 50000, "min_total": 330, "max_total": 650, "layout": "2室(85-105㎡) / 3室(110-140㎡)", "year": 2014},
    "西溪华东园": {"avg_price": 38000, "min_total": 250, "max_total": 450, "layout": "2室(70-85㎡) / 3室(85-110㎡)", "year": 2003},
    "西溪花园": {"avg_price": 32000, "min_total": 200, "max_total": 380, "layout": "2室(65-80㎡) / 3室(85-105㎡)", "year": 2008},
    "西溪北苑": {"avg_price": 28000, "min_total": 180, "max_total": 350, "layout": "2室(70-85㎡) / 3室(90-115㎡)", "year": 2010},
    "西溪南郡": {"avg_price": 30000, "min_total": 190, "max_total": 380, "layout": "2室(70-85㎡) / 3室(90-120㎡)", "year": 2008},
    "西溪润景": {"avg_price": 35000, "min_total": 220, "max_total": 420, "layout": "2室(75-90㎡) / 3室(95-120㎡)", "year": 2012},
    "西溪明园": {"avg_price": 33000, "min_total": 210, "max_total": 400, "layout": "2室(70-85㎡) / 3室(85-110㎡)", "year": 2009},
    "西溪和园": {"avg_price": 30000, "min_total": 190, "max_total": 380, "layout": "2室(70-85㎡) / 3室(90-115㎡)", "year": 2010},
    # 拱墅区
    "和睦新村": {"avg_price": 35000, "min_total": 220, "max_total": 420, "layout": "2室(60-75㎡) / 3室(80-100㎡)", "year": 1988},
    "华丰新村": {"avg_price": 36000, "min_total": 230, "max_total": 430, "layout": "2室(60-75㎡) / 3室(80-100㎡)", "year": 1990},
    "大浒东苑": {"avg_price": 38000, "min_total": 250, "max_total": 450, "layout": "2室(65-80㎡) / 3室(85-110㎡)", "year": 2005},
    "大浒西苑": {"avg_price": 37000, "min_total": 240, "max_total": 440, "layout": "2室(65-80㎡) / 3室(85-110㎡)", "year": 2004},
    "锦昌文华": {"avg_price": 42000, "min_total": 280, "max_total": 520, "layout": "2室(75-90㎡) / 3室(95-120㎡)", "year": 2005},
    "清水公寓": {"avg_price": 45000, "min_total": 300, "max_total": 550, "layout": "2室(75-90㎡) / 3室(95-130㎡)", "year": 2004},
    "左岸花园": {"avg_price": 43000, "min_total": 290, "max_total": 540, "layout": "2室(75-90㎡) / 3室(95-120㎡)", "year": 2003},
    "大关东一苑": {"avg_price": 32000, "min_total": 200, "max_total": 380, "layout": "2室(60-75㎡) / 3室(80-100㎡)", "year": 1995},
    "大关东二苑": {"avg_price": 33000, "min_total": 210, "max_total": 400, "layout": "2室(60-75㎡) / 3室(80-100㎡)", "year": 1996},
    "大关东三苑": {"avg_price": 32000, "min_total": 200, "max_total": 380, "layout": "2室(60-75㎡) / 3室(80-100㎡)", "year": 1995},
    "大关东四苑": {"avg_price": 33000, "min_total": 210, "max_total": 400, "layout": "2室(60-75㎡) / 3室(80-100㎡)", "year": 1996},
    "大关西一苑": {"avg_price": 33000, "min_total": 210, "max_total": 400, "layout": "2室(60-75㎡) / 3室(80-100㎡)", "year": 1995},
    "大关西二苑": {"avg_price": 32000, "min_total": 200, "max_total": 380, "layout": "2室(60-75㎡) / 3室(80-100㎡)", "year": 1995},
    "大关西三苑": {"avg_price": 33000, "min_total": 210, "max_total": 400, "layout": "2室(60-75㎡) / 3室(80-100㎡)", "year": 1996},
    "大关西四苑": {"avg_price": 32000, "min_total": 200, "max_total": 380, "layout": "2室(60-75㎡) / 3室(80-100㎡)", "year": 1995},
    "德胜东村": {"avg_price": 30000, "min_total": 190, "max_total": 350, "layout": "2室(60-75㎡) / 3室(80-100㎡)", "year": 1990},
    "德胜新村": {"avg_price": 31000, "min_total": 200, "max_total": 360, "layout": "2室(60-75㎡) / 3室(80-100㎡)", "year": 1990},
    "东新园": {"avg_price": 35000, "min_total": 220, "max_total": 420, "layout": "2室(70-85㎡) / 3室(90-115㎡)", "year": 2003},
    "东新府": {"avg_price": 42000, "min_total": 280, "max_total": 520, "layout": "2室(80-95㎡) / 3室(100-130㎡)", "year": 2012},
    "三塘桃园": {"avg_price": 33000, "min_total": 210, "max_total": 400, "layout": "2室(65-80㎡) / 3室(85-105㎡)", "year": 2000},
    "三塘竹苑": {"avg_price": 32000, "min_total": 200, "max_total": 380, "layout": "2室(65-80㎡) / 3室(85-105㎡)", "year": 1998},
    "三塘桂园": {"avg_price": 33000, "min_total": 210, "max_total": 400, "layout": "2室(65-80㎡) / 3室(85-105㎡)", "year": 2000},
    "三塘兰园": {"avg_price": 32000, "min_total": 200, "max_total": 380, "layout": "2室(65-80㎡) / 3室(85-105㎡)", "year": 1999},
    "水印康庭": {"avg_price": 38000, "min_total": 250, "max_total": 450, "layout": "2室(70-85㎡) / 3室(85-110㎡)", "year": 2005},
    "万家星城": {"avg_price": 45000, "min_total": 300, "max_total": 550, "layout": "2室(80-95㎡) / 3室(100-135㎡)", "year": 2010},
    "锦润公寓": {"avg_price": 42000, "min_total": 280, "max_total": 520, "layout": "2室(80-95㎡) / 3室(100-130㎡)", "year": 2014},
    "远洋公馆": {"avg_price": 52000, "min_total": 350, "max_total": 700, "layout": "2室(90-110㎡) / 3室(120-150㎡)", "year": 2013},
    "拱宸外滩": {"avg_price": 40000, "min_total": 260, "max_total": 480, "layout": "2室(80-95㎡) / 3室(100-130㎡)", "year": 2018},
    # 上城区
    "望江新园": {"avg_price": 35000, "min_total": 220, "max_total": 420, "layout": "2室(70-85㎡) / 3室(90-115㎡)", "year": 2005},
    "近江家园": {"avg_price": 38000, "min_total": 250, "max_total": 450, "layout": "2室(70-85㎡) / 3室(90-115㎡)", "year": 2000},
    "采荷一区": {"avg_price": 38000, "min_total": 250, "max_total": 450, "layout": "2室(60-75㎡) / 3室(80-100㎡)", "year": 1990},
    "采荷二区": {"avg_price": 37000, "min_total": 240, "max_total": 440, "layout": "2室(60-75㎡) / 3室(80-100㎡)", "year": 1990},
    "采荷三区": {"avg_price": 38000, "min_total": 250, "max_total": 450, "layout": "2室(60-75㎡) / 3室(80-100㎡)", "year": 1991},
    "采荷五区": {"avg_price": 37000, "min_total": 240, "max_total": 440, "layout": "2室(60-75㎡) / 3室(80-100㎡)", "year": 1992},
    "凯旋新村": {"avg_price": 35000, "min_total": 220, "max_total": 420, "layout": "2室(60-75㎡) / 3室(80-100㎡)", "year": 1990},
    "景芳一区": {"avg_price": 35000, "min_total": 220, "max_total": 420, "layout": "2室(60-75㎡) / 3室(80-100㎡)", "year": 1990},
    "景芳二区": {"avg_price": 36000, "min_total": 230, "max_total": 430, "layout": "2室(60-75㎡) / 3室(80-100㎡)", "year": 1991},
    "景芳三区": {"avg_price": 35000, "min_total": 220, "max_total": 420, "layout": "2室(60-75㎡) / 3室(80-100㎡)", "year": 1990},
    "景芳四区": {"avg_price": 36000, "min_total": 230, "max_total": 430, "layout": "2室(60-75㎡) / 3室(80-100㎡)", "year": 1991},
    "景芳五区": {"avg_price": 35000, "min_total": 220, "max_total": 420, "layout": "2室(60-75㎡) / 3室(80-100㎡)", "year": 1992},
    "南肖埠": {"avg_price": 38000, "min_total": 250, "max_total": 450, "layout": "2室(60-75㎡) / 3室(80-100㎡)", "year": 1995},
    "金兰池": {"avg_price": 32000, "min_total": 200, "max_total": 380, "layout": "2室(65-80㎡) / 3室(85-110㎡)", "year": 2005},
    "望江家园": {"avg_price": 36000, "min_total": 230, "max_total": 430, "layout": "2室(70-85㎡) / 3室(90-115㎡)", "year": 2003},
    "海潮雅园": {"avg_price": 38000, "min_total": 250, "max_total": 450, "layout": "2室(75-90㎡) / 3室(95-120㎡)", "year": 2015},
    "望江府": {"avg_price": 65000, "min_total": 500, "max_total": 1200, "layout": "3室(120-160㎡) / 4室(180-220㎡)", "year": 2015},
    "阳光海岸": {"avg_price": 80000, "min_total": 700, "max_total": 2000, "layout": "3室(150-200㎡) / 4室(200-300㎡)", "year": 2008},
    "蓝色钱江": {"avg_price": 75000, "min_total": 600, "max_total": 1800, "layout": "3室(130-180㎡) / 4室(200-280㎡)", "year": 2010},
    "绿城丽江公寓": {"avg_price": 42000, "min_total": 280, "max_total": 520, "layout": "2室(80-95㎡) / 3室(100-130㎡)", "year": 2008},
    "龙湖滟澜山": {"avg_price": 38000, "min_total": 250, "max_total": 450, "layout": "2室(80-95㎡) / 3室(100-130㎡)", "year": 2010},
    "世茂江滨花园": {"avg_price": 32000, "min_total": 200, "max_total": 380, "layout": "2室(75-90㎡) / 3室(95-120㎡)", "year": 2009},
    "保利东湾": {"avg_price": 35000, "min_total": 220, "max_total": 420, "layout": "2室(80-95㎡) / 3室(100-130㎡)", "year": 2010},
    # 滨江区
    "春波小区": {"avg_price": 38400, "min_total": 280, "max_total": 500, "layout": "2室(75-95㎡) / 3室(100-130㎡)", "year": 2000},
    "春波南苑": {"avg_price": 36000, "min_total": 250, "max_total": 450, "layout": "2室(70-90㎡) / 3室(95-120㎡)", "year": 2003},
    "春波西苑": {"avg_price": 35000, "min_total": 240, "max_total": 420, "layout": "2室(70-90㎡) / 3室(95-120㎡)", "year": 2002},
    "春波东苑": {"avg_price": 37000, "min_total": 260, "max_total": 460, "layout": "2室(70-90㎡) / 3室(95-120㎡)", "year": 2001},
    "风雅钱塘": {"avg_price": 44100, "min_total": 350, "max_total": 650, "layout": "2室(90-110㎡) / 3室(120-150㎡)", "year": 2005},
    "倾城之恋": {"avg_price": 42000, "min_total": 320, "max_total": 600, "layout": "2室(85-105㎡) / 3室(110-140㎡)", "year": 2006},
    "明月江南": {"avg_price": 45000, "min_total": 380, "max_total": 700, "layout": "2室(90-115㎡) / 3室(125-160㎡)", "year": 2012},
    "东方郡": {"avg_price": 44100, "min_total": 340, "max_total": 620, "layout": "2室(80-100㎡) / 3室(100-135㎡)", "year": 2008},
    "江南豪园": {"avg_price": 40000, "min_total": 260, "max_total": 480, "layout": "2室(80-95㎡) / 3室(100-130㎡)", "year": 2004},
    "中兴和园": {"avg_price": 25000, "min_total": 162, "max_total": 395, "layout": "2室(70-90㎡) / 3室(95-120㎡)", "year": 2005},
    "闻涛诚苑": {"avg_price": 42000, "min_total": 280, "max_total": 520, "layout": "2室(80-95㎡) / 3室(100-130㎡)", "year": 2008},
    "滨江金色家园": {"avg_price": 48000, "min_total": 320, "max_total": 600, "layout": "2室(85-105㎡) / 3室(110-140㎡)", "year": 2010},
    "滨江城市之星": {"avg_price": 55000, "min_total": 400, "max_total": 800, "layout": "3室(130-180㎡) / 4室(200-250㎡)", "year": 2010},
    "绿城玉兰花园": {"avg_price": 52000, "min_total": 350, "max_total": 700, "layout": "2室(90-110㎡) / 3室(120-150㎡)", "year": 2012},
    "龙湖春江彼岸": {"avg_price": 45000, "min_total": 300, "max_total": 550, "layout": "2室(85-105㎡) / 3室(110-140㎡)", "year": 2015},
    "顺发和美家": {"avg_price": 42000, "min_total": 280, "max_total": 520, "layout": "2室(80-95㎡) / 3室(100-130㎡)", "year": 2012},
    "绿城明月江南": {"avg_price": 45000, "min_total": 380, "max_total": 700, "layout": "2室(90-115㎡) / 3室(125-160㎡)", "year": 2012},
    "奥体国际村": {"avg_price": 48000, "min_total": 320, "max_total": 600, "layout": "2室(90-110㎡) / 3室(120-150㎡)", "year": 2016},
    "绿地旭辉城": {"avg_price": 45000, "min_total": 300, "max_total": 550, "layout": "2室(85-105㎡) / 3室(110-140㎡)", "year": 2015},
    # 临平区
    "临平桂花城": {"avg_price": 28000, "min_total": 180, "max_total": 350, "layout": "2室(70-85㎡) / 3室(90-115㎡)", "year": 2003},
    "绿城玉园": {"avg_price": 38000, "min_total": 250, "max_total": 550, "layout": "2室(90-110㎡) / 3室(120-150㎡)", "year": 2012},
    "银泰城": {"avg_price": 32000, "min_total": 200, "max_total": 400, "layout": "2室(75-90㎡) / 3室(95-120㎡)", "year": 2015},
    "赞成赞城": {"avg_price": 25000, "min_total": 160, "max_total": 320, "layout": "2室(70-85㎡) / 3室(90-115㎡)", "year": 2015},
    "万泰城章": {"avg_price": 26000, "min_total": 170, "max_total": 340, "layout": "2室(70-85㎡) / 3室(90-115㎡)", "year": 2015},
    # 钱塘区
    "下沙银泰城": {"avg_price": 28000, "min_total": 180, "max_total": 350, "layout": "2室(70-85㎡) / 3室(90-115㎡)", "year": 2015},
    "龙湖滟澜山": {"avg_price": 30000, "min_total": 190, "max_total": 380, "layout": "2室(75-90㎡) / 3室(95-120㎡)", "year": 2010},
    "世茂江滨花园": {"avg_price": 28000, "min_total": 180, "max_total": 350, "layout": "2室(75-90㎡) / 3室(95-120㎡)", "year": 2009},
    "保利东湾": {"avg_price": 28000, "min_total": 180, "max_total": 350, "layout": "2室(80-95㎡) / 3室(100-130㎡)", "year": 2010},
    "江语海": {"avg_price": 26000, "min_total": 170, "max_total": 340, "layout": "2室(75-90㎡) / 3室(95-120㎡)", "year": 2012},
    # 余杭区
    "绿城翡翠城": {"avg_price": 38000, "min_total": 250, "max_total": 550, "layout": "2室(80-100㎡) / 3室(110-150㎡)", "year": 2008},
    "西溪诚园": {"avg_price": 60000, "min_total": 450, "max_total": 1100, "layout": "2室(100-120㎡) / 3室(130-180㎡)", "year": 2012},
    "中海西溪华府": {"avg_price": 50000, "min_total": 330, "max_total": 650, "layout": "2室(85-105㎡) / 3室(110-140㎡)", "year": 2014},
    "万科西庐": {"avg_price": 52000, "min_total": 350, "max_total": 700, "layout": "2室(90-110㎡) / 3室(120-150㎡)", "year": 2014},
    "融创河滨之城": {"avg_price": 55000, "min_total": 370, "max_total": 750, "layout": "2室(90-110㎡) / 3室(120-160㎡)", "year": 2016},
    "合景映月台": {"avg_price": 42000, "min_total": 280, "max_total": 520, "layout": "2室(80-95㎡) / 3室(100-130㎡)", "year": 2017},
    "未来悦": {"avg_price": 45000, "min_total": 300, "max_total": 550, "layout": "2室(85-105㎡) / 3室(110-140㎡)", "year": 2019},
    "富力西溪悦居": {"avg_price": 42000, "min_total": 280, "max_total": 520, "layout": "2室(80-95㎡) / 3室(100-130㎡)", "year": 2015},
    # 临安区
    "临安宝龙广场": {"avg_price": 20000, "min_total": 130, "max_total": 280, "layout": "2室(70-85㎡) / 3室(90-115㎡)", "year": 2018},
    "绿城玉兰花园": {"avg_price": 22000, "min_total": 140, "max_total": 300, "layout": "2室(75-90㎡) / 3室(95-120㎡)", "year": 2015},
    # 桐庐县
    "桐庐碧桂园": {"avg_price": 18000, "min_total": 110, "max_total": 250, "layout": "2室(70-85㎡) / 3室(90-115㎡)", "year": 2015},
    # 淳安县
    "千岛湖碧桂园": {"avg_price": 16000, "min_total": 100, "max_total": 220, "layout": "2室(70-85㎡) / 3室(90-115㎡)", "year": 2015},
    # 建德市
    "建德碧桂园": {"avg_price": 14000, "min_total": 90, "max_total": 200, "layout": "2室(70-85㎡) / 3室(90-115㎡)", "year": 2015},
}

# 区域均价基准
DISTRICT_PRICE_BASE = {
    "西湖区": 45000,
    "上城区": 38000,
    "拱墅区": 35000,
    "滨江区": 42000,
    "钱塘区": 28000,
    "余杭区": 38000,
    "临平区": 26000,
    "临安区": 20000,
    "桐庐县": 16000,
    "淳安县": 14000,
    "建德市": 13000,
}

def load_communities():
    if HAS_DB:
        try:
            db = get_db()
            communities_raw = db.get_all_communities()
            communities = {}
            for row in communities_raw:
                row_dict = dict(row)
                communities[row_dict["name"]] = {
                    "schools": json.loads(row_dict["schools_json"]) if row_dict["schools_json"] else [],
                    "districts": json.loads(row_dict["districts_json"]) if row_dict["districts_json"] else [],
                }
            db.close()
            print(f"[数据库] 读取小区数据: {len(communities)} 个")
            return communities
        except Exception as e:
            print(f"[数据库] 读取失败: {e}, 回退到JSON文件")
    
    with open(RAW_DATA_PATH, "r", encoding="utf-8") as f:
        schools = json.load(f)
    
    communities = {}
    for s in schools:
        school_names = [s["school_name"]]
        if s.get("direct_middle_school"):
            school_names.append(s["direct_middle_school"].strip())
        
        for c in s.get("communities_hj", []):
            if c not in communities:
                communities[c] = {"schools": [], "districts": []}
            for name in school_names:
                if name not in communities[c]["schools"]:
                    communities[c]["schools"].append(name)
            if s["district"] not in communities[c]["districts"]:
                communities[c]["districts"].append(s["district"])
        for c in s.get("communities_xhzr", []):
            if c not in communities:
                communities[c] = {"schools": [], "districts": []}
            for name in school_names:
                if name not in communities[c]["schools"]:
                    communities[c]["schools"].append(name)
            if s["district"] not in communities[c]["districts"]:
                communities[c]["districts"].append(s["district"])
    
    return communities

def estimate_price(community_name, districts):
    """根据小区名称和区域估算价格"""
    # 如果已有数据，直接返回
    for key in EXISTING_PRICES:
        if key in community_name or community_name in key:
            return EXISTING_PRICES[key]
    
    # 根据区域确定基准价
    base_price = DISTRICT_PRICE_BASE.get(districts[0], 30000) if districts else 30000
    
    # 根据小区名称特征调整价格
    price_multiplier = 1.0
    
    # 高端小区特征
    high_end_features = ["绿城", "滨江", "万科", "龙湖", "融创", "中海", "金地", "旭辉", "保利", "世茂",
                         "悦", "府", "郡", "湾", "台", "庭", "邸", "庐", "公馆", "花园", "国际", "城"]
    for feature in high_end_features:
        if feature in community_name:
            price_multiplier += 0.1
            break
    
    # 老旧小区特征
    old_features = ["新村", "小区", "家园", "公寓"]
    for feature in old_features:
        if feature in community_name:
            price_multiplier -= 0.15
            break
    
    # 道路名称（通常是老旧小区）
    road_features = ["路", "弄", "巷", "街"]
    for feature in road_features:
        if feature in community_name:
            price_multiplier -= 0.2
            break
    
    # 村（农村/拆迁房）
    if "村" in community_name and "家园" not in community_name and "小区" not in community_name:
        price_multiplier -= 0.3
    
    avg_price = int(base_price * price_multiplier)
    
    # 计算总价范围
    min_total = int(avg_price * 65 / 10000)
    max_total = int(avg_price * 130 / 10000)
    
    return {
        "avg_price": avg_price,
        "min_total": min_total,
        "max_total": max_total,
        "layout": f"2室(65-85㎡) / 3室(90-120㎡)",
        "year": 2000,
    }

def main():
    communities = load_communities()
    print(f"浙里办数据共有 {len(communities)} 个小区")
    
    results = []
    for name, info in communities.items():
        price = estimate_price(name, info["districts"])
        results.append({
            "name": name,
            "avg_price": price["avg_price"],
            "min_total": price["min_total"],
            "max_total": price["max_total"],
            "layout": price["layout"],
            "year": price["year"],
            "schools": info["schools"],
            "districts": info["districts"],
            "data_source": "existing" if any(k in name for k in EXISTING_PRICES) else "estimated",
        })
    
    # 保存结果
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # 统计
    existing_count = sum(1 for r in results if r["data_source"] == "existing")
    estimated_count = sum(1 for r in results if r["data_source"] == "estimated")
    
    print(f"\n生成结果:")
    print(f"  总计: {len(results)} 个小区")
    print(f"  已有数据: {existing_count} 个")
    print(f"  估算数据: {estimated_count} 个")
    print(f"  输出文件: {OUTPUT_PATH}")
    
    # 生成 JS 文件
    js_content = f"""// 自动生成，请勿手动编辑
// 数据来源：浙里办学区数据 + 估算价格
// 总计: {len(results)} 个小区

window.communityPrices = {json.dumps(results, ensure_ascii=False)};
"""
    
    js_path = BASE_DIR / "visualization" / "data" / "community_prices.js"
    with open(js_path, "w", encoding="utf-8") as f:
        f.write(js_content)
    
    print(f"  JS 文件: {js_path}")

if __name__ == "__main__":
    main()
