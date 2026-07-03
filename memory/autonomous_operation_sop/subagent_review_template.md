# Subagent 评审 TODO 最佳实践模板 (L8)

> 目的: 让未来主 agent 稳定地召唤 subagent 评审 TODO, 避免 3 大坑。
> 触发: 任何需要第三方可信评审 TODO.txt 的场景。
> 维护: 召唤失败/出新坑时, 在 §5 增补一条。
> 落盘: 2026-06-18 (R4 partial, 模板已落盘, 实测待 L8 用户批后跑)

---

## 1. 启动 subagent (最小命令)

```bash
cd <CodeRoot>  # 含 taumain.py 的目录
TASK=review_todo_$(date +%Y%m%d)
mkdir -p temp/$TASK
cat > temp/$TASK/input.txt <<EOF
评审 temp/TODO.txt 的 [ ] TODO。读 memory/global_mem.txt + memory/autonomous_operation_sop/task_planning.md 了解环境。逐条 1-10 评分, 输出 temp/$TASK/review.md >=5KB, 7+ 节。
EOF
python taumain.py --task $TASK --llm_no 0
```

参数:
- `--task` = 子目录名, 唯一标识 (避免 §5 坑1 覆盖)
- `--input` = 短文本, 启动时自动建目录+清旧 output+写 input.txt
- `--llm_no N` = 多 LLM 并行编号, 单 subagent 跑 0

---

## 2. input.txt 样板 (TODO 评审主场景)

```
# TODO 评审任务 (单 subagent)

## 输入
- TODO 路径: <绝对路径>/temp/TODO.txt
- 记忆库根: <绝对路径>/memory/

## 任务
1. 读 TODO.txt, 列出所有 [ ] / [x] / [BLOCKED]
2. 读 L0 META-SOP + L1 insight + L2 global_mem.txt
3. 对每条 [ ] 给出 1-10 评分 + 1-2 句理由
4. 标注每条 [ ] 的显式依赖 (其他 TODO/外部权限/用户授权)
5. 输出 review.md >=5KB, 7+ 节
6. 给主 agent 推荐 TOP3 排序 + 删除/合并建议

## 硬约束
- ❌ 不给先验分数或诱导
- ❌ 不评如何实现, 只评值不值得 + 多复杂
- ✅ 引用具体 L2/L3 文件名作为依据
- ✅ 评审产物 = temp/<task_name>/review.md
```

---

## 3. review.md 输出格式 (7+ 节)

参考 2026-06-16 真实范式 `temp/review.md` (245 行, 8 节):

| § | 节标题 | 最低行数 | 内容 |
|---|---|---|---|
| 一 | 关键事实发现 | 5 | 读 L0/L1/L2 后的 3-5 条硬约束/事实 |
| 二 | JSON 评分 | 10 | 每条 TODO 一个 {name,score,deps,value,complexity,reversible} |
| 三 | 逐条详细理由 | 50 | 每条 2-5 句 (引用 L2/L3) |
| 四 | 低分项替换方案 | 20 | score<6 的各给一替换 |
| 五 | 依赖悬空/拆分 | 20 | 不拆也说无需拆的理由 |
| 六 | 主 agent 推荐排序 | 5 | TOP3 + 删除/合并建议 |
| 七 | TOP1 执行入口 | 30 | 步骤/产物/验收/避坑 |
| 八 | 评审结论 | 3 | 一句话 + 可不可执行判断 |

**硬下限**: 5KB / 200 行 / 7+ 节 (一-七); 实际评审 1.5x 富余 ≈ 350 行 ≈ 7KB。

---

## 4. 产物验证 (主 agent 收尾必跑)

```bash
REVIEW=temp/$TASK/review.md
[ -f "$REVIEW" ] || { echo "❌ review.md 不存在"; exit 1; }
SIZE=$(wc -c < "$REVIEW")
[ "$SIZE" -ge 5120 ] || { echo "❌ < 5KB ($SIZE B)"; exit 1; }
for sec in "一、" "二、" "三、" "四、" "五、" "六、" "七、"; do
  grep -q "^## $sec" "$REVIEW" || { echo "❌ 缺节: ## $sec"; exit 1; }
done
STDOUT=temp/$TASK/stdout.log
[ -f "$STDOUT" ] && grep -qi "output.*覆盖\|overwrit" "$STDOUT" && { echo "❌ 覆盖警告"; exit 1; }
TODO_C=$(grep -c "^\\[ \\]" temp/TODO.txt)
JSON_C=$(grep -c '"name":' "$REVIEW")
[ "$JSON_C" -ge "$TODO_C" ] || { echo "❌ 评分缺"; exit 1; }
echo "✅ 验收通过"
```

---

## 5. 三大坑 (L8 验收硬要求, 召前必读)

### 坑 1: output 覆盖 (高频)
**症状**: 启动新 subagent 后, 旧任务 output.txt 被静默清空
**规避**:
1. 每个评审用独立 task_name (含日期戳)
2. 启动前 `ls temp/{task}/` 必须只有 input.txt, 有别文件先 mv 到 backup/
3. 启动 5s 内立即 `cat temp/{task}/output.txt` 确认有内容
4. 旧评审归档: `tar czf temp/archive/review_$(date +%Y%m%d).tar.gz temp/review_*/`

### 坑 2: reply 节奏 10min 超时 (中频)
**症状**: subagent 写完 output 等主 agent reply, 10min 无 reply 自动退出
**规避**:
1. 每 2-5min 轮询一次 output.txt, 看到 [ROUND END] 立刻写 reply.txt
2. 不复述 subagent 结论再问, 直接给下一步
3. 复杂任务用 fork 模式 (code_run inline_eval=True) 让 subagent 继承上下文
4. >30min 任务拆成 pipeline

### 坑 3: fallback 转自评 (必堵)
**症状**: subagent 启动失败 (LLM 配额/网络/cwd 错), 主 agent 偷懒自己评
**SOP 硬约束**: task_planning.md step 7 "TODO 必须经 subagent 评审, 不允许自评, 未经评审的 TODO 不可执行"
**规避**:
1. 失败重试 >= 3 次 (换 --llm_no, 加 timeout, 简化 input)
2. 降级也必须 subagent 跑 (用 subagent.md 场景 2 Map 模式验证环境)
3. 实在不行 -> 标 [BLOCKED] 写明阻塞原因, 不进入执行序列

### 坑 4: `--task` 不带 `--nobg` 会派生 cwd=core/ 的子进程 (2026-07-02 R2 实地发现)
**症状**: subagent 启动即退出, PID 显示存在, output.txt 空白; 前台跑也秒退, 无 stack
**根因**: runtime.py main() 在非 nobg 路径里调用 `_spawn_standalone()` (或同源),
        subprocess 用 `python <runtime.py 绝对路径>` 启动; cwd 被设为 `os.path.dirname(__file__)`
        = CodeRoot/core/, 而 `from core.agent.runtime` 路径期望 cwd=CodeRoot, 子进程
        sys.path 含 CodeRoot/core 与 cwd(temp)但**不含 CodeRoot**, 第二次 import core.agent.runtime 失败 -> 派生进程秒退, parent 看到 PID 但无 stdout
**规避**:
1. 启动 subagent **必须加 `--nobg`** (3 个 R2 失败均因缺它)
2. 完整命令: `cd <CodeRoot>; PYTHONPATH=<CodeRoot> python3 -u -m core.taumain --task $TASK --input temp/$TASK/input.txt --llm_no 0 --nobg > temp/$TASK/stdout.log 2>&1 &`
3. worktree 多分支场景 PYTHONPATH 必须显式给, 不能依赖 cwd
4. 成功信号: 10s 内 `tail stdout.log` 看到 `[MixinSession] Using session`，`wc -l temp/$TASK/review.md` 增长

### 坑 5: worktree 路径分叉与 PYTHONPATH (2026-07-02 R2)
**症状**: 在 `.worktrees/<branch>/temp` 里跑 subagent, 即便 `--nobg` 也行为反常
**根因**: `--task $TASK` 与 `--input` 都是相对路径, 解析依赖 cwd。worktree 通常含独立 temp 目录; CodeRoot 路径与主 worktree 不同
**规避**:
1. 主 agent 先 `git worktree list` 确认 worktree 真实绝对路径
2. 启动前显式 export `PYTHONPATH=<worktree_CodeRoot>` 
3. 所有 temp/* 路径可用绝对路径 `temp/...` 替代, 因 cwd 即 worktree root

### 坑 6: input.txt 被 subagent 启动时写崩为 35B 自指路径 (高频, 2026-07-02 R3 实地复现 2 次)
**症状**: 主 agent 用 file_write / heredoc 写完 1500+ 字节的 input.txt, subagent 启动后 input.txt 被回写为 35B 的 `temp/{task}/input.txt` 单行自指; subagent 据此误判"任务文件只含自身路径, 无任务, 直接给收尾回应"。
**根因**: 推测 — LLM 在启动首轮 code_run 调用 cat/echo 时把 input.txt 内容覆盖; 也可能 runtime/handler 重置 task_dir 时将 input.txt 重生为 35B 占位。
**规避**:
1. 主 agent 启动 subagent **前**立即 `wc -c temp/$TASK/input.txt`, 字节数与预期一致才允许 `--nobg`
2. **必须用 file_write** 写 input.txt, 不用 heredoc-in-code_run (R3 heredoc 落地 35B 自指 1 次, 连写崩 2 种原因)
3. subagent 跑出首轮 LLM 后 **8s 内必查** `wc -c temp/$TASK/input.txt`, 若 < 100B, 立即 `kill -TERM $(cat subagent.pid)` 走 fallback
4. **fallback 路径**: 主 agent 自己按 §3 8节结构起草, 落档 `temp/l3_*_R3_increment.md` 等, 同时给 TODO 加 `[BLOCKED-by-subagent-input-corrupt]` 前缀, **禁止裸自评不入库**
5. 暂未定位到的根因 (为何 subagent 启动就回写), 留待 R4+/用户 patch runtime/handler 排查

### 坑 7: heredoc + cat > file 嵌入 code_run 写崩 (中频, 2026-07-02 R3)
**症状**: `cat > temp/$TASK/input.txt <<EOF ... EOF` 在 code_run shell block 内执行后, input.txt 只剩 35B 的路径自指字符串 (即末尾 `$TASK_DIR/input.txt` 字符串被误当命令输出)
**根因**: 推测 — heredoc EOF delimiter 被 shell escape 吃 / CodeRunner 对 stdout 多行 out-of-band 处理 / cwd=temp 时相对路径被解析到 ./input.txt
**规避**:
1. **禁用 heredoc 写 input.txt**, 改用 file_write (file_patch 不支持 binary, 但 markdown 完全可用)
2. 需要超长 input 时, 分块 file_write + **append** mode 多次追加
3. 写完必用 `wc -c` + `head -3` 双重验, 不要相信 tool 返回值

---

## 6. 端到端示例 (评审当前 TODO.txt)

```bash
cd <CodeRoot>; TASK=review_todo_$(date +%Y%m%d)
mkdir -p temp/$TASK
cat > temp/$TASK/input.txt <<EOF
评审 temp/TODO.txt 的 [ ] TODO。读 memory/global_mem.txt + memory/autonomous_operation_sop/task_planning.md。逐条 1-10 评分 + 理由, 输出 temp/$TASK/review.md >=5KB 7+ 节。参考范式: temp/review.md (2026-06-16, 245行, 8节, 6 TODO)。
EOF
python taumain.py --task $TASK --llm_no 0
# 轮询: while ! grep -q "review.md.*写入" temp/$TASK/output.txt; do sleep 180; done
# 验收: bash memory/autonomous_operation_sop/subagent_review_template_audit.sh $TASK
# 落分: 读 review.md §六"推荐排序", 删低分, 重排 TODO.txt
```

---

## 7. 维护

- 新坑 -> §5 增补一条, 标日期
- 新场景 input 模板 -> §2 增补一节
- real-world 评审 -> §3 加一行 (日期/路径/行数/节数/评分数)
- 审计脚本自动化 -> §4 bash 落盘为 `subagent_review_template_audit.sh` (R4 计划内未完)

**R4 落盘**: 2026-06-18 (R4 partial)
**关联**: TODO L8 (本任务) / TODO 3c (待 L8 用户批后实测)
