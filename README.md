# 杭州买房指南 - 数据可视化决策平台

## 项目概述

基于数据分析的杭州购房决策辅助平台，通过前端可视化页面展示各区域房价、学区、配套等多维度信息，帮助购房者做出理性决策。

---

## 访问链接

| 页面 | 地址 | 说明 |
|------|------|------|
| **🌐 公网访问** | https://certificate-gale-likelihood-actually.trycloudflare.com | 外网可直接访问（Cloudflare 隧道，HTTPS） |
| **主页面** | http://localhost:8767/index.html | 本地访问，完整功能页面，包含学区、房价、中考成绩等 |
| **备用端口** | http://localhost:9999/index.html | 使用 server_new.py 启动 |
| **简化版** | http://localhost:8767/index_simple.html | 简化页面 |

> **公网访问说明**：由于服务器所在网络封禁了入站端口，使用 Cloudflare Tunnel 进行内网穿透实现外网访问。需保持 `cloudflared` 进程运行，进程中断后链接失效。

---

## 快速开始

### 启动本地服务器

```bash
# 方式一：使用默认端口 8767
cd visualization
python3 server.py

# 方式二：使用备用端口 9999
cd visualization
python3 server_new.py

# 方式三：使用 Python 内置服务器
cd visualization
python3 -m http.server 8767
```

启动后访问：http://localhost:8767/index.html

### 启动公网穿透（外网访问）

本地服务启动后，运行以下命令开启 Cloudflare 隧道，即可通过公网地址访问：

```bash
# 安装 cloudflared（首次使用）
brew install cloudflared

# 启动隧道，映射本地 8767 端口
no_proxy='*' cloudflared tunnel --url http://localhost:8767
```

启动后终端会输出公网访问地址，外网用户即可通过该地址访问页面。

---

## 项目结构

```
杭州买房指南/
├── README.md                    # 项目说明（本文件）
├── docs/                        # 文档
│   ├── 数据源说明.md            # 数据来源与采集方案
│   ├── 板块分析.md              # 各板块分析报告
│   ├── 购房政策.md              # 最新限购政策整理
│   └── 需求分析.md              # 需求与功能规划
├── data/                        # 数据层
│   ├── zheliban/                # 【浙里办数据专目录】
│   │   ├── rxyj_all_schools.json      # 学校基础信息（JSON）
│   │   ├── rxyj_all_schools.csv       # 学校基础信息（CSV）
│   │   ├── rxyj_all_mappings.json     # 学校-小区映射（JSON）
│   │   ├── rxyj_all_mappings.csv      # 学校-小区映射（CSV）
│   │   ├── school_communities.csv     # 学区小区列表
│   │   ├── school_district_mapping.json   # 学区划分映射
│   │   ├── school_district_mapping.csv    # 学区划分映射（CSV）
│   │   └── school_detail.json         # 学校详细信息
│   ├── raw/                     # 原始数据（与 zheliban 目录同步）
│   ├── processed/               # 清洗后数据
│   │   ├── community_prices.json      # 小区价格数据
│   │   └── crawl_summary.json         # 采集汇总信息
│   └── scripts/                 # 数据处理脚本
│       ├── crawl_community_prices.py  # 小区价格采集
│       ├── build_frontend_data.py     # 构建前端数据
│       ├── build_community_prices.py  # 构建价格数据
│       └── analyze_data.py            # 数据分析
└── visualization/               # 可视化页面
    ├── index.html               # 主页面
    ├── index_simple.html        # 简化页面
    ├── server.py                # 本地服务器（端口 8767）
    ├── server_new.py            # 本地服务器（端口 9999）
    ├── components/              # Vue 组件
    └── data/                    # 前端数据文件
        ├── school_data.js       # 学校数据
        ├── community_prices.js  # 小区价格数据
        ├── price_data.js        # 价格分析数据
        └── primary_data.js      # 小学数据
```

---

## 核心功能模块

### 1. 学区查询
- 小学/初中分类筛选
- 公办/民办/民转公筛选
- 按区域筛选（西湖区、上城区等）
- 学校详细信息查看
- 对口小区列表及房价展示

### 2. 房价对比
- 小区均价展示
- 总价范围筛选
- 户型信息展示
- 学区小区关联

### 3. 中考成绩
- 重点中学中考成绩展示
- 升学率统计
- 学校详情补充

### 4. 数据采集工具
- 浙里办学区数据采集
- 贝壳小区价格自动采集
- 支持断点续爬
- 双接口重试机制

---

## 数据采集

### 小区价格采集

```bash
# 全量采集（约 9700+ 个小区）
python3 data/scripts/crawl_community_prices.py

# 按区域采集
python3 data/scripts/crawl_community_prices.py --district 西湖区
python3 data/scripts/crawl_community_prices.py --district 上城区

# 限制采集数量（测试用）
python3 data/scripts/crawl_community_prices.py --limit 50
```

### 数据更新

```bash
# 更新前端数据文件
python3 data/scripts/build_frontend_data.py
python3 data/scripts/build_community_prices.py
```

### 数据库存储

项目支持将数据存储到本地 SQLite 数据库，便于数据管理和历史追溯。

**数据库位置**: `data/hangzhou_home.db`

**数据库表结构**:

| 表名 | 用途 | 记录数 |
|------|------|--------|
| `schools` | 学校信息（小学、初中、九年一贯制） | 452 所 |
| `communities` | 小区信息 | 9712 个 |
| `school_community_mapping` | 学区映射关系 | 17082 条 |
| `community_prices` | 小区价格（支持历史记录） | 9712 条 |
| `community_transactions` | 小区成交记录 | 预留 |
| `crawl_tasks` | 采集任务状态追踪 | 预留 |

**数据迁移（首次使用）**:

```bash
# 初始化数据库并迁移现有数据
python3 data/scripts/migrate_to_db.py
```

### 定时更新（自动调度）

项目支持每天定时自动更新数据，采用分层更新策略：

| 数据类型 | 更新频率 | 时间 | 说明 |
|----------|----------|------|------|
| 学校学区数据 | 每周一 | 凌晨3:00 | rxyj API全量更新，约5分钟 |
| 小区价格数据 | 每天 | 凌晨4:00 | 按区轮询，每天更新1-2个区，7天覆盖全部 |
| 前端数据构建 | 每天 | 凌晨6:00 | 重建所有前端JS文件 |

**区域轮询计划**:

| 星期 | 更新区域 |
|------|----------|
| 周一 | 西湖区、上城区 |
| 周二 | 拱墅区、滨江区 |
| 周三 | 钱塘区、余杭区 |
| 周四 | 临平区、临安区 |
| 周五 | 桐庐县、淳安县 |
| 周六 | 建德市 |
| 周日 | 西湖区（重点区域） |

**使用方法**:

```bash
# 启动定时调度器（后台运行）
python3 data/scripts/scheduler.py

# 立即执行一次所有任务
python3 data/scripts/scheduler.py --run-now
```

**查看执行状态**:

```bash
# 实时查看日志
tail -f data/scheduler.log

# 查看最后执行结果
tail -20 data/scheduler.log
```

---

## 数据文件说明

所有数据文件统一存放在 `data/processed/` 目录，原始数据保存在 `data/raw/`。CSV 文件使用 UTF-8-BOM 编码，可直接用 Excel 打开。

> 数据更新后请同步修改本章节的记录数与更新日期。

| 文件 | 格式 | 记录数 | 更新日期 | 内容说明 |
|------|------|--------|----------|----------|
| rxyj_all_schools.csv | CSV | 493 | 2026-06-30 | 学校基础信息总表（小学+初中），含学校名称、校区、区县、学校类型、地址、经纬度、电话、学生/班级/教师数、学区范围、对口初中、学校介绍、户籍生/新杭州人对口小区 |
| rxyj_all_mappings.csv | CSV | 17742 | 2026-06-30 | 学校-小区对口映射表，每行一个学校×小区×学生类型记录，已关联补充 school_type/address/lng/lat 等字段 |
| school_district_mapping.csv | CSV | 93 | 2026-06-30 | 精选学区房映射表，含学校等级、板块、服务小区、重点小区、均价区间、招生年份、备注 |
| school_detail.csv | CSV | 493 | 2026-06-30 | 学校详情表，字段与 rxyj_all_schools.csv 一致，定位为详情扩展表 |

### 字段速查（rxyj_all_schools.csv）

| 字段 | 类型 | 说明 |
|------|------|------|
| school_name | STRING | 学校名称 |
| campus_name | STRING | 校区名称 |
| school_code | STRING | 学校编码 |
| campus_code | STRING | 校区编码 |
| district | STRING | 所属区县（上城区/西湖区等） |
| district_code | STRING | 区县编码 |
| school_type | STRING | 学校类型（小学/初中） |
| school_nature | STRING | 办学性质（非民办/民办） |
| address | STRING | 学校地址 |
| lng | STRING | 经度 |
| lat | STRING | 纬度 |
| school_tel | STRING | 联系电话 |
| student_count | INT | 学生总数 |
| class_count | INT | 班级总数 |
| teacher_count | INT | 教师总数 |
| school_scope | STRING | 学区范围描述 |
| direct_middle_school | STRING | 对口初中 |
| school_detail | STRING | 学校详细介绍 |
| communities_hj | STRING | 户籍生对口小区（分号分隔） |
| communities_xhzr | STRING | 新杭州人对口小区（分号分隔） |
| community_count | INT | 对口小区总数 |
| year | STRING | 数据年份 |
| visit_times | INT | 浙里办页面访问量 |

### 数据重新生成

源数据更新后，执行以下脚本可重新生成全部 CSV 文件：

```bash
python3 data/scripts/export_csv.py
```

脚本会读取 `data/raw/` 下的 JSON，输出到 `data/processed/`。生成后请同步更新本章节的记录数与更新日期。

---

## 技术方案

| 层级 | 技术选型 | 说明 |
|------|----------|------|
| 前端可视化 | Vue 3 + g-ui-web | 驾驶舱风格页面 |
| 地图展示 | 高德地图 API | 区域划分、POI标注 |
| 数据存储 | SQLite + JSON/CSV | 本地数据库存储，支持历史追溯 |
| 数据采集 | Python + requests | 浙里办、贝壳等 |
| 定时调度 | Python 内置模块 | 分层更新策略，无需外部依赖 |
| 本地服务器 | Python http.server | 带缓存控制 |

---

## 数据统计

> 以下数据基于 `rxyj_all_schools.csv`（493所），更新日期 2026-06-30。

- **学校总数**: 493 所
- **小学**: 440 所
- **初中/九年一贯制**: 53 所
- **有对口初中的小学**: 315 所
- **学区小区**: 9712 个（已采集价格）

---

## 注意事项

1. **网络环境**：沙箱环境下无法直接访问外部网站，小区价格采集需在本地终端运行
2. **代理配置**：运行爬虫前请确保清理代理环境变量
   ```bash
   unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy
   ```
3. **Python环境**：建议使用 `python3 -m pip install requests --break-system-packages` 安装依赖
4. **数据更新**：学区数据每年6月更新，房价数据建议定期重新采集

---

## 相关文档

- [数据源说明](docs/数据源说明.md) - 详细数据来源与采集方案
- [板块分析](docs/板块分析.md) - 杭州各板块深度分析
- [购房政策](docs/购房政策.md) - 最新限购政策整理