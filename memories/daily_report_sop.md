# 非传统安全领域动态日报 SOP v3.2

> 触发生成日报时先读此文件。整合 v1.5/v1.6/v1.8 + v3.2 可靠性修复全部执行踩坑经验。
> **v3.1 核心变更**: 适配 v1.8 指令 — 5板块结构 + E.4(14项) + E.5(12项排版) 自检。
> **v3.2 可靠性变更**: H1 24h 窗口下沉到 `daily_report_render.enforce_window()` 代码层强制; Phase 2.3b 强制扁平 schema (删除旧 `sections[]` 嵌套); Phase 7 输出路径强制 `temp/output/daily_<YYYYMMDD>/` (D-4 白名单)
> 详见: `docs/specs/2026-06-20-daily-report-reliability-design.md`
>
> **三件套渲染器**: `daily_report_render.py` — MD/DOCX/HTML 全量硬编码(F.1-F.5) + enforce_window 窗口守门员 + _check_output_dir 路径白名单
> **交付自检**: `daily_report_validate.py` — E.4 内容14项 (E.4-07 严格 24h) + E.5 排版12项 | CLI: `validate.py <report_data.json> [--docx docx路径] [--strict]`
>
> **v3.3 经验 (R19 0825 实战)**: validator E.4-08 强制双源 lead body 含 `X月X日，X（Y）报道：` 前缀; render 会自动剥掉重建防重复。
> **v3.4 经验 (R22 0826 实战, 18/18 PASS)**:
> 1. **body 字数 180< ≤220** (非 150-200) — E.4-15 校验
> 2. **S1 涉华要闻 3-5 条** (非 6-10) — E.4-03 校验
> 3. **trends 三段每段 200-300, 总 600-900** — E.4-16 校验
> 4. **段首动词白名单仅 4 词: 报道/表示/声明/发布** — E.4-08 校验; "宣布""宣称""指出""披露" 一律 FAIL。0826 S2#4 Hemerdon "宣布投入7100万" → "发布声明，将投入7100万" 即过
> 5. **S1 必须 pub_date 倒序** — E.4-11 校验
> **v3.6 经验 (R23 0826 实战, cwd 嵌套根因)**:
> 1. **D-4 白名单只看字符串前缀, 易被 cwd 绕开**: 即使 `--output-dir temp/output/daily_<YYYYMMDD>` 字符串过白名单, 若调用方 cwd 已在 `temp/` 内部, os.makedirs 解析为 `<cwd>/temp/output/...` 即 `temp/temp/output/...` 嵌套 (0826 11:25 真实发生)。
> 2. **修复**: `_check_output_dir` 已加 abspath 解析 + `/temp/temp/` 嵌套检测, 触发即 raise ValueError。fallback 模块、render CLI、调度 prompt 全部走该函数。
> 3. **用户侧推荐**: 调用 render 前 `cd <project_root>` 或传绝对路径 `--output-dir $(pwd)/temp/output/daily_<YYYYMMDD>`。
> **失败兜底**: `daily_report_render_fallback.py` — render/validate 任一非 0 时复制昨日报告加黄条 + `_FALLBACK` 后缀
> **用户指令存档**: `daily_report_instruction.md` — v1.8 原文
>
> 相关脚本: `daily_report_fetch.py`(分层多源采集, 取代 `fetch_bing_news.py`) + `daily_report_sources.json`(源配置) + `daily_report_reference_sources.md`(参考层) / `daily_report_build_today.py`(旧版,保留兼容)
> 采集设计: `docs/specs/2026-06-20-daily-report-fetch-multisource-design.md`
> HTML主题: `claude_html_theme.md`

---

## 新流程概览 (v3.1)

```
Phase 1 采集 → Phase 2 整编(输出 report_data.json) → render.py(三件套) → validate.py(自检) → 交付
```

**关键**: LLM 只输出 `report_data.json` (纯数据), 所有格式/颜色/间距由 `render.py` 硬编码渲染。
`report_data.json` 结构见下方 Phase 2 输出规范。

---

## Phase 0 · 硬约束（执行前必读，违反即返工）

### H1. 时效窗口 D-1 00:00 ~ D 18:00 BJT（习称"24h 窗口"，实覆盖约 42h）— 第一硬约束 (v3.2 升级: 代码层强制)
- 仅纳入 **D-1日 00:00 ~ D日 18:00（北京时间）** 内发布的条目
- D = 报告日期（如6月4日报 → 仅6月3日~4日）
- **严禁**：为凑条目数而放宽窗口。宁可某板块条目不足，也不纳入超窗条目
- **v3.2 代码层守门员**：`daily_report_render.enforce_window(data)` 强制校验：
  1. `data["window"]` 字符串必须等于 `D-1 00:00 至 D 18:00` (BJT)，不符 → `ValueError` (render 入口 exit 2)
  2. 扫描 `s1_items/s2_items/s3_hot/s3_clues` 每条 `pub_date`，越窗 → 就地剔除 + stderr 警告
  3. `validate.py` E.4-07 同样执行严格 24h 检查
- 豁免路径：`data["manual_construction"] = true` (B 路手工构造, SOP v3.1 坑 #12)
- 验收命令：`grep -oP '\d+月\d+日' report.md | sort | uniq -c`，超窗日期出现则 FAIL
- **历史事故 (2026-06-20)**: window 字符串被 LLM 写成 `18:00~18:00` (窄 18h) + `data["date"]` 漂到 3 天 16 小时窗口; v3.2 enforce_window 已修复

### H2. 板块内倒序排列
- 每个板块内条目必须 **按发布日期严格倒序**（D日在前，D-1日在后）
- 同一天内按重要性排序
- 验收：逐板块提取日期序列，检查是否单调非递增

### H3. 条目数约束
| 板块 | 下限 | 上限 | 说明 |
|------|------|------|------|
| S1 非传统安全领域涉华要闻 | 3 | 5 | 不足3条时用D-1日补充，但不可超窗 |
| S2 主要国家及国际组织的重要动向 | 5 | 10 | 覆盖多领域优先 |
| S3 其他热点或苗头性线索 | 2 | 5 | 含3.1社会/行业热点 + 3.2苗头性线索 |
| S4 本期要情与趋势分析 | 2 | 4 | 跨事件关联分析 |
| S5 重点关注信号的情报价值 | 3 | 5 | 含情报缺口标注 |

### H4. 内容质量红线
- 每条目必须有：**来源媒体名 + 原文URL**
- 涉华政策类条目需 **≥2源交叉核验**（或标注"单源待确认"）
- 禁止主观评价词（"令人震惊""不幸的是"）
- 中文字数：正文 2000~3500 字

### H5. 路径防嵌套 (v3.4 新, R21 2026-08-25)
- 日报 json 直存 `temp/<name>.json`，产物直出 `temp/output/daily_<YYYYMMDD>/`；**禁止任何 `/temp/temp/` 嵌套**（fetch.py / render.py 已加 guard 拒绝并 exit 5）

---

## Phase 1 · 数据采集

### 1.1 爬虫策略（已验证）
| 来源 | 结果 | 替代方案 |
|------|------|----------|
| **Google News** | ❌ CAPTCHA封锁（46次全0） | → **Bing News** 无反爬 |
| 联邦站点 .gov (FDA/USGS/IEA/BGS) | ❌ Cloudflare 403 | → Bing聚合绕路 |
| WHO/ECDC/PAHO | ✅ Playwright+Chrome可爬 | 直接爬取 |
| Bing News | ✅ 无反爬，15查询批量 | **首选** |

### 1.1b 引擎: TMWebDriver (2026-08-25 端到端已验证)
- `daily_report_fetch.py --engine tmwebdriver`: 双通道 = RSS(urllib) + bing新闻卡(桥exec), 实测 263 条(218 RSS + 45 bing-tmwd), 后续 render/validate --strict 全过
- fetch.py 已就地适配两坑: `d.jump(url)`(无goto) + CARD_JS 包 IIFE `(()=>{...})()`(桥不自动调用函数体, 否则静默0卡, 详见 tmwebdriver_sop 通用特性)
- 前置: master daemon 常驻(18765 WS + 18766 HTTP, /link 需 POST); 采集前 `d.set_session('bing')` 钉死工作tab, 用完 CDP Page.close 关tab
- ⚠bing卡噪音: rare_earth 等类目离题卡多(股评/无关公司), 选稿须人工剔除, 勿按 digest 顺序直接取前N
- 渲染/校验 CLI: `python3 memories/daily_report_render.py <json> --fmt all` → `output/daily_<D>/`; `python3 memories/daily_report_validate.py <json> --docx <产物> --strict`

### 1.2 分层多源采集 (v3.3: config 驱动, 取代手工 fetch_bing_news.py)
- **入口零编辑**: 从 worktree 根执行 `python memories/daily_report_fetch.py [--date YYYY-MM-DD] [--min N]`
- **源配置** `daily_report_sources.json` (增删源改 config, 不改代码):
  - `daily_news[领域]` = `keywords` + `bing_sites`(域白名单) + `rss`(可空)
  - `analysis.think_tanks_rss` = 智库低频分析源, 命中喂 S4/S5 (feed 待逐源核实后填)
  - 纯数据平台/无 RSS 智库见 `daily_report_reference_sources.md`, **不进每日爬虫**, 整编时按需核对数字
- **双通道**: Bing `site:` 域约束 (绕 .gov 403, locale 锁 en-US + interval=7) + RSS stdlib 直拉; 按真实 URL 跨通道去重
- **每领域查询**: 优先 4 域受限 (SITES_PER_QUERY) + 一条不限域兜底
- Playwright 走 `channel='chrome'`; 如本地无 chrome channel 改 `executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"`

### 1.3 输出 schema (v3.3 新: {_meta, records}, 取代旧 {query_key:[...]})
```json
{
  "_meta": {"scraped_at": "2026-06-20T18:00:00+08:00", "total": N, "by_category": {...}},
  "records": [{"title","url"(已 unwrap),"source","pub_date_abs","rel_time","snippet","category","tier","channel"}]
}
```
- `pub_date_abs` 由代码用 `_meta.scraped_at` 锚点换算 (整编直接用, 不再自己猜锚点)
- 整编时按 `category` 把 9 采集领域映射到报告 5 板块 (S1-S5)

### 1.4 采集后处理 / 异常
- URL 已 unwrap Bing 跳转链 (pit #18 已修); 无 `pub_date_abs` 的条目整编标"（时效性不明）"
- **数据稀薄守门**: `total < --min`(默认 20) → `exit 3` + stderr 告警 → 触发 pit #12 B 路手工兜底
- **立即剔除超窗条目** (H1 24h), 后续不再使用


## Phase 2 · 条目整编

### 2.1 精选流程
1. 从采集JSON中按板块关键词分组
2. 按 **时效性(D日优先) → 重要性(涉华/战略级优先) → 多样性(避免同源集中)** 排序
3. 每条目提取：发布日期、来源媒体、原文URL、核心事实(181-220字中文, 严格区间)
4. **剔除超窗条目**（此步骤不可跳过）

### 2.2 条目模板（中文撰写）
```
**{D日/D-1日}，{来源媒体}报道：** {一句话核心事实}。{2-3句展开细节}。{分析性总结句，如有}。
▸ 来源: {原文URL}
```

> **v3.3 新增 (2026-08-25 实战踩坑, R19)**: LLM 整编时必须把 lead prefix `X月X日，X（Y）报道：` 写入 `report_data.json` 的 `body` **字段首部**（不能仅写在 MD/DOCX 渲染输出里）。
> - `daily_report_render._strip_body_lead()` (render L445) 会自动剥掉 body 已有前缀再由 `_format_md_item` (L475) 重建 → 渲染输出无重复前缀
> - `daily_report_validate` E.4-08 (validate L226) 强制检查 body 必须以 `X月X日` + `(报道|表示|声明|发布)` 开头，动词距日期 ≤40 字 — 否则 FAIL
> - 双源规则一致：JSON body 含 lead = validator 通过 + render strip 后视觉正确

### 2.3 五板块定义
| 编号 | 板块名 | 条目数 | 内容范围 |
|------|--------|--------|----------|
| S1 | 非传统安全领域涉华要闻 | 3-5 | 稀土管制/AI芯片/涉华外交/海外利益 |
| S2 | 主要国家及国际组织的重要动向 | 5-10 | 核能/粮食/水资源/气候/地缘博弈 |
| S3 | 其他热点或苗头性线索 | 2-5 | 含3.1社会/行业热点 + 3.2苗头性线索 |
| S4 | 本期要情与趋势分析 | 2-4 | 跨事件关联分析，每条一个趋势线 | **字段 schema 见 §2.4 / Appendix C** |
| S5 | 重点关注信号的情报价值 | 3-5 | 含情报缺口标注 (情报缺口：...) | **字段 schema 见 §2.5 / Appendix C** |

### 2.3b report_data.json 输出规范 (v3.1 新增, v3.2 升级: 强制扁平 schema)

**v3.2 强制约束**: render 与 validator **只认**扁平 schema (`s1_items/s2_items/s3_hot/s3_clues/trends/signals`)。旧 `sections[]` 嵌套结构 (SOP v3.0 时期) 不再被 `daily_report_render._get_section_items` 兼容 — 若 LLM 输出旧 schema，render 会因 `data['s1_items']` 缺失而抛 `KeyError` 触发 fallback。

LLM 整编完成后输出 `report_data.json`，结构如下：
```json
{
  "date": "2026-06-04",
  "monitoring_window": "2026-06-03 00:00 至 2026-06-04 18:00（北京时间）",
  "s1_items": [
    {"pub_date": "6月4日", "source": "Tech Times", "body": "正文约200字...", "url": "https://..."}
  ],
  "s2_items": [
    {"pub_date": "6月3日", "source": "Reuters", "body": "正文...", "url": "https://..."}
  ],
  "s3_hot": [...],
  "s3_clues": [...],
  "trends": "趋势分析正文(300-500字)",
  "signals": [
    {"label": "信号1：XXX", "text": "1-2句研判(含情报缺口)"}
  ]
}
```

**渲染**: `python daily_report_render.py report_data.json --format all`
**自检**: `python daily_report_validate.py report_data.json --strict`

### 2.4 本期要情与趋势分析（trends）写法 (v3.2 升级: 对齐 render.is_analysis 与 Appendix C 字段速查)

**字段结构**: `report_data.json` 的 `trends` 字段必须是 **dict**，三个 key 全部非空：

| key | 含义 | 字数 | 必含 |
|-----|------|------|------|
| `core_situation` | 核心态势 | 200-300 | 本期跨事件共性矛盾 |
| `actor_dynamics` | 行为体联动 | 200-300 | ≥2 主要行为体张力 |
| `china_impact_direction` | 涉华影响方向 | 200-300 | 引用本期涉华条目作论据 |

**渲染规则**（由 `render.is_analysis=True` 路径硬编码）：
- 每段以加粗黑体小标签开头：`**核心态势：**` / `**行为体联动：**` / `**涉华影响方向：**`
- 标签后正文不加粗，仿宋 12pt，主色
- 每段首行缩进 2 字符，1.5 倍行距
- 总长 600-900 字

**红线**：
- 禁止把 `trends` 写成 string / list — render 不会走 dict 分支，内容丢失
- 禁止三段任一为空字符串 — validator E.4-12 视为缺失
- 禁止标签自加冒号 — render 会自动追加 `：**`
- **每段严格 ≥200 字** — validator E.4-16 (191 字实测 FAIL，整 200-300 字是硬区间)

### 2.5 重点关注信号的情报价值（signals）写法 (v3.2 升级: 对齐 render.is_signals 与 Appendix C 字段速查)

**字段结构**: `report_data.json` 的 `signals` 字段必须是 **list of dict**，3-5 条：

```json
[
  {"label": "关键矿产供应链重构", "text": "印度评估西伯利亚稀土...(情报缺口：俄方报价条款未公开)"},
  {"label": "网络基础设施大规模受控", "text": "FortiBleed 事件影响超 8.6 万台..."}
]
```

**渲染规则**（由 `render.is_signals=True` 路径硬编码，[render.py:686](memories/daily_report_render.py)）：
- 标签文字由 render 渲染时自动追加 `：` — **LLM 禁止在 `label` 字段末尾写冒号**
- label 黑体加粗、橙色（ACCENT），text 仿宋主色
- 每条首行缩进 2 字符，1.5 倍行距
- 段落优先级：涉华 > 战略级 > 预警级

**红线**（与 validator E.4-17 / E.4-08 严格对齐）：
- 3-5 条 — validator 直接 FAIL
- `label` 末尾禁止含 `：` / `：` / `:` — validator E.4-08 段首加粗格式 FAIL（6-20 真实事故）
- 每条 `text` 必须含 `(情报缺口：xxx)` 标注 — 缺失视为"无情报价值研判"
- `text` 长度 **严格 60-120 字** — validator E.4-17 (130-152 字实测 FAIL, 130-152 → 60-120 字重写)
- `source` 字段最多 **1 对**全角括注（如 `BBC（英国广播公司）`）— validator E.4-18 多括注 FAIL（2026-08-25 R19 实战）

---

## Phase 3 · MD/DOCX/HTML 三件套渲染 (v3.1 → render.py, v3.2 D-4 路径强制)

> **格式控制权已转移**: Phase 3/4/5 的所有排版规范现已硬编码在 `daily_report_render.py` 中。
> 以下保留结构说明供参考,实际渲染由 `render.py` 保证一致性。
> 命令: `python daily_report_render.py report_data.json --format all` (不传 `--output-dir` 走默认)
>
> **v3.2 D-4 输出路径强制**: 三件套唯一输出位置 `temp/output/daily_<YYYYMMDD>/` (北京时间当日)。
> - CLI `--output-dir` 默认值已是 `temp/output/daily_<YYYYMMDD>/` (2026-06-20 起, 由 `render._check_output_dir` 白名单校验)
> - 显式传值必须以 `temp/output/daily_<8 位日期>` 开头, 否则 `exit 4` 拒绝
> - 历史漂移路径 `output/daily_*/` (6/20 真实事故) 已被白名单拒收

### 3.1 MD 文件结构 (参考)
```markdown
## 非传统安全领域动态日报（{D日}）

> 监测窗口：{D-1日} 00:00 至 {D日} 18:00（北京时间）

## 一、非传统安全领域涉华要闻
{条目们，D日在前，D-1日在后}

## 二、主要国家及国际组织的重要动向
{条目们，倒序}

## 三、其他热点或苗头性线索
### 3.1 社会/行业热点
### 3.2 苗头性线索

## 四、本期要情与趋势分析
{趋势条目}

## 五、重点关注信号的情报价值
{研判条目}
```

### 3.2 文件命名
`非传统安全领域动态日报_YYYYMMDD.md`



## Phase 4 · DOCX 排版规范 (v3.1 → 由 render.py 保证)
> 所有样式参数已内嵌于 `daily_report_render.py` 的 `render_docx()` 函数。
> 以下保留参考实现,修改样式时直接改 render.py 中对应常量。

### 4.1 色板
| Token | 值 | 用途 |
|-------|-----|------|
| 主色 PRIMARY | `#1A1A1A` | 正文/标题 |
| 次色 SECONDARY | `#C9B99A` | 英文副标题/分隔线/装饰 |
| 强调色 ACCENT | `#D97757` | 板块标题/标识行/序号/来源符号 |
| 灰色 GRAY | `#666666` | 来源标签/页脚 |
| 底纹 | `#FBEEE6` | 板块标题底纹 |

### 4.2 F.2 文档顶部样式（强制，逐层精确）
文档顶部由 **四层** 构成，从上至下依次排列，**居中对齐**：

| 层级 | 内容 | 字号 | 颜色 | 字重 | 特殊 |
|------|------|------|------|------|------|
| 第一层·标识行 | `■ 国际非传统安全领域 · 每日情报整编 ■` | 9pt | ACCENT #D97757 | 加粗 | 行高14pt |
| 第二层·主标题 | `非传统安全领域动态日报` | 36pt | PRIMARY #1A1A1A | 加粗 | 字体:微软雅黑, 行高38pt, 上空6pt |
| 第三层·英文副标题 | `INTERNATIONAL NON-TRADITIONAL SECURITY BRIEFING` | 9pt | SECONDARY #C9B99A | 常规 | 字距加宽60 |
| 第四层·日期行 | `YYYY年M月D日（星期X）` | 14pt | PRIMARY #1A1A1A | 加粗 | 上空8pt |

**顶部区域整体要求**：
- 四层之间 **不插入分隔线**，依靠字号与颜色层次自然区分
- 顶部区域与正文第一个板块之间加一条 **次色细横线(1pt)** 作为分隔
- 分隔线实现：`<w:pBdr><w:bottom w:val="single" w:sz="4" w:space="1" w:color="C9B99A"/></w:pBdr>`

### 4.3 python-docx 实现参考（顶部四层）
```python
from docx.shared import Pt, RGBColor
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml
from docx.enum.text import WD_ALIGN_PARAGRAPH

C_MAIN = RGBColor(0x1A, 0x1A, 0x1A)
C_ACCENT = RGBColor(0xD9, 0x77, 0x57)
C_SUB = RGBColor(0xC9, 0xB9, 0x9A)
C_GRAY = RGBColor(0x66, 0x66, 0x66)

# Layer 1: 标识行
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(0)
p.paragraph_format.space_after = Pt(0)
p.paragraph_format.line_spacing = Pt(14)
r = p.add_run('■ 国际非传统安全领域 · 每日情报整编 ■')
r.font.size = Pt(9); r.font.color.rgb = C_ACCENT; r.bold = True
r.font.name = 'Inter'
r._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')

# Layer 2: 主标题
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(6)
p.paragraph_format.space_after = Pt(4)
p.paragraph_format.line_spacing = Pt(38)
r = p.add_run('非传统安全领域动态日报')
r.font.size = Pt(36); r.font.color.rgb = C_MAIN; r.bold = True
r.font.name = 'Inter'
r._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')

# Layer 3: 英文副标题
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(0)
p.paragraph_format.space_after = Pt(0)
p.paragraph_format.line_spacing = Pt(14)
r = p.add_run('INTERNATIONAL NON-TRADITIONAL SECURITY BRIEFING')
r.font.size = Pt(9); r.font.color.rgb = C_SUB; r.bold = False
r.font.name = 'Inter'
r._element.get_or_add_rPr().append(
    parse_xml('<w:spacing {} w:val="60"/>'.format(nsdecls('w'))))

# Layer 4: 日期行
wk = ['星期一','星期二','星期三','星期四','星期五','星期六','星期日']
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(8)
p.paragraph_format.space_after = Pt(0)
p.paragraph_format.line_spacing = Pt(20)
r = p.add_run(f'2026年6月4日（{wk[date(2026,6,4).weekday()]}）')
r.font.size = Pt(14); r.font.color.rgb = C_MAIN; r.bold = True
r.font.name = 'Inter'
r._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')

# Separator line
p = doc.add_paragraph()
p.paragraph_format.space_before = Pt(6)
p.paragraph_format.space_after = Pt(12)
p._element.get_or_add_pPr().append(parse_xml(
    '<w:pBdr {}><w:bottom w:val="single" w:sz="4" w:space="1" w:color="C9B99A"/></w:pBdr>'.format(nsdecls('w'))))
```

### 4.4 板块标题样式
```python
# 板块标题: 左侧橙色粗线 + 淡橙底纹
p = doc.add_paragraph()
p.paragraph_format.space_before = Pt(16)
p.paragraph_format.space_after = Pt(8)
p.paragraph_format.left_indent = Cm(0.5)
pPr = p._element.get_or_add_pPr()
pPr.append(parse_xml('<w:shd {} w:fill="FBEEE6" w:val="clear"/>'.format(nsdecls('w'))))
pPr.append(parse_xml(
    '<w:pBdr {}><w:left w:val="single" w:sz="32" w:space="8" w:color="D97757"/></w:pBdr>'.format(nsdecls('w'))))
r = p.add_run('一、非传统安全领域涉华要闻')
r.font.size = Pt(14); r.font.color.rgb = C_ACCENT; r.bold = True
```

### 4.5 条目正文样式
- 前缀加粗: `6月4日，Tech Times报道：` → 12pt PRIMARY 加粗
- 正文常规: 12pt PRIMARY
- 来源行: `▸ `(ACCENT) + `来源: `(GRAY) + URL(SUB)，10.5pt

### 4.6 页面设置
```python
section = doc.sections[0]
section.page_width = Cm(21)    # A4
section.page_height = Cm(29.7)
section.top_margin = Cm(2.5)
section.bottom_margin = Cm(2.5)
section.left_margin = Cm(2.5)
section.right_margin = Cm(2.5)
```

### 4.7 页脚
```python
fp = section.footer.paragraphs[0]
fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = fp.add_run('非传统安全领域动态日报 · {DATE} · 第N页')  # PAGE field 由 render._setup_footer 注入
r.font.size = Pt(9); r.font.color.rgb = C_SUB  # 次色, 顶部加分隔线
```


## Phase 5 · HTML 生成 (v3.1 → 由 render.py 保证)
> HTML渲染已内嵌于 `daily_report_render.py` 的 `render_html()` 函数。

### 5.1 Claude HTML 主题
- 按 `claude_html_theme.md` 规范
- Primary `#1A1A1A` / Secondary `#C9B99A` / Tertiary `#D97757` / Neutral `#FAF9F7`
- 卡片用 `news-item` 列表 + 橙色圆形序号
- 字体: 正文系统无衬线, 代码/标签用 Space Mono

### 5.2 HTML 结构
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8">
<style>/* Claude theme CSS */</style>
</head>
<body>
  <header>顶部四层 banner (同DOCX视觉一致)</header>
  <main>
    <section id="s1">板块一</section>
    <section id="s2">板块二</section>
    ...
  </main>
  <footer>非传统安全领域动态日报 · {DATE} · 第N页</footer>
</body>
</html>
```

---

## Phase 6 · 交付前自检 (v3.1 → validate.py)

> **自动化自检**: `python daily_report_validate.py report_data.json --docx output.docx --strict`
> **E.4 内容自检 (14项)**: URL覆盖/字段完整/条目数/涉外因素/准入条件/时效窗口/倒序/缩写括注/命名等
> **E.5 排版自检 (12项, 需--docx)**: 顶部四层/板块标题底纹边框/来源行三色/页边距/页脚等

### 6.1 E.4 内容自检 (14项, 已编码于 validate.py)
> 以下为参考清单, 实际执行由 `daily_report_validate.py` 自动完成。

| # | 检查项 | PASS条件 |
|---|--------|----------|
| E.4-01 | URL覆盖 | 每条目有来源URL |
| E.4-02 | 字段完整性 | 必填字段无缺失 |
| E.4-03 | 板块一条数+涉外因素 | 3-5条, 含涉外因素标签 |
| E.4-04 | 板块二条数 | ≤10条 |
| E.4-05 | 3.1准入条件 | 标注准入条件标签 |
| E.4-06 | 中方主动发起 | 7日内+明文提及 |
| E.4-07 | 时效窗口 | D-1 00:00~D 18:00 (BJT) |
| E.4-08 | 段首加粗格式 | 日期+来源标加粗 |
| E.4-09 | 英文缩写括注 | 首次出现已括注中文全称 |
| E.4-10 | 来源行间距 | (由render保证) |
| E.4-11 | 倒序排列 | 各板块内按日期倒序 |
| E.4-12 | 板块四五无新材/无重叠 | 无新URL/无重叠文本 |
| E.4-13 | 加粗仅三处 | (由render保证) |
| E.4-14 | 文件命名 | 含YYYYMMDD |

### 6.2 E.5 排版自检 (12项, 需 --docx, 已编码于 validate.py)

| # | 检查项 | PASS条件 |
|---|--------|----------|
| E5-01 | 顶部标识行 | 含"每日情报整编" |
| E5-02 | 主标题 | "非传统安全领域动态日报" |
| E5-03 | 英文副标题 | 全大写, 含"NON-TRADITIONAL SECURITY" |
| E5-04 | 日期行 | 含YYYY年M月D日 |
| E5-05 | 分隔线 | 顶部与正文间有次色1pt底线 |
| E5-06 | 板块标题 | 底纹+左边框 |
| E5-07 | 段首来源标 | 加粗 |
| E5-08 | 条目正文 | 样式合规 |
| E5-09 | 来源行三色 | ▸(橙)+来源:(灰)+URL(次色) |
| E5-10 | 来源行间距 | 与正文间距合规 |
| E5-11 | 页边距 | 2.5cm |
| E5-12 | 页脚 | 含分隔线+页码 |

---

## Phase 7 · 产物归档

### 7.1 三件套
归档到 `./output/`（或当前目录）：
```
非传统安全领域动态日报_YYYYMMDD.md
非传统安全领域动态日报_YYYYMMDD.docx
非传统安全领域动态日报_YYYYMMDD.html
```

---

## Appendix A · 历史踩坑记录

| # | 坑 | 表现 | 解决 | 首现版本 |
|---|-----|------|------|----------|
| 1 | Google News CAPTCHA | 46次请求全0结果 | 改用Bing News | v1.0 |
| 2 | .gov 站点 Cloudflare 403 | FDA/USGS/IEA等全403 | Bing聚合绕路 | v1.0 |
| 3 | DOCX顶部样式不合规 | 缺少四层精确spec | Phase 4.2 逐层参数化 | v1.6 |
| 4 | 24h窗口违规 | 为凑条目数纳入D-2及更早 | Phase 0 H1前置为第一硬约束 | v1.6 |
| 5 | 板块内未倒序 | 6月4日与6月3日混排 | Phase 0 H2强制+自检脚本 | v1.6 |
| 6 | Playwright chromium启动失败 | 网络问题拉不下来 | 显式指定本地Chrome路径 | v1.5 |
| 7 | file_write大内容截断 | ≥10KB易流截断 | 改用 code_run + Python分块追加 | SOP编写 |
| 8 | 9板块→5板块结构变更 | v1.5用9板块,v1.6改5板块 | 以v1.6用户指令为准 | v1.6 |
| 9 | **E.4-08段首动词硬约束** | body必须以 `X月X日` + 1-40字 + (报道/表示/声明/发布) + 冒号 起首。写"推演监测/综合报道"等生造词全12条FAIL | 全局替换为"报道"或四选一, 加粗前缀由render自动加 | v3.1 |
| 10 | **E.4-09缩写括注** | 2-6字母大写缩写(IRA/WHO/LNG/FT/GDACS/SCMP等)首次出现必须括中文全称(美国《通胀削减法》(IRA)) | 首次出现用"中文全称(abbr)"形式, render时缩进加粗 | v3.1 |
| 11 | **schema版本分歧** | SOP说扁平{s1_items/...}, 旧报告用sections[].items[]; validator/render只认**扁平版** | LLM输出以validator认的schema为准, 遇分歧先读validator源码确认 | v3.1 |
| 12 | **B路手工构造(数据稀薄时)** | 周日/节假日fetch.py+RSS仍无满足H3条数时, 手工构造极简report_data.json(3+5+2+2+2+3) + 标"周日数据稀薄"免责声明 + signals里加"(情报缺口:6/X数据回归后核实)" | 优先级: A路(自动)→ B路(手工)→ C路(报告失败) | v3.1 |
| 13 | **24h 窗口漂移 (2026-06-20)** | LLM 把 window 字符串写成 3 天 16 小时 + window 18:00~18:00 偏窄 18h, 同时 report_data.json `date` 与条目 pub_date 范围不一致 | render 入口加 `enforce_window()` 强制 24h 校验, window 字符串不符 -> ValueError exit 2 触发 fallback | v3.2 |
| 14 | **输出路径漂移 (2026-06-20)** | render.py CLI 默认值 `output/daily_<YYYYMMDD>/` 与 prompt 期望的 `temp/output/daily_/` 不一致, 实际产物漂到 `output/` | render 默认值改为 `temp/output/daily_<YYYYMMDD>/` + `_check_output_dir` 白名单 (仅 `temp/output/daily_<8 位>/` 通过) + exit 4 | v3.2 |
| 15 | **管线从未入版本控制** | `.gitignore memories/*` 仅放过 4 个工具 SOP, `daily_report_render.py` 等核心代码从未 git 跟踪, 6/20 漂移从未被 review | `.gitignore memories/*` 白名单补 7 个 daily_report_* + fetch_bing_news.py | v3.2 |
| 16 | **render 必须从 worktree 根执行 (2026-06-20)** | 在 `memories/` 子目录跑 `python memories/daily_report_render.py` 输出落在 `memories/temp/output/...` 而非 `temp/output/...`; `--output-dir` 父路径被 D-4 白名单拒绝 (exit 4) | 从 worktree 根执行 `python memories/daily_report_render.py temp/report_data.json --fmt all` | v3.2 |
| 17 | **email_report.py 只扫 done/ 根 (2026-06-20)** | docx 复制到 `sche_tasks/done/20260620/` 子目录后, `python mailer/email_report.py` 报 FileNotFoundError; `done/` 根残留多个 docx 会随机挑 | docx 直接落 `sche_tasks/done/` 根; 每次执行前清空 done/*.docx | v3.2 |
| 18 | **fetch_bing_news.py 提取 bug (2026-06-20)** | 卡片 source 与 rel_time 同一文本节点拼接 (如 `CBSSports.com22 小时`); URL 多被 `bing.com/ck/...` 跳转链接替代; 标题/摘要截断 80-150 字 | **v3.3 已修**: `daily_report_fetch.py` locale 锁 en-US (时间英文化) + CARD_JS source/time 分离 + `unwrap_bing_url()` 还原跳转链 + snippet 上限放宽 800 | v3.2→v3.3 |
| 19 | **trends 键名错配导致 S4 空白 (2026-06-25)** | `daily_report_validate.py` 要求键名为 `china_impact_direction`; 但 `daily_report_render.py` 第 356/636/890 行仍读旧键 `china_impact`, 导致 S4 第三段空白且 validate 的 E5-08 简化检查无法发现 | trends 字段必须 dict 且键名严格为 `core_situation/actor_dynamics/china_impact_direction`; render.py 已同步修复 | v3.3 |
| 20 | **fetch urllib fast-path 无 snippet (2026-06-25)** | `daily_report_fetch.py --no-playwright` 走 urllib fast-path 时, 返回记录只有 `title/url/source/pub_date`, `snippet` 字段为空; 若直接 LLM 扩写 body 会大量编造 | B路手工构造时 body 只能以抓取 title 为唯一可核实事实, 附加极简公共背景, 并显式声明 `manual_construction=true` + `data_quality_note` | v3.3 |


## Appendix C · report_data.json 字段速查 (v3.1 扁平schema)

```python
{
  "date": "2026-06-07",                          # 报告日期
  "window": "2026-06-06 00:00 至 2026-06-07 18:00 (北京时间)",  # 监测窗口
  "s1_items":   [{"pub_date": "X月X日", "source": "...", "body": "X月X日，源报道：...", "url": "..."}],  # S1 涉华要闻, 3-5条
  "s2_items":   [同S1结构],                     # S2 各国动向, 5-10条
  "s3_hot":     [同S1结构],                     # S3.1 社会/行业热点, 与clues合计2-5
  "s3_clues":   [同S1结构],                     # S3.2 苗头性线索
  "trends": {                                   # S4 本期要情与趋势分析, dict结构(非list)
    "core_situation": "...",                    # 核心态势
    "actor_dynamics": "...",                    # 行为体动态
    "china_impact_direction": "..."              # 涉华影响方向
  },
  "signals": [{"label": "信号1", "text": "..."}]  # S5 重点信号, 3-5条, label无冒号
}
```

**红线复述**:
- body 字数: 单条新闻 180 < body ≤ 220 字 (validator E.4-15; s3_clues 豁免下限)
- source 字段: 最多 1 个括注对, 英文全称放 source_full_name (validator E.4-18; 禁"美联社（AP）（AP News）"双括注)
- body段首动词: 报道/表示/声明/发布 (四选一)
- 英文缩写首次出现: 中文全称(abbr)
- 倒序: 每板块D日在前,D-1日在后
- 文件名: `非传统安全领域动态日报_YYYYMMDD.{md,docx,html}`

## Appendix B · 监控网站清单

### 核心源
- Bing News (首选聚合)
- Reuters / AP / Bloomberg
- WHO / ECDC / CIDRAP (公共卫生)
- IAEA官网 (核安全)
- Carbon Brief / WMO (气候)
- FAO / WFP (粮食安全)

### 地缘与战略
- War on the Rocks / Foreign Affairs / Geopolitical Monitor
- Washington Examiner / The Hill
- Saudi Gazette / Gulf Today (中东)
- Daily Times / Euromaidan Press (区域)

### 技术与产业
- Tech Times / Seeking Alpha
- American Bazaar

### 数据源
- IEA https://www.iea.org/
- 全球能源监测 https://globalenergymonitor.org/
- Our World in Data https://ourworldindata.org/

## Appendix C-pre · v3.2 补遗 (R9, 2026-07-12)

| 坑 | 现象 | 解决 |
|----|------|------|
| 1. `validate.py` CLI 用错 | 误传 `--json`/`--input` 触发 argparse 报错,真实接口是**位置参数 `<report_data.json>` + 可选 `--docx <path>`** (无 `--strict` 也会跑全检) | `python memories/daily_report_validate.py temp/report_data.json --docx temp/output/daily_YYYYMMDD/*.docx` |
| 2. `data["window"]` 字符串必须含日期 | render.enforce_window 要求形如 `"2026-07-11 00:00 至 2026-07-12 18:00"` (BJT, 中文「至」),只写 `"D-1 00:00 至 D 18:00"` 占位符会被打回 | window 字段按当日日期填完整字符串,不要留 `D`/`D-1` 占位 |
| 3. `data["items"][i].pub_date` 要中文 | E.4-07 期望 `"7月12日"` 这种 `M月D日` 短格式,而非 `"2026-07-12"` 或 `"07-12"` | 整编时直接 `pub_date=f"{m}月{d}日"` |
| 4. body 段首来源必须加粗 + 冒号结尾 | E.4-08 模式 `^\d{1,2}月\d{1,2}日.{1,40}(报道\|表示\|声明\|发布):` (冒号是半角);`source` 媒体名不能超过 ~40 字否则 `报告:` 字数超出 | source 名截短到 12-14 字;body 首句 **`X月X日<来源>报道:**` 用中文冒号（按当前 validate regex 看是英文冒号,实测两个都可,但源长要小） |
| 5. trends 三段字数硬卡 200-300 | E.4-16 严格 `min(每段)=200 AND max(每段)=300 AND 总和∈[600,900]`;每段头必须 `“……”` 框引文 | 直接先写满 250 字一段,然后照边界裁 |
| 6. 大写缩写首次出现须括注中文全称 | E.4-09 扫 body 去掉 lead 后,首次见 `\b[A-Z]{2,6}\b` 看附近 25 字符内是否含 `中文(XXXX)` | 常见 EU/US 手工写 `欧盟（EU）`/`美国（US）`;IPO/WHO 等按需,正文写一次即可 |
| 7. `manual_construction=true` 必带 | B 路手工或数据稀薄时缺这一项会触发 E.4-07 redundant 报错 (D-1 00:00~D 18:00 和 JSON pub_date 不一致) | report_data.json 顶层加 `"manual_construction": true` |
| 8. 三件套输出强制 `temp/output/daily_YYYYMMDD/` | render 写入路径与 SOP D-4 白名单不符会 exit 2 | 先 `mkdir -p temp/output/daily_$(date +%Y%m%d)` |



R7 第一次端到端跑通,记下 3 个 L2 描述与实际不符的坑:

1. **render schema 仍向后兼容旧 `sections[]`**: L2 说"旧 sections[] 不再被 _get_section_items 兼容 (会抛 KeyError)" — **实测不会**。render 只输出 warning 并自动转扁平,正常出三件套。今后不必为了避免 KeyError 而一定用扁平 schema (扁平是偏好但非强制)。

2. **`fetch_bing_news.py` 硬编码 OUTFILE 必踩**: 脚本内 `OUTFILE = '../temp/bing_raw_20260619.json'` 相对路径 + 日期写死。从 worktree 根直接 `python memories/fetch_bing_news.py` 会报 `FileNotFoundError: ../temp/...`。**修复**:
   ```python
   import sys; sys.path.insert(0, 'memories')
   from fetch_bing_news import main
   import fetch_bing_news
   fetch_bing_news.OUTFILE = 'temp/bing_raw_20260620.json'  # 改当天
   fetch_bing_news.main()
   ```
   建议把 `OUTFILE` 改成 CLI 参数 (`argparse`) 或读 `BING_RAW_OUT` 环境变量。

3. **Bing News rel_time 已失效**: Playwright 抓的卡片 `rel_time` 字段全 0 — Bing News 当前 DOM 不再暴露相对时间字符串,不要花时间 regex split; `source` 字段的"域名+几小时"格式 (如 `Philstar.com7 小时`) 也只在中文 UI 出现,英文界面下 source 字段干净,rel_time 为空属正常。

4. **Bing News 涉华稿件命中率极低 (R7 实测)**: 15 查询 × 152 卡 → 6 条真新闻 → 0 条涉华。H4 红线(涉华≥2 源)在 Bing News 单一源下几乎不可能达到。**处置**:
   - A路: 接 cross_verify (L2 `temp/cross_verify.py`) 拿 Google News RSS 补二源
   - B路: 走 SOP A12 手工合成 + 顶部 `data_quality_note` 显式声明 + signals 全带"(情报缺口:...)"标签
   - 严禁 LLM 编造 2026-06-19/20 假事件 (LLM 知识截止 2026-01)

## Appendix D · Bing Playwright vs urllib 双通道 (R8, 2026-06-20)

R7 端到端跑通后,R8 反复遇到 Playwright 启动慢/挂起/版本冲突,新增 `urllib` 直连 fast-path 作为兜底。

### 通道对比

| 维度 | Playwright (原) | urllib (新 fast-path) |
|------|----------------|----------------------|
| 启动耗时 | 15-40s (chromium 拉起) | <1s (stdlib) |
| 适用环境 | GUI/headful/headless 全支持 | 任意 Python 3.9+ 容器 |
| 渲染能力 | 完整 DOM (含 JS 注入卡片) | 仅 SSR HTML (Bing News SSR 卡片可用) |
| URL 关键参数 | 任意 | **必须仅传 `q+qft+setmkt+setlang`**,**禁传** `form=QBNT/sp/lq/pq/sc/cvid`(后者触发 SPA,SSR 卡片消失) |
| UA 关键 | `chrome-...` | `Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36` |
| 抓取量级 (R8 实测) | 8 类目 27 条 | 8 类目 60 条 |
| 抓取质量 | 标题/摘要/来源/URL 完整,时间相对值 | 标题/摘要/来源/URL 完整,rel_time/author 偶空 |

### 触发规则 (R8 在 `run()` 入口)

1. CLI `--no-playwright` → 强制走 urllib
2. Playwright 调用 `TimeoutError/Exception` → 自动 fallback urllib
3. urllib 失败 → 旧行为报错退出

### 关键踩坑 (R8)

| 坑 | 现象 | 解决 |
|----|------|------|
| 1. 旧 fetch_bing_urllib 用 `build_bing_url` 全参,触 SPA,卡片 0 | 返回 `<div id="main_content">` 空壳,无 `data-title` | URL 精简到 4 参;headers 改用 `chrome-120` 完整 UA |
| 2. 误读 Bing 静态 HTML | 找 `<a class="title">` / `data-title` 均 0;实际新闻列表在 `<a title="..." href="...">` 属性里 | 旧 `<a class="title">` 模式在 2026 版 Bing 已失效,改用 `<a title>` + 紧邻 `<a title="来源名">` 配对 |
| 3. 一次 patch 改三件事易 0 records | 替换 fetch_bing_urllib 时 url/headers/regex 三者须同步换 | 复用 `temp/_bing_urllib_fetch.py` (R7 已 60 条) 作为唯一真相源,先复制粘贴再调 |
| 4. `--no-playwright` 跑前未删除残档 | 旧结果干扰判断 | 每次跑前 `rm -f temp/output/_evo_*.json` |
| 5. urllib 返回卡 DOM 含脚本 | 新闻标题藏在 `<script>` JSON 里,SSR 卡片在 `<a title>` 块内 | `CARD_JS` (data-title) 优先 + `CARD_HTML` (a title) 兜底,两者都返 0 才真失败 |

### 调用方式

```bash
# 自动 (Playwright 优先,失败 fallback)
python memories/daily_report_fetch.py --date 2026-06-20

# 强制 urllib (CI/快速冒烟)
python memories/daily_report_fetch.py --date 2026-06-20 --no-playwright

# 仅生成空 report_data.json 模板(供手工/缺数据时填)
python memories/daily_report_fetch.py --emit-template temp/report_data.json --date 2026-06-20
```

### 输出路径约束 (D-4 强化, 2026-08-02 用户反馈)

渲染器 `--output-dir` / emit-template / 抓取输出必须基于 **项目根目录** `<project>/temp/output/daily_<YYYYMMDD>/`, **不能用 cwd 相对路径** `temp/output/...`。当 cwd 已经是 `<project>/temp` 时, 相对路径 `temp/output/` 会嵌套成 `<project>/temp/temp/output/...`(本任务实测踩坑)。

**正确调用** (任选其一):
```bash
# 1. 渲染时显式指定 --output-dir 为项目根绝对路径
python memories/daily_report_render.py report_data.json --fmt all \
  --output-dir /Users/x404/Tau/.worktrees/tau-v5.0.0/temp/output/daily_20260802

# 2. 先 cd 到项目根再调用
cd <project_root> && python memories/daily_report_render.py temp/report_data.json --fmt all
```

**事后修复**: 若已嵌套成 `<project>/temp/temp/output/...`, 直接 `mv <project>/temp/temp/output/daily_<YYYYMMDD> <project>/temp/output/` 即可, render.py 不写绝对路径以外的副作用。

### 维护要点
- 任何 `build_bing_url` 改动都需双通道同时跑通测试
- Bing 改版 → 优先改 urllib 通道 regex (Playwright 可再升级 chrome)
- 60 条阈值是 R8 实测,8 类目 × 8-12 条/类目是当前水位
