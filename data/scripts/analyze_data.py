"""分析爬取的学校数据，生成前端可用的小学→初中映射"""
import json
from collections import Counter

with open('/Users/yanxi/Downloads/0绿城/kiro-data/data-warehouse/杭州买房指南/data/raw/rxyj_all_schools.json') as f:
    schools = json.load(f)

with open('/Users/yanxi/Downloads/0绿城/kiro-data/data-warehouse/杭州买房指南/data/raw/rxyj_all_mappings.json') as f:
    mappings = json.load(f)

# 分类
primary = [s for s in schools if s['school_type'] == '小学']
middle = [s for s in schools if s['school_type'] in ('初中', '九年一贯制')]

print(f"小学: {len(primary)} 所")
print(f"初中/九年一贯制: {len(middle)} 所")

# 有对口初中的小学
has_middle = [s for s in primary if s.get('direct_middle_school')]
print(f"有对口初中的小学: {len(has_middle)} 所")

# 按区域统计
areas = Counter(s['district'] for s in primary)
print("\n按区域:")
for area, cnt in areas.most_common():
    middle_cnt = len([s for s in middle if s['district'] == area])
    print(f"  {area}: 小学{cnt}所, 初中{middle_cnt}所")

# 样例
print("\n--- 样例 ---")
for s in primary[:5]:
    comm_count = len(s.get('communities_hj', [])) + len(s.get('communities_xhzr', []))
    print(f"  {s['school_name']} | {s['district']} | 对口初中: {s.get('direct_middle_school','')} | 小区: {comm_count}个")

# 检查对口初中名称是否在中学列表中
middle_names = set(s['school_name'] for s in middle)
print(f"\n中学名称集合大小: {len(middle_names)}")

# 检查小学的对口初中是否匹配
matched = 0
unmatched_examples = []
for s in has_middle:
    dm = s['direct_middle_school']
    if dm in middle_names:
        matched += 1
    else:
        if len(unmatched_examples) < 5:
            unmatched_examples.append(f"  {s['school_name']} -> {dm}")

print(f"对口初中匹配: {matched}/{len(has_middle)}")
if unmatched_examples:
    print("未匹配样例:")
    for e in unmatched_examples:
        print(e)
