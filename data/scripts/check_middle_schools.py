#!/usr/bin/env python3
"""检查初中学校数据，为中考成绩模块做准备"""
import json

with open('visualization/data/school_data.js', 'r', encoding='utf-8') as f:
    content = f.read()

start = content.find('window.schools = ') + len('window.schools = ')
end = content.rfind(';')
schools = json.loads(content[start:end])

# 初中学校
middle_schools = [s for s in schools if s.get('school_type') == '初中' or '九年' in s.get('school_type', '')]
print(f'初中/九年一贯制学校数: {len(middle_schools)}')
print('\n所有初中学校:')
for s in middle_schools:
    print(f'  - {s["school_name"]} | {s["district"]} | {s.get("school_nature", "")} | 学生:{s.get("student_count", 0)}')

# 检查小区价格数据
with open('visualization/data/community_prices.js', 'r', encoding='utf-8') as f:
    content = f.read()
start = content.find('window.communityPrices = ') + len('window.communityPrices = ')
end = content.rfind(';')
prices = json.loads(content[start:end])

# 统计各区域有价格数据的小区
district_stats = {}
for p in prices:
    if p.get('avg_price', 0) > 0:
        for d in p.get('districts', []):
            if d not in district_stats:
                district_stats[d] = 0
            district_stats[d] += 1

print(f'\n各区域有价格数据的小区数:')
for d, cnt in sorted(district_stats.items(), key=lambda x: -x[1]):
    print(f'  {d}: {cnt}个')
