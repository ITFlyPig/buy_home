import json, re

with open('/Users/yanxi/Downloads/0绿城/kiro-data/data-warehouse/杭州买房指南/visualization/data/school_data.js', 'r', encoding='utf-8') as f:
    content = f.read()

match = re.search(r'export const schools = (\[.*\]);', content, re.DOTALL)
schools = json.loads(match.group(1))

types = {}
natures = {}
districts = {}
for s in schools:
    t = s.get('school_type', '')
    n = s.get('school_nature', '')
    d = s.get('district', '')
    types[t] = types.get(t, 0) + 1
    natures[n] = natures.get(n, 0) + 1
    districts[d] = districts.get(d, 0) + 1

print('school_type:', types)
print('school_nature:', natures)
print('district:', districts)
print('total:', len(schools))
print('sample:', json.dumps(schools[0], ensure_ascii=False, indent=2))
