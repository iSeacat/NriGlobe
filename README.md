# NRI 跨境情报地球（NriGlobe）

把内容源（「每日新闻」Markdown 与「每日社媒吐槽日报」HTML）编译成一颗**自转的情报地球**：
新闻与产品痛点按发生国家打点在地球对应位置上，可以"只看今天"或"全部一起转"，可以点国家星点看该国明细，也可以按日期筛选。

参照 os-taxonomy-main 的工程约定：**内容源 → 构建校验 → data（前端只读） → index.html**，内容与前端解耦。

## 快速使用

```bash
# 1. 重新编译数据（新闻/社媒有更新后跑一次）
python scripts/build.py

# 2a. 直接双击 index.html 就能看（无 fetch，file:// 可用）
# 2b. 或起本地/局域网服务
python server.py 8731          # http://<本机IP>:8731/index.html
```

## 目录结构

```
content/                 ← 内容源（改这里）
  markets.json             国家/地区坐标、中英别名、全球核心市场、产品线默认市场
  countries-110m.json      world-atlas 原始地理数据（已内置，离线可重建）
data/                    ← 前端消费，禁止手改（由脚本生成）
  world.js                 极简陆地环数据（build_world.py 产出）
  dataset.js               情报条目（build.py 产出）
lib/three.min.js         ← 离线 three.js（来自 os-taxonomy-main）
scripts/build.py         ← 解析 每日新闻/*.md + 每日社媒/*.html → data/dataset.js
scripts/build_world.py   ← TopoJSON → 极简陆地数据
tools/make_debug.py      ← 生成无头验证调试页
index.html               ← 地球前端（three.js，无其它在线依赖）
```

## 配置（路径外置 / 自托管）

所有部署路径（新闻源、社媒源、发布目录）都**不写死在代码里**，通过以下顺序解析（后者覆盖前者）：
1. `config.local.json` —— 本机私有配置（已在 `.gitignore`，**不要提交**）；
2. 环境变量 `NRI_NEWS_DIR` / `NRI_SOCIAL_DIR` / `NRI_PUBLISH_DIR`；
3. 相对默认：`content/news`、`content/social`、`publish`。

仓库里给的是 `config.example.json`（相对路径示例）。本地部署时复制为 `config.local.json` 并填你自己的路径即可：

```bash
cp config.example.json config.local.json
# 编辑 config.local.json，填入你的新闻/社媒源目录与发布目录
```

## 运行示例数据（无需任何私有数据）

仓库自带一份**示例数据** `data/dataset.example.js`（纯演示，不含任何真实情报）。想本地预览地球：

```bash
cp data/dataset.example.js data/dataset.js   # index.html 默认读取 data/dataset.js
python server.py 8731                        # 打开 http://127.0.0.1:8731/index.html
```

也可以用自带示例源重新编译：

```bash
python scripts/build.py --news content/news --social content/social --out data/dataset.example.js
```

> 注：`data/dataset.js`（由 `build.py` 从你的私有源生成）在 `.gitignore` 中，不会被提交；每日真实情报请保留在私有环境。

## build.py 解析规则（要点）

- **新闻**：解析 `## 分节` + `N. **标题**` + `分类/摘要/来源` 行；国家优先取自「分类」行，再扫标题；无国家的归为"全球"，落到核心市场（美/欧/日/澳）并打"全球性"标记。
- **社媒痛点**：遍历所有表格，按列名关键词识别「痛点/类别、影响产品、国家/目标市场、严重度、证据、来源」；国家列缺失时从行文本猜，再退回报告级默认市场（🎯 行 → 三国行 → 全文词频 → 产品线默认市场）。
- **去重**：同类日报里"沿用"的痛点行按 `产品线+标题+摘要` 指纹合并，保留所有出现日期（`dates`），所以"今天/指定日期/全部"三种过滤都能命中。
- 别名匹配规则：中文别名 ≥2 字才做子串扫描，英文别名 ≥4 字符才扫描（避免 IT/IN/NO 这类误命中）；单字/短别名只做整词精确匹配。
- 校验失败（条目无市场、未知市场 id）时**不写文件**并逐条报错。

## 每日自动更新（07:00 中国时间）

自动化名：**NRI 情报地球 · 每日 07:00（中国时间）抓新闻+社媒+编译**（rrule `FREQ=DAILY;BYHOUR=17;BYMINUTE=0`，本机时区 UTC-6 → 中国时间次日 07:00）。

流程：闸口检查 → 抓新闻 → 抓社媒（示例产品线A/示例产品线B/示例产品线C）→ `build.py` 编译 → `sync_publish.py` 同步共享盘 → 简短汇报。

**免费窗口闸口**（`content/free_window.json`，改配置即可，不用改自动化）：

```json
{ "free_window": { "enabled": true, "start": "00:00", "end": "09:00" } }
```

```bash
python scripts/daily_check.py --wait    # 退出码 0=放行抓取；1=不在免费窗口/等待超时 → 停止抓取，不消耗付费额度
python scripts/sync_publish.py          # 同步 index.html + lib + data 到发布目录（config 指定）
```

停止条件（任一条触发立即收工、保留现状）：①不在免费窗口；②任何工具返回付费/额度用尽/限流提示；③同一产品线连续 2 次搜索 0 命中（省流量）。运行日志在 `logs/daily.log`。

## 视觉版本 v2（2026-09-15）

- 程序化地球贴图：海洋分层底色 + 海盆起伏 + 大陆架泛光 + 海岸线外发光 + 陆地纬度渐变与地形颗粒
- 程序化云层（value-noise fbm + 纬度云带），独立缓慢漂移，夜里变暗
- 海面镜面高光（specularMap：海面反光、陆地哑光）
- 太阳主光 + 背面冷补光，有昼夜明暗过渡；球面 fresnel 边缘光（向阳面更亮）
- 双层大气光晕 + 三层星空（呼吸闪烁、缓慢自转）+ 页面暗角
- 标记升级：雷达涟漪（表面扩散圆环）+ 数据光柱（高度随条目数）

## 已知边界

- 严重度/国家识别依赖日报写法，日报格式大改时需同步调整 `COL_PATTERNS`。
- 国家坐标是国家质心近似值，仅用于打点示意。
- 每日抓取量受 AI 模型 免费额度约束：新闻 8–15 条，社媒每条产品线最多 4 次搜索；若免费窗口调整，改 `content/free_window.json` 的 start/end。

## 无头验证

```bash
python tools/make_debug.py select:JP   # 自动选中日本
msedge --headless=new --use-gl=angle --use-angle=swiftshader \
  --window-size=1600,900 --virtual-time-budget=12000 \
  --screenshot=shot.png "file:///E:/Projects/NriGlobe/_debug.html"
```

调试页顶部绿条会显示 JS 错误列表和页面状态；`window.NRI_DEBUG` 暴露 select/refresh/state 供自动化驱动。
