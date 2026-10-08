# 收尾计划（2026-10-08 晚）— 供你据此布置 goal

用途：把剩余验收拆成可一次性授权的条目。你照这份清单下 goal，我就不再逐项问。
每一项都标了 **【自主】**（我可独立完成）或 **【需你在场】**（必须你来配合）。

---

## 0. 当前状态快照（本轮实测，非转述）

| 项 | 状态 |
|---|---|
| git HEAD | `65beaf6`，全部改动**未 commit / 未 push** |
| 后端 pid | 3812（持有 48911/48912/48916），已运行 ~132 分钟 |
| 桌面 | `N.E.K.O.exe` pid 21432；角色面板 hwnd 7538316 |
| 端口 48915 | agent/character 状态 API（`health` / `agent/state` / `agent/flags`） |
| 端口 48916 | 嵌入式用户插件服务器（Study 入口） |
| Study | `ready` |
| awareness | `enabled: false`，runtime `active: false`（已恢复关闭） |
| 数据库 | WAL 模式，`qa_records` 5 条、`interactions` 33 条、`topics` 821 条 |
| 回归 | 14 项 Python + 2 个前端脚本通过 |

**一处 handoff 表述修正（重要）**：交接文档里"记录 id 24/29/33"指的是 **`interactions` 表的 id**（共 33 条学习交互），
**不是** `qa_records`。`qa_records` 目前只有 5 条（id 1–5）。
红线"不要用初始全量备份覆盖数据库"因此应理解为：**会抹掉 `interactions` 的 33 条 + `qa_records` 的 5 条**。
本轮已用只读方式核实，未做任何写入。

**已完成（本轮新增）**：
- **Stage 1 关闭** — awareness 消息已在角色 UI 上确认显示。决定性证据：`had_input=False` 的一轮
  LLM turn 后，角色面板选项文本从「切回来了 / 好啦好啦 / 窗口像个小星球」变为
  「好，我切回来了，正在写 cos·ln x / 好啦不闹了，我乖乖写 cos·ln x / 遵命，指挥官」。
  证据：`benchmarks/raw/evidence/goal-stage1-correlate.json` + `stage1-correlate-hit{0,1,2}-224213.png`。
- **Stage 2 根因定位完成** — 见下节，尚未修复。

---

## 1. Stage 2：选区截图 `capture_busy`

### 已查明的根因（这部分不用再查）
- **CSRF 是红鲱鱼**。插件走 `httpx` loopback 且**不带 `Origin`**，
  `screenshot.py:313-314` 明确允许这种纯服务端调用跳过 CSRF。实测对比：
  - 无 `Origin` → `409 capture_busy`（插件的真实路径）
  - 带 `Origin` → `403 csrf_validation_failed`（另一道独立且正确的防护）
- **邻居通道全部健康**，说明渲染器在、桥接正常：
  - `/api/capture/health` → `available: true`
  - `/api/capture/screenshot` → **200，364KB PNG (1666×1080)**，已解码存证
    `evidence/stage2-bridge-window.png`
- **故障点**：`utils/capture_bridge.py:93` 的模块级全局 `_interactive_capture_active`。
  在 416 行置 True，仅由 `_release_interactive_capture`(512 行) 清除；而
  `retain_busy_until_renderer_stops()`(441–453 行) 会把 `release_on_return` 置 False，
  把释放交给一个等渲染器 future 的后台任务。**future 无人 resolve → 锁永久保持**。
- **顺带发现一个真实产品缺陷**：`entry_ocr_entries.py:79-110` 的降级白名单只有
  `{no_renderer, main_server_unavailable, interactive_unavailable}`，**`capture_busy` 不在内**，
  所以锁一卡整个 OCR 直接 `Err`，用户没有任何恢复路径。

### 待办与决策点
| # | 动作 | 类型 | 说明 |
|---|---|---|---|
| 2.1 | 重启 pid 3812，重启后立刻重跑无 `Origin` 的 interactive 请求 | **【需授权】** | 会短暂中断 N.E.K.O（渲染器重连）。**这是区分两种泄漏机制的唯一手段**：重启后若仍 409 → 锁被活跃会话重新占用；若返回真实 overlay / `renderer_timeout` → 确认是泄漏，问题在 release 路径 |
| 2.2 | 据 2.1 结果给出 release 路径修复补丁 | **【自主】** | 只交 diff，不改运行中的二进制 |
| 2.3 | 把 `capture_busy` 纳入降级白名单，使卡锁时退化为全屏而非硬失败 | **【自主】** | 改插件源码，需重部署；属已知的产品缺陷修复 |
| 2.4 | 严格模式回归：开 `allow_fullscreen_fallback=false`，验证不自动回退 | **【自主】** | 依赖 2.1 的锁是否已清 |

> 2.1 是唯一需要你点头的地方。若你不想中断后端，我可以改为只交付 2.2/2.3 的补丁与
> 静态论证，但那样**无法确认**根因是泄漏还是活跃会话。

---

## 2. Stage 3：评分与教学广度（6–8 条，你已封顶）

你已明确"先就这样不用扩大"，所以**严格 6–8 条，不扩**。

### 观察维度
1. 同一题的错误/正确两答，评分是否稳定区分
2. 长上下文（连续追问后）评分是否漂移
3. 第二份材料是否串到第一份的知识点
4. **mastery 污染**：`mastery_snapshots`（现 5 条）与 `interactions`（现 33 条）是否被正常累加而非覆盖
5. **知识图谱是否真被用**：`candidate_knowledge_items`(6) / `knowledge_evidence`(11) 是否在出题时被引用

### 决策点
| # | 动作 | 类型 |
|---|---|---|
| 3.1 | 跑 6–8 条样本，逐条记录 verdict/score/mastery_delta | **【自主】** |
| 3.2 | 采集前先另存一份 DB 快照到 `evidence/`（**增量另存，绝不覆盖**） | **【自主】** |
| 3.3 | 结束后比对 `interactions` 33 条与 `qa_records` 5 条**只增不减** | **【自主】** |

> 注意：样本会产生新的 `interactions`/`qa_records`，这是验收的必然结果。
> 若你希望**零写入**，请改为只做 3.2 的静态分析，我来只出不写库的分析报告。

---

## 3. Stage 4：正式源码集成

### 现状
- 已有 `patches/neko-study-2026-10-08/`：`study.patch`(25KB) + `host-loop.patch`(6KB) + README
- 候选源码 checkout：`1d814cf32fba8c02b5727d2890710e4e7b8ece24`
- 本机实际后台是 Nuitka/Python 3.11 冻结 exe，SHA256 `BE32BD85…086AF6288`
- README 已注明：**冻结二进制的兼容钩子不是发布方案**

### 决策点（这三条请你明确，否则我不动）
| # | 问题 | 选项 |
|---|---|---|
| 4.1 | 集成范围 | A. 只 `study.patch`　B. `study.patch` + `host-loop.patch`　C. 暂不集成，只完善补丁与 review 材料 |
| 4.2 | 目标基线 | 针对候选源码 `1d814cf` 做 `git apply --check` 并修正冲突？还是只保持"供人 review 的 diff" |
| 4.3 | 冻结二进制怎么办 | 承认当前测试部署只是临时手段，写入 handoff 作为已知限制？还是另开编译验证 |

---

## 4. Stage 5：真实语音 / 听感 / 打断

**【需你在场】** — 麦克风、扬声器、打断时机都无法由我独立完成。

本轮我能做的只有前置（**【自主】**，可与前面并行）：
- 5.1 核对 ASR/TTS 配置与连通性（不发声、不收麦）
- 5.2 确认打断所需的事件通路在日志里存在
- 5.3 写好你在场时的验收脚本与判据，你回来直接跑

真实验收等你到场再做。

---

## 5. 收尾

| # | 动作 | 类型 |
|---|---|---|
| 6.1 | 更新 `docs/neko-handoff-2026-10-08-goal-wip.md`：Stage 1 已关闭、Stage 2 根因、id 24/29/33 的归属修正 | **【自主】** |
| 6.2 | 更新 README 的剩余验收清单 | **【自主】** |
| 6.3 | 桌面状态复原（WorkBuddy 窗口已还原，输入控制已交回） | **已完成** |
| 6.4 | **commit / push** | **【红线，需你明确指令】** 当前零提交，GitHub 不含本轮成果 |

---

## 我建议的 goal 措辞（你可整段采用或改）

> 继续 N.E.K.O 验收收尾，基于 `docs/neko-goal-plan-2026-10-08.md`。
> 自主完成 2.2/2.3/2.4、Stage 3（严格 6–8 条，采集前增量另存 DB 快照，结束后核对记录只增不减）、5.1–5.3 前置、6.1/6.2 文档更新。
> 授权 2.1（重启 pid 3812，短暂中断后端）。
> Stage 4 选【__】，Stage 5 真实语音等你到场。
> 全程：不 commit/push、不读不输出 API key、不用初始全量备份覆盖数据库、
> 重启前证明 PID/路径归属、桌面操作后复原并交还输入控制。

需要你填的只有 Stage 4 的选项（4.1/4.2/4.3）和是否授权 2.1。
