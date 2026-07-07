# Streamlit 上传文件功能 · 设计文档

- **日期**:2026-07-07
- **目标文件**:`apps/web/streamlit/app_v4.py`(前端主要改动)+ `core/agent/runtime.py`(后端补线)+ 新建 `apps/web/streamlit/upload_utils.py`
- **状态**:设计已定稿,待实现

---

## 1. 背景与目标

Tau 的 Streamlit 前端 `app_v4.py` 当前只能通过底部 `st.chat_input` 接收**纯文本**指令,没有任何文件上传/附件能力。用户希望支持:

- 上传 `.py`,让 Tau 读代码后 review / 修改
- 上传截图,让 Tau **原生看图**回答问题
- 上传 PDF 报告,让 Tau 总结要点
- 上传任意文件存到工作区,后续让 Tau 用工具翻阅

即一个覆盖**文本 / 图片 / 富文档 / 任意二进制**的通用附件功能。

## 2. 现状摸底(影响设计的事实)

| 维度 | 现状 | 结论 |
|---|---|---|
| `put_task` 签名 | `put_task(query, source="user", images=None)`([runtime.py:172](../../../core/agent/runtime.py)) | images 参数**已存在** |
| `run()` 解包 | [:196](../../../core/agent/runtime.py) 只取 `query/source/output`,**丢弃 images** | images 是"死参数",需补线 |
| LLM 多模态层 | [messages.py:76-78](../../../core/llm/messages.py) 已处理 `image_url` part → `input_image` | **已就绪,零改动** |
| `agent_runner_loop` | [loop.py:106](../../../core/agent/loop.py) 已有 `initial_user_content` 参数,首轮 user message 在 [:109](../../../core/agent/loop.py) 组装 | 复用该参数传多模态 list,**loop.py 零改动** |
| 文件工具 | `core/tools/file_io.py` 有 `file_read/file_write`,`expand_file_refs` 用 `{{file:路径:起:止}}` 语法 | 工具层不动 |
| 工作目录 | `TEMP = <repo>/temp/`([paths.py](../../../core/paths.py)),handler cwd = TEMP | 落盘到 `temp/uploads/` |
| 视觉能力标记 | backend 无 `supports_vision` 之类的标记 | 不支持视觉时靠保底(见 §8) |
| TUI 参考 | [apps/tui/app.py:1158](../../../apps/tui/app.py) 已有「落盘 + `[Image #N]`/`[File #N]` 占位符」机制,但 TUI 的 `put_task` 也未传 images | 语义可借鉴,占位符协议 web 端不需要 |

**一句话**:文本/任意文件近乎免费,「看图」要把断掉的 images 线接通,PDF 要靠 agent 自解析。

## 3. 需求决策记录

经逐项澄清,确定以下决策:

| # | 决策点 | 选择 |
|---|---|---|
| 1 | 交互模型 | **暂存式**:上传 → 待发附件挂输入区 → 回车时「文本 + 全部附件」一起发 |
| 2 | 图片看图 | **第一版就补线**,原生多模态(接通 `put_task` 的 images) |
| 3 | 富文档解析 | **零依赖分层**:纯文本前端读正文注入;图片走多模态;富文档/二进制落盘交给 agent `code_run` 自解析 |
| 4 | 落盘 | `<repo>/temp/uploads/<UTC时间戳>__<原名>`;同名不覆盖 |
| 5 | 文本注入阈值 | ≤ 200 KB 且 ≤ 5000 行 → 注入正文;超过 → 只落盘 + 清单标注 |
| 6 | 容量上限 | 单文件 50 MB;单条消息 ≤ 10 附件 |
| 7 | 会话边界 | 新建对话清空待发附件;已发送附件磁盘文件保留 |
| 8 | UI 布局 | `chat_input` 正上方待发条 + 图片内联缩略图 + 文件 chip |
| 9 | 不支持视觉的链路 | **方案 P**:不判断能力,runtime 直接传 images;不支持时 LLM 报错(现有 except 显示),用户切链路;图片始终落盘+路径作保底 |
| 10 | 实现路径 | **路径 1**:最小侵入前端 + 补 images 线;不动工具层 |

## 4. 架构总览

```
┌─ apps/web/streamlit/upload_utils.py (新建·纯逻辑·可测) ─────────────┐
│  常量 + save_upload / extract_text / read_image_b64 / build_prompt   │
│  (零 streamlit 依赖,可独立 import 单测)                              │
└──────────────────────────────────────────────────────────────────────┘
                              │ import
┌─ apps/web/streamlit/app_v4.py (前端 UI) ────────────────────────────┐
│  ① session_state.pending_attachments = [ {id,name,size,kind,path,    │
│         text?,img_b64?,lines?}, ... ]   ← 待发附件(会话级)           │
│  ② 待发条 fragment: chip[×]… + st.file_uploader(多选)               │
│  ③ render_html_message: user 气泡支持 内联缩略图 + 文件 chip          │
│  ④ start_agent_task: 组装 query+images → put_task(prompt,source,imgs)│
└──────────────────────────────────────────────────────────────────────┘
                              │ put_task(images=…)
                              ▼
┌─ core/agent/runtime.py (后端补线·仅 1 处) ───────────────────────────┐
│  ⑤ run(): 解包 task 取 images(当前被丢弃)                            │
│  ⑥ _build_initial_user_content(query, images) → 传 initial_user_content│
└──────────────────────────────────────────────────────────────────────┘
                              │ initial_user_content = 多模态 list
                              ▼
┌─ core/agent/loop.py (零改动) ────────────────────────────────────────┐
│  ⑦ 首轮 user message: content = initial_user_content(含 image_url)   │
└──────────────────────────────────────────────────────────────────────┘
                              │ 多模态 message
                              ▼
                       core/llm/messages.py (已就绪·零改动)
```

**三块职责分明**:
- **前端**(`upload_utils.py` + `app_v4.py`):上传 / 暂存 / 落盘 / 文本注入 / 气泡渲染 / 组装发送
- **后端补线**(`runtime.py`):让 images 真正流到 LLM
- **LLM 层**(`messages.py`)+ **工具层**(`file_io.py`):零改动

**不触碰**:`file_io.py` / 工具层 / `core/` 顶层结构 / `memory/`。符合 CLAUDE.md「外科手术式 + 结构勿大重排」。

## 5. 组件分解与接口

### 5.1 后端补线 · `core/agent/runtime.py`

**新增纯函数:**

```python
def _build_initial_user_content(raw_query, images):
    """images 为空→None(保持原行为);非空→多模态 parts list。"""
    if not images:
        return None
    parts = [{"type": "text", "text": raw_query}]
    parts += [{"type": "image_url", "image_url": {"url": u}} for u in images]
    return parts
```

**`run()` 改动(两处):**

```python
# 解包处(原 :196):补回 images
raw_query, source, display_queue, images = (
    task["query"], task["source"], task["output"], task.get("images", []))

# 调 loop 前(原 :214):组装并传入
initial_user_content = _build_initial_user_content(raw_query, images)
gen = agent_runner_loop(self.llmclient, sys_prompt, raw_query, handler, self.tools_schema,
                        max_turns=80, verbose=self.verbose, yield_info=True,
                        initial_user_content=initial_user_content)  # ← 新增
```

> `loop.py` / `messages.py` / `file_io.py` / 工具层:**全部不动**。

### 5.2 前端纯逻辑 · `apps/web/streamlit/upload_utils.py`(新建)

**常量:**

```python
UPLOAD_DIR = TEMP / "uploads"
_TEXT_EXTS  = {".py",".md",".txt",".json",".csv",".log",".xml",".html",
               ".yaml",".yml",".toml",".ini",".sh",".js",".ts",".sql"}
_IMAGE_EXTS = {".png",".jpg",".jpeg",".gif",".bmp",".webp",".tiff",".tif",".ico"}    # 同 TUI
TEXT_INJECT_MAX_BYTES = 200 * 1024
TEXT_INJECT_MAX_LINES = 5000
MAX_FILE_SIZE  = 50 * 1024 * 1024
MAX_ATTACHMENTS = 10
```

**函数:**

| 函数 | 职责 | 签名 |
|---|---|---|
| `save_upload(uf, upload_dir=UPLOAD_DIR)` | 校验大小 → 落盘(`basename`+时间戳)→ 按 ext 分流 → 返回元数据 dict;超限/失败返回 None | `-> dict\|None` |
| `extract_text(path)` | 读 UTF-8 正文(`errors="replace"`),返回 `(text, lines)`;超阈值 `text=None` | `-> tuple[str\|None, int]` |
| `read_image_b64(path)` | 读字节 → `data:image/<ext>;base64,...` | `-> str` |
| `build_prompt(text, atts)` | 组装 query:用户文本 + 文本类正文注入 + 全部附件清单(含 binary 路径) | `-> str` |

**附件元数据 dict 结构:**

```python
{"id": str, "name": str, "size": int,
 "kind": "text"|"image"|"binary",      # 按 ext 分流
 "path": str,                          # 落盘绝对路径
 "text": str|None, "lines": int|None,  # kind=text 时
 "img_b64": str|None,                  # kind=image 时(data URI)
 "thumb_b64": str|None}                # 图片压缩缩略图(气泡渲染用)
```

**分流细则(`save_upload` 内部,职责单一:落盘 + 分流 + 提取):**

- **text 类**:读字节 → 计算可打印字符率 → **≥ 60%** 才调 `extract_text`、`kind="text"`;**< 60% 降级为 binary**(防止二进制误判为文本产生乱码)。可打印率检测归属 `save_upload`,不归 `extract_text`。
- **image 类**:用 **PIL**(TUI 已用,复用已有依赖,**非新增依赖**)生成压缩缩略图 `thumb_b64`(max 400px / JPEG q70);同时 `read_image_b64` 生成原图 `img_b64`。
- **binary 类**:仅落盘 + `path`,`text`/`img_b64`/`thumb_b64` 均为 None。

### 5.3 前端 UI · `app_v4.py`

**A. 状态** — `st.session_state.pending_attachments: list[dict]`(会话级)

**B. 函数:**

| 函数 | 职责 |
|---|---|
| `render_pending_bar()` (`@st.fragment`) | 待发条:渲染 chip[×] + `st.file_uploader(accept_multiple_files=True)`;处理上传/删除 |
| `attachment_chip_html(att)` | 单个 chip / 缩略图的 HTML 片段 |

**C. 改造点:**

- [start_agent_task](../../../apps/web/streamlit/app_v4.py)(原 :547):扩展为接收 `attachments` → 组装 `query = build_prompt(text, atts)`、`images = [a["img_b64"] for a in atts if a["kind"]=="image"]` → `put_task(query, source, images)`
- [render_html_message](../../../apps/web/streamlit/app_v4.py)(原 :408):user 消息新增可选 `attachments` 参数 → 气泡内:图片内联 `<img>` 缩略图、其他文件 chip
- messages 列表项追加(原 :612):`"attachments": [...]` 字段供重渲染

**D. 注入格式(agent 在 query 里看到的样子):**

```
<用户输入的文本>

---
📎 已上传文件:
1. demo.py (文本·340行) — 正文已注入 ↓
```python
<…demo.py 正文…>
```
2. report.pdf (二进制·1.2MB) — 已落盘 temp/uploads/20260707T1430__report.pdf(可用 file_read 读取)
3. shot.png (图片·800KB) — 已作为图像附件发送
```

## 6. 数据流时序

> Streamlit 每次交互都从头重跑整个脚本,状态只能存 `session_state`。

```
用户                前端(app_v4.py)              session_state                 后端(runtime/loop)
──────────────────────────────────────────────────────────────────────────────────────────────────

【① 上传】
 选文件 ──▶ file_uploader 返回 [uf…]
            对每个 uf → save_upload(uf)          pending_attachments += [att…]
            清空 uploader 值(防 rerun 重复)▲
            st.rerun()  ◀────────────────────── (重跑:待发条显示新 chip)

【② 暂存期】
 打字/再传/删 ──▶ chat_input 文本(未提交)
            点 chip[×]                          pending_attachments 移除该项; rerun
            再传文件                            回到 ①(校验 ≤ MAX_ATTACHMENTS)

【③ 发送:回车】
 回车 ──▶ prompt = chat_input(可能为空)
            atts = pending_attachments(快照)
            校验:空文本&无附件→不发;有附件无文本→默认 prompt「请处理这些文件。」
            query  = build_prompt(prompt, atts)
            images = [a.img_b64 for a in atts if kind==image]
            messages.append({"role":"user",       messages[-1].attachments = atts 快照
              "content":prompt,"time":ts,"attachments":atts快照})
            put_task(query, source, images) ──▶  task_queue.put({query,source,images,output})
            pending_attachments = []  (清空)
            streaming=True; st.rerun()

【④ agent 处理】                                                      run() 取 task{…,images}
                                                                       initial_user_content =
                                                                         _build_initial_user_content(query, images)
                                                                       agent_runner_loop(…, initial_user_content)
                                                                       loop: messages=[{system},{user,content=多模态}]
                                                                       client.chat → LLM 收到 文本+图像 ◀── 看图在此
                                                          ◀──────── display_queue 流式 {next/done}

【⑤ 渲染】
 rerun     遍历 messages:
            user 气泡 → render_html_message("user",text,ts,attachments)
                        ├─ image kind → 内联 <img src=thumb_b64> 缩略图
                        └─ text/binary → chip(图标·名·大小·行数)
            streaming 中 → render_streaming_area()(现有逻辑不变)

【⑥ 会话边界】
 新建对话 ──▶ btn_new_chat 内              pending_attachments=[](连同 messages 等)
```

### Streamlit 三个坑(实现时注意)

1. **file_uploader 重复处理** — 同一批文件每次 rerun 都会再次返回。用组件 key + 处理后清空 `session_state[key]=[]`(在组件重建前),或用已处理指纹去重。
2. **chat_input 与 file_uploader 不在同一组件** — 文本在底部 `chat_input`、附件在它上方的 fragment。发送时合并两处的 `session_state`,而非靠组件返回值。
3. **附件快照 vs 引用** — `messages` 里存附件**快照副本**(含已落盘 path、已提取 text/b64),发送后即便 `pending_attachments` 清空,历史气泡仍能渲染。

## 7. 不变的现有流程

- streaming / 停止 / 轮询([poll_agent_output](../../../apps/web/streamlit/app_v4.py)) / 分段渲染:**完全不动**
- 侧边栏 LLM 切换 / token 统计:不动
- streaming 时 `chat_input(disabled=True)` 已禁用——附件区同样禁用上传

## 8. 错误处理与边界场景

| 场景 | 处理 |
|---|---|
| 超单文件上限 50 MB | `save_upload` 返回 None + `st.toast("文件过大(上限 50MB)")` |
| 超附件数上限 10 | 拒绝新增 + toast |
| **路径穿越 / 特殊文件名** | 落盘只用 `os.path.basename()` + 时间戳前缀,彻底杜绝 `../` 与绝对路径注入 |
| 同名重复上传 | 时间戳保证不覆盖,正常处理 |
| 不识别的扩展名 | 兜底当 `binary`(落盘+路径进清单),不报错 |
| 文本超注入阈值(>200KB 或 >5000 行) | 不注入正文,清单标注「大文件·已落盘·请用 file_read 分段读」 |
| 文本解码异常(非 UTF-8) | `errors="replace"`;可打印字符率 < 60% 自动降级为 binary |
| 图片损坏 / 读不出 | `read_image_b64` 失败 → 降级为 binary(落盘+路径) |
| 空文本 + 有附件 | 自动用默认 prompt「请处理这些文件。」 |
| streaming 进行中 | 上传区禁用(`chat_input` 已 `disabled=streaming`,附件区同步) |
| 落盘失败(权限/磁盘满) | `save_upload` try/except → toast 报错,不入 pending |
| 删除待发附件 | 同时删磁盘文件;**已发送的附件磁盘文件保留**(历史消息引用路径) |
| **历史气泡图片性能** | 气泡只内联**压缩缩略图**(max 400px / JPEG q70,前端生成);原图落盘保留。避免每次 rerun 重传大 base64 |
| **纯文本链路收到图片**(方案 P) | runtime 不判断能力,直接传 images;不支持视觉的链路 LLM 报错 → [现有 except](../../../core/agent/runtime.py)(:232) 显示 → 用户切链路;图片**始终落盘 + 路径进 query 清单**作保底,切链路后 agent 仍可 `file_read`/`code_run` 读图 |

## 9. 测试策略

### 9.1 为可测性分层

- 前端纯逻辑抽到 `upload_utils.py`(零 streamlit 依赖,可 import 单测)
- 后端补线逻辑抽成 `_build_initial_user_content` 纯函数

### 9.2 单元测试清单(对齐项目 pytest 风格,见 [tests/](../../../tests))

**`tests/test_streamlit_upload.py`(新建)—— 测 `upload_utils.py` 纯函数**

| 测试 | 断言 |
|---|---|
| `test_save_upload_text_file` | 落盘成功 + `kind=="text"` + text 已提取 |
| `test_save_upload_image_file` | `kind=="image"` + `img_b64` 合法 data URI |
| `test_save_upload_binary_file` | `kind=="binary"` + 仅 path |
| `test_save_upload_oversize_rejected` | >50MB 返回 None |
| `test_save_upload_path_traversal_sanitized` | 文件名 `../../etc/x` → 只落 `x` |
| `test_save_upload_same_name_no_overwrite` | 两同名 → 两个不同时间戳文件 |
| `test_extract_text_under_threshold` | 返回 `(text, lines)` |
| `test_extract_text_over_threshold` | 超阈值 → `(None, lines)` |
| `test_save_upload_non_utf8_degrades_to_binary` | 可打印率 < 60% → `kind="binary"`(降级归属 save_upload) |
| `test_read_image_b64_data_uri` | 返回 `data:image/...;base64,xxx` |
| `test_build_prompt_text_injected` | 文本类正文进 query + 围栏标注 |
| `test_build_prompt_binary_path_only` | binary 仅进路径清单 |
| `test_build_prompt_image_noted` | 图片标注「已作为图像附件发送」 |
| `test_build_prompt_empty_attachments` | 无附件 → 返回原文本不变 |

**`tests/test_runtime_images.py`(新建)—— 测补线纯函数 + 结构不变量**

| 测试 | 断言 |
|---|---|
| `test_build_initial_content_no_images` | `images=[]` → `None`(向后兼容) |
| `test_build_initial_content_with_images` | 返回 `[text_part, image_url_part…]` |
| `test_build_initial_content_url_format` | part = `{"type":"image_url","image_url":{"url":…}}` |
| `test_runtime_unpacks_images` | 源码级:`run()` 解包了 `task["images"]`(inspect 风格,防回归成"死参数") |

> 最后一项照搬 [test_loop_no_upper_deps](../../../tests/test_core_agent_layout.py) 的 `inspect.getsource` 套路——把"images 不再被丢弃"固化为结构不变量。

### 9.3 UI 层:手动验证清单(项目 verify skill 驱动真 app)

项目无 streamlit app 测试先例,第一版 UI 不硬上自动化,用 verify skill 逐项过:

- 上传 `.py` + 文本 → agent 收到正文注入并 review
- 上传截图 → agent **原生看图**回答(验证补线)
- 上传 PDF → agent `code_run` 解析后总结
- 多文件 + 文本一条消息发送
- 删除待发附件 → 磁盘文件同步删除
- 超 50MB → toast 拒绝;超大文本 → 不注入、清单标注
- streaming 中上传区禁用
- 新建对话 → 待发附件清空

## 10. 范围边界(v1 不做)

以下明确**不在**第一版范围,列为后续增强:

- **视觉能力标记 / 自动降级**(方案 Q):给 backend 加 `supports_vision`,不支持时自动不注入多模态。第一版走方案 P(报错 + 保底)。
- **PDF/Word 前端解析**(方案 B):第一版富文档靠 agent `code_run` 自解析。
- **拖拽到主区域上传**:Streamlit 原生不友好,第一版用 `st.file_uploader`。
- **附件跨会话持久化**:待发附件是会话级,不跨对话残留。
- **图片点击放大 / 原图预览**:第一版只内联缩略图。

## 11. 风险

| 风险 | 缓解 |
|---|---|
| 纯文本链路收到图片报错(方案 P 的代价) | 图片始终落盘 + 路径进 query 保底;用户可切链路;错误由现有 except 显示 |
| base64 图片撑大 LLM 请求 | 气泡用压缩缩略图;images 通道传原图(受 LLM API 自身边界约束,50MB 上限已挡住极端情况) |
| Streamlit rerun 导致 file_uploader 重复处理 | §6 三个坑已预判,实现时用 key + 清空策略 |
| `app_v4.py` import 副用阻塞测试 | 纯逻辑抽到 `upload_utils.py` |
