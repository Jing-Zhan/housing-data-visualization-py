# 城市居住数据可视化与智能分析平台

基于开源项目「医疗数据可视化系统」扩展而来的二手房（城市居住数据）可视化平台。
系统沿用原有 13 个业务字段作为通用数据槽位，通过「领域配置 + 数据源适配器」切换题材，
不改变数据库结构与前端图表结构。

- 领域：二手房在售与成交数据（可切换到医疗、二手车等其它领域）
- 形态：Flask 后端 + Vue 2 大屏前端 + MySQL 存储
- 当前阶段：需求规格说明书完成，进入设计阶段；模块分工在需求评审后确定

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.10+ / Flask / PyMySQL / Pandas |
| 存储 | MySQL 8.0（`cases` 事实表 + 4 张辅助表） |
| 前端 | Vue 2 / Vue Router / ECharts / DataV |
| 智能 | BERT 中文文本分类（PyTorch + Transformers）/ DeepSeek 对话 |
| 实时 | APScheduler 定时采集 + Flask-SocketIO 推送 |

## 目录结构

```text
housing-data-visualization-py/
├─ backend/
│  ├─ app.py                  # 应用入口：create_app + 蓝图注册
│  ├─ config.py               # 配置读取（.env）
│  ├─ domain/                 # 领域配置层
│  │  ├─ profile.py           #   领域配置加载与读取
│  │  └─ profiles/            #   house.yaml / medical.yaml
│  ├─ adapters/               # 数据源适配层（适配器模式）
│  │  ├─ base.py              #   抽象接口 DataSourceAdapter
│  │  ├─ mock_adapter.py      #   演示用增量数据
│  │  ├─ csv_adapter.py       #   离线 CSV / Excel
│  │  ├─ crawler_adapter.py   #   链家 / 贝壳采集（待实现）
│  │  ├─ api_adapter.py       #   开放数据 API（待实现）
│  │  └─ registry.py          #   适配器工厂
│  ├─ blueprints/             # 接口层
│  │  ├─ dashboard.py         #   大屏聚合接口
│  │  ├─ data.py              #   数据管理接口
│  │  ├─ ai.py                #   预测与对话接口
│  │  └─ domain.py            #   领域配置接口
│  ├─ services/               # 应用服务层
│  │  ├─ kpi_service.py       #   指标计算
│  │  └─ chart_service.py     #   图表数据组装
│  ├─ repo/                   # 仓储层（SQL 收敛于此）
│  ├─ models/schema.sql       # 建表脚本
│  └─ legacy/                 # 原医疗系统实现（对照与回归）
├─ frontend/                  # Vue 2 大屏前端（沿用原工程）
├─ docs/                      # 需求、UML、分工与设计文档
├─ scripts/                   # 初始化与导入脚本
├─ tests/                     # 单元测试
└─ .github/                   # Issue / PR 模板与 CI
```

## 分支策略

| 分支 | 用途 | 规则 |
|---|---|---|
| `main` | 可演示、可交付的稳定版本 | 只接受来自 `develop` 的合并，不直接提交 |
| `develop` | 集成分支，功能汇合处 | 功能分支合并到这里，保持可运行 |
| `feature/<模块>-<简述>` | 单人功能开发 | 从 `develop` 切出，完成后向 `develop` 提 PR |
| `fix/<简述>` | 缺陷修复 | 从 `main` 或 `develop` 切出，修复后提 PR |
| `docs/<简述>` | 文档与图集 | 从 `develop` 切出，合并到 `develop` |

```text
main ───●────────────────●───────────────▶
          ╲              ╱
develop    ●───●───●────●───●───●────────▶
                ╲ ╱      ╲ ╱
feature/x        ●        ●
```

约定：

1. 每个功能分支只改自己负责的模块目录，避免跨模块冲突。
2. 提交信息使用 `feat: / fix: / docs: / refactor: / test: / chore:` 前缀。
3. 合并前在本地执行 `pytest -q`，CI 通过后再合并。
4. `develop` 合并到 `main` 由组长操作，合并后打标签（`v0.1`、`v0.2`…）。

## 本地启动

### 1. 后端（框架版，无需数据库即可演示）

```bash
pip install -r requirements.txt
copy .env.example .env
python -m backend.app
# 访问 http://127.0.0.1:5000/api/health
```

默认 `DATA_SOURCE=mock`，接口用领域配置生成演示数据，便于前端联调。

### 2. 数据库与离线数据

```bash
mysql -u root -p < backend/models/schema.sql
python scripts/init_db.py
python scripts/import_csv.py --file data/sample_house.csv
```

### 3. 前端

```bash
cd frontend
npm install
npm run serve
```

### 4. 原医疗系统（对照）

```bash
cd backend/legacy
python app.py
python websocket_chat.py   # 对话服务，端口 5001
```

## 配置项

| 变量 | 说明 | 示例 |
|---|---|---|
| `DOMAIN` | 领域配置名，对应 `backend/domain/profiles/*.yaml` | `house` |
| `DATA_SOURCE` | 数据源类型：`mock` / `csv` / `crawler` / `api` | `mock` |
| `MOCK_ROWS` | 演示数据条数 | `300` |
| `DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASSWORD` / `DB_NAME` | MySQL 连接信息 | `127.0.0.1` / `3306` |
| `DEEPSEEK_API_KEY` | 对话服务密钥 | `sk-...` |
| `FLASK_SECRET_KEY` | Flask 会话密钥 | 随机字符串 |

## 13 个字段槽位

| 槽位 | 医疗（原） | 二手房（现） |
|---|---|---|
| `type` | 疾病类型 | 户型 |
| `gender` | 性别 | 装修 |
| `age` | 年龄 | 房龄（年） |
| `time` | 就诊时间 | 挂牌日期 |
| `content` | 病情描述 | 标题与房源描述 |
| `docName` | 医生 | 经纪人 |
| `docHospital` | 医院 | 小区 |
| `department` | 科室 | 区域（区县） |
| `detailUrl` | 详情链接 | 房源链接 |
| `height` | 身高 | 建筑面积（㎡） |
| `weight` | 体重 | 挂牌总价（万） |
| `illDuration` | 病程 | 楼层 |
| `allergy` | 过敏史 | 朝向与权属 |

## 文档索引

| 文档 | 说明 |
|---|---|
| `docs/01-需求规格说明书.md` | 需求规格说明书 V1.0（含 AI 对话与 Agent 需求） |
| `docs/01-需求规格说明书.docx` | 同上，Word 版（宋体小四、1.1 倍行距） |
| `docs/02-UML/` | 用例图、类图、时序图、状态图、部署图（设计阶段产出） |

模块分工在需求评审后确定，任务拆解与负责人登记为仓库 Issue。

## 数据来源

- 链家二手房：<https://sh.lianjia.com/ershoufang/>
- 贝壳二手房：<https://cs.ke.com/ershoufang/>
- 公开离线集：<https://www.kaggle.com/datasets/ruiqurm/lianjia>
- 官方开放数据：<https://opendata.sz.gov.cn/>

采集遵守站点规则：单页间隔不少于 5 秒、轮换 User-Agent、仅采集列表页公开字段。

## 许可

仅用于课程教学与学习，数据版权归原平台所有。
