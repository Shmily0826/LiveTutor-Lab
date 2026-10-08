# N.E.K.O 验收 Handoff (End of Day 2026-10-08)

> 写给下一个接手的 agent。自包含: 不依赖本文件之外的对话上下文。
> 前置文档 (同目录): `neko-acceptance-2026-10-08.md` (四轮验收全文, 事实基准),
> `neko-handoff-2026-10-08.md` (早间 handoff, 含更早的发现与坑),
> `neko-windows-native-reality-check.md` (上轮 verdict)。

---

## 1. Mission 与验收问题

LiveTutor-Lab (`D:/CODE/project/LiveTutor-Lab`, GitHub 私有仓
`Shmily0826/LiveTutor-Lab`) 是选型实验室。已定: 主线留在 LiveTutor base
(Option A), N.E.K.O 作为 candidate 做"能否日常实时带学"的验收。
验收四问:

1. **Q1** 能否支撑日常实时带学?
2. **Q2** 核心质量如何 (core 缺陷 vs 集成/配置问题)?
3. **Q3** 若采用, 值得开发什么?
4. **Q4** 下一轮 Goal 是什么?

**当前答案 (v3, 截至本 handoff):**
Q1 **未就绪** —— 语义路由/截图桥/宠物聊天(唤醒态)三项 PASS,
但 awareness 挂死 + 语音未配两根柱子断了。Q2 核心不坏, 问题集中在
集成与配置层。Q3 见 §5。Q4 见 §6。

## 2. 环境事实 (接手必读)

**N.E.K.O 应用**
- Windows Electron 应用, 窗口名 `Project N.E.K.O.`; 宠物 = 全屏透明
  TOPMOST 覆盖层上的 Live2D 猫 (YUI)
- 数据目录: `C:/Users/Shmily/AppData/Roaming/N.E.K.O/`
  (日志 `neko-electron-debug.log`, UTC 时间, +13=本地)
- 端口: 48911 = 后端 FastAPI (340 routes, `/openapi.json`),
  48916 = plugin runs API (93 routes)。**CSRF**: 所有写操作需
  `X-CSRF-Token` (Electron 注入, 无发放端点) → 程序化聊天 POST 不可行,
  UI 交互只能走桌面控制
- Study Companion 插件: SQLite `study_companion.db`; **配置真源 = DB kv
  行 key='config'**, 启动时 `_persist_state()` 会把 DB 写回并压过一切
  toml/API 路径 (见 acceptance R2.1 五路径表)
- ASR registry 已有本地 faster_whisper; 深度seek provider 无独立 ASR

**宠物聊天 UI (已验证的交互链)**
- 点击宠物 (物理坐标 2724,692) → 输入气泡 → 点击输入框 (2460,677) →
  剪贴板粘贴 → Enter
- **陷阱 1**: 回复默认收起, 只显示输入框顶部蓝色小横杠把手, 点它才展开
  聊天面板 (官方新手教程有写, App 内 seven-day-tutorial)
- **陷阱 2**: 面板展开后首次 click+paste+Enter 可能不送达; 正确姿势 =
  粘贴后先截图验证文字在框内 (出现蓝色猫爪发送按钮) 再 Enter
- **陷阱 3**: 猫挂机自动睡觉 (by design 沉浸设计); 睡觉态回复全是
  "喵 zzZ" 梦呓模板, 无任何"我睡着了"提示; **点击猫即唤醒**, 唤醒态
  记忆与算术正常 (实测 47/150 全对, 含计算链)

**桌面控制工具链**
- gui.py: `C:/Users/Shmily/.workbuddy/skills/windows-desktop-control/scripts/gui.py`
- python: `C:/Users/Shmily/.workbuddy/binaries/python/envs/default/Scripts/python.exe`
- 子命令: `click x y` / `paste text` / `key enter` / `crop x1 y1 x2 y2 [out]`
- DPI: 物理 2880×1800 @ 200%; 中文必须走 paste (pyautogui.write 不支持)
- 避开 (0,0) (pyautogui FAILSAFE)

**沙箱坑 (踩过的)**
- Bash 工具链式命令含中文参数会被沙箱拦
  ("cmd decisionRecord missing actual resource subject") → 把多步操作写成
  python 脚本文件再单条执行 (参考 `scripts/neko_ui_multiturn.py`,
  `neko_burst_shots.py`)
- Agent 工具调用的子进程在调用结束被收割 → 长活 GUI 进程只能用户手动启动
- urllib 访问本地端口需 `ProxyHandler({})` 绕系统代理

## 3. 已完成 (四轮验收, 全部证据在 benchmarks/raw/evidence/ — gitignored)

| 轮次 | 内容 | 关键结论 |
|---|---|---|
| R1 14:30 | deepseek 接入 + 语义路由/截图桥/OCR 复测 | 语义路由 `routing_unavailable`→`available`, 延迟降至 1/6-1/10; 截图桥 PASS (上轮 CORE GAP 是无头桌面假象); 数学题命中知识条目; **所有 CONFIG 级项转 PASS, 不需要写任何 extension** |
| R2 15:00 | awareness 管道五路径 + 语音 CONFIG + CSRF | awareness 启用唯一有效路径 = 停机改 DB kv 行 (toml/API 全被 DB 压过); 启用后**静默挂死零 tick**: message plane 每启动必故障 (26 次/日) + awareness tick 无超时; awareness 用 capture_lightweight **不用 OCR**; 语音三层 CONFIG 定位 (见 §5); CSRF 完整是加分项 |
| R3 16:15 | 桌面控制代测三轮对话 | UI 链路打通 (含两个陷阱); 睡觉态三轮全梦呓, 误判 GAP; 发现 assistant agent 4 分钟 unresponsive→crashed→recover 循环 (openfang daemon unreachable, 属桌面 agent 能力, 与宠物聊天无关) |
| R4 16:36 | 唤醒态复核 (用户实测) | 47 与 150 全对含计算链 → **宠物聊天记忆连续性 PASS (唤醒态)**; 睡眠=渲染层状态机, 后端 340 路由无开关、日志零记录; 睡觉无提示记为小可用性 GAP |

**GitHub (17:13-17:17):** 私有仓已建, SSH remote, 本地与 origin 完全同步
(HEAD = c9a7414, 7 commits)。推送前安全检查已做: `candidates/` (N.E.K.O
第三方源码) 与 `benchmarks/raw/` (含桌面截图) 均 gitignored; 脚本无硬编码
密钥 (`neko_set_deepseek.py` 从本地密钥文件读, 只打码)。

## 4. 还差什么 (三大项 + 一小项)

1. **B. Study 模式带学全链路验证** (未开始) — 验收的最后一环:
   用户开着真实学习材料学习 5-10 分钟, Study Companion 真实带学,
   取证 study_ocr_snapshot 触发/讲解延迟/知识条目命中/内容质量,
   然后共同判定"体验是否撑得起日常带学"
2. **A. 语音三层配置** (未开始, 全是 CONFIG):
   - `microphone_id=null` → 需在 App UI 选麦克风 (AI 可代点)
   - ASR: deepseek 无独立 ASR → 推荐走本地 faster_whisper (registry 已有),
     不必换 provider
   - `ttsProvider` 空 → doubao/elevenlabs/gptsovits 槽位选一家, 可能需
     用户注册拿 key
3. **C. awareness 修复立项** (未立项, **必须用户批准才动 core**):
   三个修复点 = message plane 启动硬失败/重试、awareness tick 超时降级、
   配置管道贯通 (让覆盖 toml 或 hot-update 真正到达插件)
4. 小项: 睡觉态 UI 加"Zzz"提示 (外部产品只能建议, 不归我们改)

## 5. Q3 值得开发清单 (若采用 N.E.K.O)

按优先级:
1. message plane 健壮性 + awareness 超时降级 + 配置管道贯通 (C 项, 集成级,
   解锁"感知式主动辅导"的唯一路径)
2. 睡觉态 UI 提示 (低优先级体验项)
3. ~~宠物聊天接入宿主历史~~ (R4 撤回 — 唤醒态实测历史连续性正常)
4. ~~写 extension 补能力~~ (R1 撤回 — CONFIG 全通后一个都不需要)

## 6. 建议下一步 (给接手 agent 的行动序)

| 步 | 动作 | 谁 | 耗时 |
|---|---|---|---|
| B1 | 用户开真实学习材料 (如 COMPSCI 701 slides) 正常学习几分钟 | 用户 | 5-10 min |
| B2 | 并行取证: study_ocr_snapshot 状态、讲解延迟、知识命中 (GET 端点 + 插件日志) | AI | 并行 |
| B3 | 共同评估体验 → **决定 C 是否立项** | 一起 | 10 min |
| A1 | AI 代点 UI 选麦克风 | AI | 5 min |
| A2 | 配置本地 faster_whisper 为 ASR | AI | 15 min |
| A3 | 用户选 TTS provider + 提供 key → AI 代点配置 | 用户+AI | 20-40 min |

**为什么先 B 后 C**: C 要动 core 成本最高; B/A 零代码先把体验证据拿全。
若 B 跑下来 Study 模式已够用, C 可降级为"不修, 绕着用"。

## 7. 工作纪律 (用户明确要求过)

- **先讨论再动手**: 方案/策略先口头确认, 未批准不动代码不执行命令
- **动 core 或改配置前必须问**; 验证类操作尽可能自主完成
- **不读取/输出/传播任何 API key**; 证据文件脱敏
- 推送前必查: gitignored 敏感面 + 脚本无硬编码密钥; push 走 SSH
  (HTTPS push/fetch 均失败)
- 代测/使用 N.E.K.O 前先确认**宠物唤醒状态**
- 测试期间用户可能在工作: 桌面控制前告知, 结束后归还鼠标键盘
- 日常短指令推进 ("开始吧/继续吧"); 完成后总结改动

## 8. 快速索引

- 验收全文: `docs/neko-acceptance-2026-10-08.md` (R1-R4, 最权威)
- 测试脚本: `scripts/neko_*.py` (probe2-6 = awareness 管道实验;
  ui_multiturn/burst_shots = 桌面控制代测)
- 运行时取证模式: GET `http://127.0.0.1:48911/api/study_runtime` 类端点
  (urllib + ProxyHandler({})), 插件日志在 neko-store 目录
- 用户环境: Windows, 用户名 Shmily, GitHub = Shmily0826 (SSH 已配,
  gh CLI 已登录); 学生, 中文交流, 技术术语保留英文
