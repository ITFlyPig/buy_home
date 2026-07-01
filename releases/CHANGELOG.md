# 版本发布记录

> 杭州买房指南 - 数据可视化决策平台
> 本文件记录每个发布版本的变更内容，便于版本追溯与回滚恢复。

---

## 版本恢复指引

如需恢复到某个历史版本，在仓库根目录执行：

```bash
# 查看所有版本
git log --oneline -- 杭州买房指南/

# 恢复指定版本的某个文件（示例）
git checkout <commit-hash> -- 杭州买房指南/visualization/index_xq.html

# 恢复指定版本的全部文件
git checkout <commit-hash> -- 杭州买房指南/
```

---

## v1.2.0 | 2026-06-30

**说明：** 学校学区数据CSV化并完善字段

### 变更内容

| 类型 | 文件 | 说明 |
|------|------|------|
| 新增 | `data/scripts/export_csv.py` | CSV 导出脚本，从 raw JSON 生成全量 CSV |
| 新增 | `data/processed/school_detail.csv` | 学校详情表（493所，22字段） |
| 更新 | `data/processed/rxyj_all_schools.csv` | 补充 communities_hj/communities_xhzr/community_count 字段 |
| 更新 | `data/processed/rxyj_all_mappings.csv` | 关联补充 school_type/school_nature/address/lng/lat 等9个字段 |
| 更新 | `data/processed/school_district_mapping.csv` | 关联补充 school_type/school_nature 字段 |
| 更新 | `README.md` | 新增「数据文件说明」章节（含字段速查表），更新数据统计 |
| 新增 | `visualization/community_trend.html` | 小区价格趋势页面 |

### 数据文件清单

| 文件 | 记录数 | 说明 |
|------|--------|------|
| rxyj_all_schools.csv | 493 | 学校基础信息总表 |
| rxyj_all_mappings.csv | 17742 | 学校-小区对口映射 |
| school_district_mapping.csv | 93 | 精选学区房映射 |
| school_detail.csv | 493 | 学校详情表 |

### 数据重新生成

```bash
python3 data/scripts/export_csv.py
```

---

## v1.1.0 | 2026-06-30

**提交：** `b3fcb5c`
**说明：** 恢复学区查询页面并修复区域统计 Bug

### 变更内容

| 类型 | 文件 | 说明 |
|------|------|------|
| 新增 | `visualization/index_xq.html` | 从 git 历史恢复被误删的学区查询页面（1302 行） |
| 修复 | `visualization/index_xq.html` | 修复区域数据概览中学类型统计的 JS 错误 |
| 新增 | `releases/CHANGELOG.md` | 新建发布目录与变更记录 |

### 修复详情

**问题：** 首页"区域数据概览"表格统计初中/小学数量时报错，导致 `init()` 中断，学校列表无法渲染。

```js
// 修改前（报错：Cannot use 'in' operator to search for '九年' in 小学）
if (s.school_type === '初中' || '九年' in (s.school_type || '')) districtStats[d].middle++;

// 修改后
if (s.school_type === '初中' || (s.school_type || '').includes('九年')) districtStats[d].middle++;
```

**原因：** JavaScript 的 `in` 操作符用于检查对象属性键，右操作数为字符串时会抛 `TypeError`。应使用 `String.prototype.includes()` 判断字符串包含关系。

### 本地访问

```bash
cd visualization
python3 -m http.server 8765
```

- http://localhost:8765/index.html
- http://localhost:8765/index_simple.html
- http://localhost:8765/index_xq.html

---

## v1.0.0 | 2026-06-30

**提交：** `8751cdb`
**说明：** 初始版本：杭州买房指南数据可视化平台

### 变更内容

- 搭建项目基础结构（docs / data / visualization 三大模块）
- 实现学区查询、房价对比、中考成绩等可视化页面
- 完成浙里办 440 所小学 + 53 所初中数据采集
- 采集 9712 个学区小区价格数据
- 提供数据采集与处理脚本工具集

### 后续维护提交

| 提交 | 说明 |
|------|------|
| `d3a1cb4` | 文档：添加版本发布流程文档（注：此提交误删 index_xq.html，已在 v1.1.0 恢复） |
