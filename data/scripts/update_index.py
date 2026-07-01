"""
更新 /Users/yanxi/Downloads/杭州买房指南/index.html 的小学导航页
1. 注入爬取的 493 所学校数据
2. 增加办学性质(公办/民办) + 学校类型(小学/初中) 筛选
3. 点击学校行可展开查看完整信息（对口小区、地址、规模等）
"""
import json
from pathlib import Path

# 1. 读取爬取数据
with open('/Users/yanxi/Downloads/0绿城/kiro-data/data-warehouse/杭州买房指南/data/raw/rxyj_all_schools.json') as f:
    schools = json.load(f)

# 构建前端数据
all_schools = []
for s in schools:
    if s['school_type'] in ('小学', '初中', '九年一贯制'):
        all_schools.append({
            'name': s['school_name'],
            'district': s['district'],
            'type': s['school_type'],
            'nature': s['school_nature'],
            'address': s.get('address', ''),
            'middle': s.get('direct_middle_school', ''),
            'communities_hj': s.get('communities_hj', []),
            'communities_xhzr': s.get('communities_xhzr', []),
            'community_count': s.get('community_count', 0),
            'student_count': s.get('student_count', 0),
            'class_count': s.get('class_count', 0),
            'teacher_count': s.get('teacher_count', 0),
            'school_scope': s.get('school_scope', ''),
            'school_detail': s.get('school_detail', ''),
            'tel': s.get('school_tel', ''),
        })

districts = sorted(set(s['district'] for s in all_schools))
data_js = f"const rxyjSchools = {json.dumps(all_schools, ensure_ascii=False, separators=(',',':'))};\nconst rxyjDistricts = {json.dumps(districts, ensure_ascii=False)};"

print(f"数据: {len(all_schools)} 所学校, {len(districts)} 个区域")
print(f"JS 大小: {len(data_js)/1024:.0f} KB")

# 2. 读取目标 HTML
target_path = Path('/Users/yanxi/Downloads/杭州买房指南/index.html')
with open(target_path, 'r', encoding='utf-8') as f:
    html = f.read()

# 3. 替换小学导航页 HTML
old_primary_html = """    <!-- ========== 小学导航页 ========== -->
    <div class="page" id="page-primary">
        <div class="hero" style="padding:24px 30px;">
            <h1 style="font-size:24px;">小学对口初中导航</h1>
            <p>从小学查初中：选择小学，查看对口初中及中考成绩 | 公办按学区对口直升</p>
        </div>

        <div class="toolbar">
            <select id="primAreaFilter" onchange="renderPrimaryTable()">
                <option value="">全部区域</option>
                <option value="滨江区">滨江区</option><option value="拱墅区">拱墅区</option>
                <option value="西湖区">西湖区</option><option value="上城区">上城区</option>
                <option value="钱塘区">钱塘区</option>
            </select>
            <input type="text" id="primSearch" placeholder="搜索小学名称..." oninput="renderPrimaryTable()" style="width:240px">
        </div>

        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>区域</th><th>小学名称</th><th>对口初中</th><th>初中性质</th>
                        <th>前十三率</th><th>优高率</th><th>前三裸考</th>
                        <th>入学方式</th><th>学区最低门槛</th><th>操作</th>
                    </tr>
                </thead>
                <tbody id="primaryTableBody"></tbody>
            </table>
        </div>
    </div>"""

new_primary_html = """    <!-- ========== 学校导航页 ========== -->
    <div class="page" id="page-primary">
        <div class="hero" style="padding:24px 30px;">
            <h1 style="font-size:24px;">学校导航（浙里办数据）</h1>
            <p>数据来源：浙里办「入学早知道」2026年 | 共<span id="rxyjCount">-</span>所学校 | 点击学校行展开查看完整信息</p>
        </div>

        <div class="toolbar">
            <select id="primAreaFilter" onchange="renderPrimaryTable()">
                <option value="">全部区域</option>
            </select>
            <select id="primTypeFilter" onchange="renderPrimaryTable()">
                <option value="">全部类型</option>
                <option value="小学">小学</option>
                <option value="初中">初中</option>
                <option value="九年一贯制">九年一贯制</option>
            </select>
            <select id="primNatureFilter" onchange="renderPrimaryTable()">
                <option value="">全部性质</option>
                <option value="非民办">公办</option>
                <option value="民办">民办</option>
            </select>
            <input type="text" id="primSearch" placeholder="搜索学校或小区名称..." oninput="renderPrimaryTable()" style="width:260px">
            <span style="margin-left:auto;font-size:13px;color:#888;" id="primResultCount"></span>
        </div>

        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th style="width:30px"></th>
                        <th>区域</th><th>学校名称</th><th>类型</th><th>性质</th>
                        <th>对口初中</th><th>对口小区数</th><th>规模</th>
                    </tr>
                </thead>
                <tbody id="primaryTableBody"></tbody>
            </table>
        </div>
    </div>"""

html = html.replace(old_primary_html, new_primary_html)

# 4. 替换 renderPrimaryTable 函数
old_func_start = "// ========== 小学导航页 ==========\nfunction renderPrimaryTable() {"
old_func_end = "\n}\n\n// ========== 初始化 =========="

# 找到函数位置
idx_start = html.find(old_func_start)
idx_end = html.find(old_func_end)

if idx_start < 0 or idx_end < 0:
    print("[ERROR] 找不到 renderPrimaryTable 函数")
    exit(1)

new_func = """// ========== 学校导航页 ==========
function renderPrimaryTable() {
    const area = document.getElementById('primAreaFilter').value;
    const type = document.getElementById('primTypeFilter').value;
    const nature = document.getElementById('primNatureFilter').value;
    const search = document.getElementById('primSearch').value.toLowerCase();

    let filtered = rxyjSchools.filter(s => {
        if (area && s.district !== area) return false;
        if (type && s.type !== type) return false;
        if (nature && s.nature !== nature) return false;
        if (search) {
            const inName = s.name.toLowerCase().includes(search);
            const inMiddle = s.middle.toLowerCase().includes(search);
            const inComm = s.communities_hj.some(c => c.toLowerCase().includes(search));
            if (!inName && !inMiddle && !inComm) return false;
        }
        return true;
    });

    document.getElementById('primResultCount').textContent = '共 ' + filtered.length + ' 所学校';
    const tbody = document.getElementById('primaryTableBody');

    tbody.innerHTML = filtered.map((s, i) => {
        const areaClass = areaColors[s.district] || '';
        const typeBadge = s.type === '小学' ? 'badge-public' : s.type === '初中' ? 'badge-private' : 'badge-transfer';
        const natureText = s.nature === '非民办' ? '公办' : '民办';
        const natureBadge = s.nature === '非民办' ? 'badge-public' : 'badge-private';
        const scale = s.student_count > 0 ? s.student_count + '学生/' + s.class_count + '班' : '-';
        const commCount = s.community_count > 0 ? s.community_count + '个' : '-';

        // 展开行内容
        const hjComm = s.communities_hj.length > 0
            ? s.communities_hj.map(c => '<span class="tag tag-primary">' + c + '</span>').join('')
            : '<span style="color:#999">无</span>';
        const xhzrComm = s.communities_xhzr.length > 0
            ? s.communities_xhzr.map(c => '<span class="tag">' + c + '</span>').join('')
            : '';
        const detailRow = '<div class="detail-row" style="display:none" id="detail-' + i + '">' +
            '<div style="padding:16px 20px;background:#fafafa;border-top:2px solid #e8e8e8">' +
            '<div class="section-title">学校地址</div><div style="margin-bottom:12px;font-size:13px">' + (s.address || '暂无') + '</div>' +
            (s.tel ? '<div class="section-title">联系电话</div><div style="margin-bottom:12px;font-size:13px">' + s.tel + '</div>' : '') +
            (s.school_detail ? '<div class="section-title">学校简介</div><div style="margin-bottom:12px;font-size:13px;line-height:1.8;color:#666">' + s.school_detail + '</div>' : '') +
            (s.school_scope ? '<div class="section-title">学区范围</div><div style="margin-bottom:12px;font-size:13px;line-height:1.8;color:#666;white-space:pre-wrap">' + s.school_scope + '</div>' : '') +
            (s.teacher_count > 0 ? '<div class="section-title">师资规模</div><div style="margin-bottom:12px;font-size:13px">学生' + s.student_count + '人 / 班级' + s.class_count + '个 / 教师' + s.teacher_count + '人</div>' : '') +
            '<div class="section-title">户籍生对口小区（' + s.communities_hj.length + '个）</div><div class="tag-list" style="margin-bottom:12px">' + hjComm + '</div>' +
            (xhzrComm ? '<div class="section-title">新杭州人对口小区（' + s.communities_xhzr.length + '个）</div><div class="tag-list">' + xhzrComm + '</div>' : '') +
            '</div></div>';

        return '<tr onclick="toggleDetail(' + i + ')" style="cursor:pointer">' +
            '<td style="text-align:center;color:#999">&#9654;</td>' +
            '<td><span class="' + areaClass + '" style="font-weight:600">' + s.district + '</span></td>' +
            '<td style="text-align:left;font-weight:600">' + s.name + '</td>' +
            '<td><span class="badge ' + typeBadge + '">' + s.type + '</span></td>' +
            '<td><span class="badge ' + natureBadge + '">' + natureText + '</span></td>' +
            '<td style="text-align:left">' + (s.middle || '<span style="color:#999">-</span>') + '</td>' +
            '<td>' + commCount + '</td>' +
            '<td style="font-size:12px;color:#888">' + scale + '</td>' +
            '</tr><tr><td colspan="8" style="padding:0">' + detailRow + '</tr>';
    }).join('');

    document.getElementById('rxyjCount').textContent = rxyjSchools.length;
}

function toggleDetail(idx) {
    const row = document.getElementById('detail-' + idx);
    if (row) {
        const display = row.style.display === 'none' ? 'block' : 'none';
        row.style.display = display;
        // 更新箭头
        const arrow = row.closest('tr').previousElementSibling.querySelector('td:first-child');
        if (arrow) arrow.innerHTML = display === 'block' ? '&#9660;' : '&#9654;';
    }
}"""

html = html[:idx_start] + new_func + html[idx_end + len(old_func_end):]

# 5. 在 <script> 标签后注入爬取数据
script_tag = "<script>\n// ========== 完整数据 =========="
injected_data = "<script>\n" + data_js + "\n\n// ========== 完整数据 =========="
html = html.replace(script_tag, injected_data, 1)

# 6. 保存
with open(target_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"\n[OK] 已更新: {target_path}")
print(f"  文件大小: {target_path.stat().st_size / 1024:.0f} KB")
