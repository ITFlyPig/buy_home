#!/usr/bin/env python3
"""检查数据文件中的字段和内容"""
import json

# 检查学校数据中的字段
with open('visualization/data/school_data.js', 'r', encoding='utf-8') as f:
    content = f.read()

# 提取window.schools数据
start = content.find('window.schools = ') + len('window.schools = ')
end = content.rfind(';')
schools = json.loads(content[start:end])

print(f'学校总数: {len(schools)}')
print(f'字段列表: {list(schools[0].keys())}')

# 检查初中学校
middle_schools = [s for s in schools if s.get('school_type') == '初中' or '九年' in s.get('school_type', '')]
print(f'\n初中/九年一贯制学校数: {len(middle_schools)}')
print(f'初中学校样例: {[s["school_name"] for s in middle_schools[:10]]}')

# 检查是否有杭二白马湖
baimahu = [s for s in schools if '白马湖' in s.get('school_name', '')]
print(f'\n白马湖学校: {[s["school_name"] for s in baimahu]}')

# 检查是否有十五中
shiwuzhong = [s for s in schools if '十五' in s.get('school_name', '')]
print(f'十五中学校: {[s["school_name"] for s in shiwuzhong]}')

# 检查community_prices数据
with open('visualization/data/community_prices.js', 'r', encoding='utf-8') as f:
    content = f.read()
start = content.find('window.communityPrices = ') + len('window.communityPrices = ')
end = content.rfind(';')
prices = json.loads(content[start:end])
print(f'\n小区价格数据: {len(prices)} 条')
has_price = [p for p in prices if p.get('avg_price', 0) > 0]
print(f'有价格数据: {len(has_price)} 条')
if has_price:
    print(f'样例: {json.dumps(has_price[0], ensure_ascii=False)[:200]}')

# 检查school_detail
with open('data/zheliban/school_detail.json', 'r', encoding='utf-8') as f:
    detail = json.load(f)
print(f'\n学校详情数据: {len(detail)} 条')
if detail:
    print(f'字段: {list(detail[0].keys())}')
