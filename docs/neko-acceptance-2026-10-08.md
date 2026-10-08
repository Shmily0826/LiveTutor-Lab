# N.E.K.O Native Tutor 验收报告 (Final Reality Check)

日期: 2026-10-08 14:30
前置文档: `docs/neko-windows-native-reality-check.md` (上轮 verdict 与能力矩阵)
`docs/neko-handoff-2026-10-08.md` (交接, 含三个关键发现与沙箱坑)

本轮目标: 把 N.E.K.O + Study Companion 推进到真正可用于日常实时学习辅导,
并回答四个验收问题。全程只动配置, 零代码改动, 零 core 改造。

---

## 0. 本轮做了什么

1. 把 ASSIST provider 从 `free` 切到 `deepseek` (用户提供的本地密钥文件,
   脚本内读取并直接 POST 给后端, 密钥从未被打印或写入任何日志)
2. 重跑语义路由与延迟基线对比
3. 真实桌面上复测截图桥
4. 真实屏幕上的 OCR 接地 + 多轮教学测试
5. 测量 OCR 热启动延迟
6. 核对 Strong Model (凝神) 机制与 OpenFang 状态

脚本: `scripts/neko_set_deepseek.py`, `neko_semantic_retest.py`, `neko_screen_multiturn.py`
证据: `benchmarks/raw/evidence/study-runtime5-deepseek.txt`,
`study-runtime6-screen-multiturn.txt`, `retest-stdout.txt`, `multiturn-stdout.txt`

---

## 1. 核心结果: 换上 DeepSeek 后, 语义路由从"全坏"变"全好"

| 指标 | free 基线 (上午) | deepseek (本轮) |
|---|---|---|
| `study_semantic_status` | `routing_unavailable` | **`available`** |
| `study_semantic_reason` | `invalid_response` | 空 (无错误) |
| `study_semantic_intent` | `unknown` | 具体意图, 如 `explain extremum criterion using second derivative` |
| `study_semantic_subject` | `unknown` | `computer_science` / `math` |
| `study_semantic_content_type` | `unknown` | `calculus concept` / `Docker concept review notes` |
| `knowledge_guidance_applied` | `false` | **`true`** (数学题命中知识条目 `college_convavity_inflection` 凹凸性与拐点) |
| 延迟 (Flutter 概念题) | 31,412 ms | **5,261 ms** |
| 延迟 (数学题) | 33,570 ms | **3,379 ms** |
| `degraded` | - | `false` |

延迟降到原来的 **1/6 到 1/10**。

根因确认: 上轮在 `brain/computer_use.py:1030-1038` 找到的注释
("free-agent-model 会返回 choices 非空但 message=None") 是正确解释。
免费中转给不出语义路由要解析的结构化输出, 不是路由代码坏了。

**文档里所有 CONFIG 等级项, 换 provider 后全部转 PASS。**
上轮 verdict "Native N.E.K.O + small Study Companion extensions" 里的"extension"
部分, 目前实测**一个都不需要写**。

---

## 2. 截图桥: 上轮的 CORE GAP 是环境假象, 实际 PASS

| 上轮 (无交互桌面) | 本轮 (用户真实桌面) |
|---|---|
| `/api/capture/health` -> 503 `no_renderer` | **`/api/capture/health` -> 200 `{"success":true,"available":true}`** |

判定逻辑在 `main_routers/capture_router.py:62-70`: 只要 `capture_bridge.has_capture_client()`
为真就 200。上轮失败是因为我的会话没有交互桌面, 渲染器无法注册。
**这不是 core 缺口, 是测试环境假象, 已从 CORE GAP 降级为 PASS。**

附带收获: 屏幕接地现在有两条路, OCR 路径和 capture bridge 路径, 互为冗余。

---

## 3. 屏幕接地多轮教学: 讲解非常好, 连续性有明确边界

实测流程 (用户的真实屏幕, 当时显示的是 WorkBuddy 里的 Docker 笔记):

### 3.1 OCR 快照, 31.3 s

- `status=ok`, 读到 1,118 字符真实屏幕文本
- 屏幕分类: `screen_type=question`, `confidence=0.98`
  (信号: `question_score=4.8`, `review_score=2.15`, 命中 "how"/"题"/"回顾"/"说明")

### 3.2 空文本提问 (回退到 `last_ocr_text`), 5.2 s

回复是一份结构化的 Docker 概念梳理, 覆盖 Dockerfile / Image / Registry / Container,
并且**明确引用了屏幕上看到的英文原句** "contains instructions for building an image"。
语义路由给出意图 `review and consolidate Docker terminology for exam preparation`,
主题 `computer_science`, 内容类型 `Docker concept review notes`。
这是真正的屏幕接地, 不是通用百科回答。

### 3.3 追问依赖上一轮, 3.4 s, **失败, 但失败得体面**

我追问"就你刚才回答里提到的那个要点, 给我出一个练习题"。回复:

> 你指的应该是刚才提到的要点, 但我这边没有保留"上一轮具体内容",
> 所以不能凭空确定是哪个要点, 也不能硬编一道题。

语义路由同步标出 `study_semantic_status=low_confidence`,
`study_semantic_content_type=unresolved reference request`。

**根因 (源码确认):** `study_explain_text(self, text="", vision_image_base64="", **kwargs)`
签名里**没有任何 history / context 参数**
(`entry_tutor_explain_entries.py:170-171`)。这个入口本来就是单轮设计,
跨调用的连续性由宿主聊天循环负责 (配置里 `history_limit: 50` 属于宿主大脑)。

**分类: 不是缺陷, 是我直接打插件入口绕过了宿主。** 但这意味着
"多轮连续辅导"这条必须在真实聊天 UI 里验证才算数, 本轮无法替代。
标 **UNVERIFIED (需要 UI 级验证)**, 不标 PASS 也不标 GAP。

### 3.4 OCR 热启动延迟: 23 到 25 s, 这是一个真实的实用性问题

| 运行 | 延迟 | 读到字符 |
|---|---|---|
| 首次 | 31,315 ms | 1,118 |
| 热启动 1 | 25,293 ms | 871 |
| 热启动 2 | 23,372 ms | 871 |

不是冷启动模型加载, 是稳定成本。影响: 配置里 `awareness.snapshot_interval_seconds: 5`,
即 awareness (持续屏幕理解) 想每 5 秒采一次样, 但单次全屏 OCR 要 23 到 31 秒,
**根本跟不上**。awareness 默认是关的 (`study.awareness.enabled=false`), 现在知道为什么了。

这是本轮发现的**最值得动手的一个点**, 见第 6 节。

---

## 4. 其余两项核实

### Strong Model (凝神)

`config/focus_settings.py:59` `FOCUS_MODE_ENABLED = True`, 默认开启。
机制: 信号触发、用户无感的"这一轮开思考 + 换强模型", 用 leaky 累加器
(`FOCUS_CHARGE_RETENTION=0.5`) 而不是连续 K 轮低分。
它的"强模型"就是各模型槽位, 现在全部跟着 `deepseek-flash` 走, 无需额外配置。

### OpenFang (50051)

独立体系, 启动日志明说: `Primary LLM driver init failed ... Missing API key:
Set ANTHROPIC_API_KEY`, `No LLM drivers available`。与 Study Companion 无关,
不改, 留给用户决定要不要喂 key。

---

## 5. 四个验收问题的回答

### Q1: N.E.K.O 现在是否已经适合日常实时带学?

**文本和屏幕路径: 接近可用。** 讲解质量高、结构清晰、引用屏幕真实内容,
延迟 3 到 5 秒在对话节奏里可接受, 语义路由准确到能区分 CS 和数学并命中知识条目,
判分和掌握度回写上轮已验证。

**整体"日常实时带学": 还不能下最终结论**, 卡在两件事:
- 语音对话与打断 **UNVERIFIED**, 没测就不能说"实时"
- 多轮连续性只在插件入口层测过 (无状态), 真实聊天循环没测

不推断, 不提前判 PASS。

### Q2: 还存在什么真正影响使用的障碍?

| 障碍 | 性质 | 影响 |
|---|---|---|
| 语音 + 打断未验证 | 验证缺口 | "实时"二字成立的唯一前提, 无法绕过 |
| 全屏 OCR 23-31 s | 性能 | awareness 的 5 秒采样节拍完全跟不上, 持续屏幕理解不可行 |
| explain 入口无状态 | 设计 | 单打插件时没有连续性; 真实路径靠宿主, 需 UI 验证 |
| OpenFang 无 LLM key | 配置 | 不影响 Study Companion, 是另一个产品面 |

### Q3: 哪些靠原生配置解决, 哪些值得开发?

**本轮靠纯配置解决的 (零代码):**
- 语义路由 / 知识引导 / Strong Model 槽位: 换 `deepseek` provider
- 截图桥: 换到真实桌面即恢复, 环境假象
- 上一轮遗留的全部 CONFIG 项

**值得开发的 (按价值排序, 全部是插件级, 不动 core):**
1. **OCR 提速**, 插件级。方向: 区域裁剪 (只截活动窗口而非全屏)、降采样、
   或把 OCR 换成 capture bridge 的截图喂给有视觉能力的模型
   (`llm_vision_enabled` 现在是 `false`, DeepSeek 官方有 vision 型号)。
   这是"持续屏幕理解"能不能成立的关键
2. **把连续性接到插件入口**, 仅当 UI 级验证确认宿主循环也没接上时才做

**明确不值得做的:**
- 修语义路由 (已好), 修截图桥 (已好), 建 Tutor Brain (上轮 verdict 已否决),
  动 core (没有任何证据指向 core)

### Q4: 下一轮最有价值的工程 Goal

**"验证实时性: 语音 + 打断 + UI 级多轮"**

一句话: 把最后两个 UNVERIFIED 变成 PASS 或 GAP, 顺带量 OCR 在真实使用里的
实际节拍。这一轮之后, "N.E.K.O 是否适合日常实时带学"才能从"接近可用"
变成可签字的结论。

具体内容:
1. 用户在场、环境允许出声的前提下, 测语音对话、打断 (barge-in)、恢复
2. 在真实聊天窗口里连问三轮相关问题, 验证宿主是否携带历史
3. 顺手测 awareness 打开后的实际行为 (采样节拍 vs OCR 延迟)
4. 若 OCR 延迟确认是瓶颈, 那时的工程任务就是上面第 3 节的第 1 条

---

## 6. 与上轮 verdict 的关系

上轮 verdict: **Native N.E.K.O + small Study Companion extensions**

本轮的修正: 上轮列的 CONFIG 项全部转 PASS, 截图桥从 CORE GAP 转 PASS,
所以"small Study Companion extensions"的清单**缩短到了一项候选** (OCR 提速),
而且这一项是否成立还要看下一轮 UI 级验证的结果。

verdict 本身不变, 但离"原生几乎全够用"更近了一步。

---

## 7. 遗留与说明

- 密钥处理: 本轮脚本在进程内读取 `D:\CODE\API\new api.txt` 并 POST 给后端,
  密钥从未打印、从未写入日志或文档。后端 GET 返回的是掩码形态
  (`__NEKO...ED__`), 说明 N.E.K.O 自己做了脱敏存储
- 上轮遗留的 `legacy_cleanup_pending: true` 存储提示仍未消, 不阻塞任何功能
- 上轮误标的两个 SKIPPED (判分/定向追问) 已在本轮与上轮之间纠正,
  是我方取 ID 的 bug, 不是产品缺口
- 本报告与 `neko-windows-native-reality-check.md` 并存, 后者保留作上轮基线

---

# 第二轮 (2026-10-08 15:00-15:50): awareness 深挖 + 语音前置 + 聊天 API 面

执行的是上轮 Q4 计划的第 3 项 (awareness 实际行为) 与第 1/2 项的前置侦察。
全程仍零代码改动; 涉及的配置/DB 修改全部现场回滚并有备份。

## R2.1 awareness: 五条启用路径逐一实测, 只有 DB kv 行有效

上轮用 `study_update_settings_config {"awareness": {...}}` 被静默忽略。
本轮源码定位 + 五条路径实测:

| # | 路径 | 结果 | 证据 |
|---|---|---|---|
| 1 | settings 入口 | 无效: `_apply_settings_config` (entry_status_entries.py:87-147) 根本没有 awareness 分支 | 源码 |
| 2 | `PUT /plugin/{id}/config` + reload | 无效: 写入覆盖 toml (`neko-store/.../config/plugin.toml`, mtime 证实), GET 合并视图变 True, 但**运行时 echo 仍 False** | study-runtime8 |
| 3 | PUT + stop/start | 同上, 运行时 False; **插件进程启动只读 base toml, 覆盖文件到不了它** | probe3-stdout |
| 4 | `config/hot-update` temporary | 200 `"hot_reloaded":true, "handler_called":false` 但运行时 `_cfg` 不变; permanent 模式持久化**未实现** (exe 字符串: "permanent mode persistence is not implemented") | probe3-stdout |
| 5 | 改 base toml (内置 plugin.toml 第 58 行) + 重启 | **仍无效** — 因为启动序列是 `toml dump -> store.load_config`, **DB kv 行永远压过一切 toml** | study-runtime9 |
| 6 | **直接改 DB kv 行** (`study_companion.db` kv 表 key='config', 停机状态下改, 与插件自身的 save_config 同一写法) | **有效**: 运行时 echo `awareness.enabled=True` 首次为真 | study-runtime10 |

根因链 (源码): `startup()` 里 `self._persist_state()` 每次启动都把完整 cfg
(含 `awareness.enabled=False`) 写回 DB; `store.load_config` (store.py:540-546)
再把 DB 行合并到 toml 之上。所以 DB 行永远是最终赢家, 用户能碰到的一切
toml/覆盖/API 途径都是摆设。**这是配置管道的集成缺陷**, 不是用户配置问题。

## R2.2 启用之后: 循环静默挂死, 零 tick

DB 行启用成功后观测 330 s (覆盖 300 s 的 push 间隔):

- `recent_classifications` 冻结在 4, `last_activity_at` 恒 0.0
- `sensor_available=False` (supervision.observe_activity 从未被调用过,
  因为 `_sensor_available` 只在该函数内赋值)
- `/plugin/messages` 零推送 (300 s push 间隔已过)
- 插件日志零条 awareness 相关行 (既无失败也无跳过警告)

**重要更正 (推翻本报告 §3.4 的推断):** awareness 不用全屏 OCR。
`awareness_tick` 走 `capture_lightweight` (study_ocr_pipeline.py:228):
全屏截图 + 缩略图 + phash + 窗口标题, **没有 OCR**。
所以"OCR 23-25 s 跟不上 5 s 采样"这个理由是错的——OCR 提速与 awareness 无关。
真正的死因在别处:

插件日志显示 **host<->plugin 消息总线 (message plane) 今天 26 次故障,
每次启动必现**: `failed to subscribe neko.study_command via messages bus:
message_plane bus.get_recent timed out after 5.0s` + `message-plane transport
unavailable`。awareness 第一个 tick 要经同一总线 `get_os_activity_snapshot`
取 OS 信号, 该路径**没有超时** (超时逻辑只包在 startup 的 subscribe 里),
总线不通时第一次 await 就永久挂起——与全部观测吻合 (零失败日志, 因为
根本不是异常, 是挂起)。

**分类: PLUGIN GAP (集成级)。** 修复方向 (未来工程 Goal, 不在本轮做):
1. message plane 的 subscribe 失败要在启动时硬失败或重试, 而不是带病运行
2. awareness tick 的 OS 信号读取要有超时 + 降级 (跳过 OS 信号只留截图)
3. 配置管道: 让覆盖 toml 或 hot-update 真正到达插件进程, 或文档化
   "唯一改法是 DB"

回滚确认: kv 行还原, 运行时 echo False, REVERT OK。备份:
`study_companion.db.bak-awareness*`, `study_companion.kv-config-row.bak.json`。

## R2.3 语音: 三层 CONFIG 阻塞, 全部定位

| 项 | 现值 | 含义 |
|---|---|---|
| `microphone_id` | `null` (`/api/characters/get_microphone`) | 没选麦克风, 需在 App UI 里选 |
| `supportsIndependentAsr` | `false` (deepseek profile) | 当前 provider 不带独立 ASR; 要么换 ASR-capable provider, 要么走本地 faster_whisper (registry 里有) |
| `ttsProvider` | 空 | 没配 TTS 音色 (doubao/elevenlabs/gptsovits 等槽位全空) |

另有 `independentAsrEnabled=false`, `noiseReductionEnabled=true`,
`userLanguage=en`, 所有 proactive 开关全关 (测试时不会被主动搭话干扰)。
**语音 = CONFIG, 不是核心缺陷**, 但每一项都要用户在 UI 里点, AI 不可代劳。

## R2.4 聊天 API 面: CSRF 防护完整, 聊天 POST 必须用户来

`POST /api/card-assist/chat` 描述即 "Persistent companion-style chat ...
sees the current card + conversation history" — 宿主聊天循环确有历史,
这正是上轮 §3.3 说的"连续性由宿主负责"的宿主本体。

但该端点强制 CSRF (`X-CSRF-Token`, Electron 注入后端环境, 无发放端点;
Origin/Referer 回退不可用, 403 + 后端日志记录拒绝)。
**这是加分项: 本地 API 面的写操作防护是完整的。**
副作用: 三轮连续对话只能由用户在真实聊天窗口完成 (AI 无法代发)。

## R2.5 对四个验收问题的增量修正

- **Q1** 不变: 仍卡语音 + UI 多轮两项 UNVERIFIED
- **Q2** 表格修正: 删去"OCR 23-31 s 导致 awareness 不可行" (理由错误,
  awareness 不用 OCR), 替换为 **"awareness 启用管道 + message plane 挂死"
  (PLUGIN GAP, 集成级)**; OCR 提速降级为 study_ocr_snapshot 自身体验问题
  (23-31 s 出一次讲解仍然慢, 但不阻塞任何已声明功能)
- **Q3** 修正: "值得开发"清单第 1 项从"OCR 提速"改为
  **"message plane 健壮性 + awareness 超时降级 + 配置管道贯通"**;
  OCR 提速移为可选体验优化
- **Q4** 下一轮 Goal 内容不变 (语音 + 打断 + UI 三连问), 前置侦察已完成:
  语音需用户在 UI 选麦克风 (+ 视情况配 ASR/TTS), 三连问由用户在聊天窗口发,
  AI 负责事后的日志/状态取证

## R2.6 本轮产物

- 脚本: `scripts/neko_awareness_probe2.py` (config API + reload),
  `neko_awareness_probe3.py` (stop/start + hot-update),
  `neko_awareness_probe4.py` (base toml), `neko_awareness_probe5.py` (DB kv),
  `neko_awareness_probe6.py` (330 s 节奏观测)
- 证据: `benchmarks/raw/evidence/study-runtime8/9/10/11-*.txt`,
  `awareness-probe3/4/5/6-stdout.txt`,
  `study_companion.plugin.toml.bak-awareness`,
  `study_companion.db.bak-awareness*`, `study_companion.kv-config-row.bak.json`
- 全部现场状态已回滚 (awareness=False, 插件运行中, 用户 App 未受影响)

---

# 第三轮 (2026-10-08 16:15-16:40): 桌面控制代测 UI 三轮对话

## R3.0 方法: AI 代测获得用户批准

R2.4 结论"三轮连续对话只能由用户在真实聊天窗口完成"被用户推翻:
用户选择"我来代测"方案 —— AI 用 windows-desktop-control 接管鼠标键盘约几分钟,
替用户在真实 N.E.K.O 宠物聊天窗口逐句发送 (期间用户不碰鼠标键盘)。
本轮零代码改动 (仅新增测试脚本), 全部操作走真实 UI, 无 API 绕过。

## R3.1 UI 交互链路 (打通 + 两个陷阱)

链路: 点击宠物 (物理坐标 2724,692) -> 弹出输入气泡 (placeholder
"Press Enter to send, Shift+Enter for new line") -> 点击输入框 (2460,677)
-> 剪贴板粘贴中文 -> Enter。paste 返回 `{"pasted":"...","length":N}` 确认文本入框。

**陷阱 1: 回复默认收起。** 回复气泡不直接显示, 只在输入框顶部中间渲染一个
蓝色小横杠把手, 点击把手才展开完整聊天面板 (用户提示, 出自官方新手教程;
AI 文档审查未覆盖此交互, 三轮 t=6/11/19s 三连拍全部"未见回复"即此原因)。

**陷阱 2: 展开态焦点。** 聊天面板展开后, 首次 click+paste+Enter 消息未送达
(面板无新气泡, 输入框仍空)。正确姿势: 点击输入框 -> paste -> **截图验证文字
已在框内且出现蓝色猫爪发送按钮** -> Enter。二次执行成功送达。

## R3.2 三轮对话结果 (YUI 宠物快捷聊天)

| # | 消息 | 发送 | YUI 回复 | 期望 | 判定 |
|---|---|---|---|---|---|
| 1 | "记住一个数字：47，等下考你" | ~16:2x | "喵……。（´ｏ｀）zzZ" | 确认记忆 | 卖萌, 无确认 |
| 2 | "我刚才让你记住的数字是多少？" | 04:26 PM | "喵。（´ρ｀）zzZ" | 47 | **未答** |
| 3 | "把那个数字乘以 3 再加 9，等于多少？" | 04:32 PM | "喵……(ω｀)zzZ" | 150 | **未答** |

消息 2 回复延迟 <60s (同分钟), 消息 3 在 Enter 后 t<=4s 已渲染。
三轮中 YUI 始终睡觉状态 (zzZ 系列), 未表现出对 "47" 的任何记忆, 未执行算术。

## R3.3 判定: 宠物快捷聊天记忆连续性 = GAP
> **[R4 修正] 本节判定被 R4 唤醒态复核推翻: 睡觉是挂机自动触发的沉浸设计,
> 唤醒后记忆连续性 PASS (47 与 150 均答对, 含计算过程)。见 R4。**

- 宿主聊天循环 (`/api/card-assist/chat`, 带 Persistent conversation history)
  与宠物快捷聊天**不是同一通道**; 宠物聊天实测**无学习类指令的连续性**。
- "喵"是 LLM 生成还是睡觉状态本地模板: **UNVERIFIED**
  (electron 日志无 LLM 调用痕迹; 猫全程睡觉 zzZ, 合理假设睡觉=梦呓模板,
  唤醒后行为可能不同 —— 留给下一轮唤醒态重测)。
- 生成延迟 (t<=4s) 与 deepseek 3-5s 量级吻合, 但不构成 LLM 证据。

## R3.4 日志证据: assistant agent 4 分钟崩溃-恢复循环

`AppData/Roaming/N.E.K.O/neko-electron-debug.log` (UTC, +13=本地):
16:19/16:23/16:27 三轮 `Agent is unresponsive (inactive_secs=210,
timeout_secs=180)` -> `marked as Crashed` -> `Auto-recovering (attempt 1/3)`
-> `recovered`。**测试全程 assistant agent 处于 4 分钟周期崩溃-恢复循环**,
与 R2.2 message plane 每启动必故障 (26 次/日) 同属宿主稳定性问题。
另: `[CompactChatBall] click forwarded to react chat` 证实宠物聊天球
点击转发给 React 聊天层; social-sse 未配置 (无害)。

## R3.5 四个验收问题 (最终状态)

- **Q1 能否日常实时带学: 否, 未就绪。** 语义路由/截图桥 PASS,
  但四根柱子断了三根: awareness 启用管道断+挂死 (R2.2, PLUGIN GAP),
  宠物聊天无学习连续性 (R3.3, GAP), 语音三层 CONFIG 未配 (R2.3, 需用户);
  外加宿主稳定性两条 (message plane 每日 26 故障, agent 4 分钟崩溃循环)。
- **Q2 核心质量**: 新增 GAP 一条 —— 宠物快捷聊天退化为睡觉模板
  (是否 by design 待唤醒态重测判别); 撤回 R2.4 "三轮只能用户来"的表述
  (桌面控制可代测)。
- **Q3 值得开发清单**: 在 R2.5-Q3 基础上追加
  **"宠物聊天接入宿主会话历史, 或明确其纯陪伴定位"**;
  前置: assistant agent 崩溃循环修复 (它与 message plane 可能同根因)。
- **Q4 下一轮 Goal**: ①语音 (用户 UI 选麦克风 + 视情况配 ASR/TTS, AI 代点);
  ②唤醒态宠物聊天重测 (先摸清唤醒交互); ③Study 模式带学全链路;
  ④UI 三连问在宿主主聊天入口重测 (若找到入口)。

## R3.6 本轮产物

- 脚本: `scripts/neko_ui_multiturn.py` (发消息+三连拍),
  `scripts/neko_burst_shots.py` (纯三连拍)
- 证据: `benchmarks/raw/evidence/ui-chat-3-msg1-sent.png` 至
  `ui-chat-11-msg3b-t17.png` (10 张, 含发送回执/把手/展开面板/三轮回复),
  `ui-chat-6-fullscreen.png` (全屏拓扑: 宠物+输入气泡悬浮于 WorkBuddy 上方)
- 未回滚项: 无 (零配置改动; 鼠标键盘控制权已交还用户)

---

# 第四轮 (2026-10-08 16:36-16:45): 唤醒态复核 —— 判定反转

## R4.1 用户实测: 唤醒后记忆全部答对

用户指出猫是**挂机自动入睡** (沉浸式人设设计), 点一下即可唤醒, 并亲自重问:

| 时刻 | 消息 | YUI 回复 | 判定 |
|---|---|---|---|
| 16:35:01 | "我刚才让你记住的数字是多少" | 16:35:02 "**47。**" + "喵，这种小事还难住我。" | **PASS** |
| 16:35:20 | "把那个数字乘以 3 再加 9，等于多少" | 16:35:20 "**47乘3是141，再加9就是150。**" | **PASS** (计算链正确) |

证据: `ui-chat-12-awake-answer.png` (唤醒态完整对话 + Live2D 立绘形态)。
R3 三连拍"未答"全部源于睡觉态梦呓, 非宿主缺陷。

## R4.2 睡眠机制定位 (AI 补查)

- electron 日志: **零**睡眠/唤醒记录 (grep sleep/wake/awake/idle 仅命中
  social-sse "sleeping" 噪声) —— 睡眠状态机不落日志
- 后端 OpenAPI 340 路由: **无** sleep/idle/wake 配置端点; catgirl 路由
  全为 Live2D 模型管理 (L2D/touch_set/lighting/mmd/voice); idle 命中均为
  awareness OS 信号定义
- `GET /api/agent/state`: openfang_ready=false
  (`AGENT_OPENFANG_DAEMON_UNREACHABLE`) —— 与 R3.4 崩溃循环互证, 但属
  桌面 agent 能力, 与宠物聊天无关
- 结论: 睡眠=**渲染层行为状态机**, 配置不在后端 API 面; 官方说明位于
  App 内新手教程 (seven-day-tutorial, 用户已完成 round 1 并从中学到
  唤醒交互)。AI 的事先审查未覆盖 App 内教程/交互细节层, 属审查盲区。

## R4.3 修正后的判定

- **宠物快捷聊天记忆连续性: PASS (唤醒态)**。睡觉态梦呓 = by design,
  不是缺陷; 但**睡觉时 UI 无任何提示** (输入框 placeholder 仍是普通
  "Press Enter to send", 没有"我睡着了"标记) —— 新用户会像本轮代测一样
  误判为"答非所问/无记忆"。记 **可用性 GAP (小)**: 建议睡觉态在输入气泡
  或回复把手处加"Zzz"角标。
- 回复延迟观察: 唤醒态 16:35:01->16:35:02 即答, 时间戳为渲染时刻,
  真实 LLM 延迟被流式/异步渲染遮蔽, 不影响判定。

## R4.4 四问最终状态 (v3)

- **Q1**: 宠物聊天柱子由"断"改为**"可用 (需唤醒)"**; 剩余断柱:
  awareness (R2.2 PLUGIN GAP) + 语音 (R2.3 三层 CONFIG)。
  "日常实时带学"仍判**未就绪**, 但距离缩短: 睡觉误判问题已被理解,
  awareness 与语音仍是硬阻塞。
- **Q2**: 宠物聊天退化为模板一条撤回, 改记睡觉态无提示可用性小 GAP。
- **Q3**: "宠物聊天接入宿主历史"一条撤回 (实测历史连续性正常);
  保留 message plane/awareness/配置管道三项, 追加"睡觉态 UI 提示"为
  低优先级体验项。
- **Q4**: 下一轮 Goal 不变 (语音 + awareness 修复验证 + Study 模式全链路);
  增补一条操作纪律: **代测或使用前先确认宠物唤醒状态**。
