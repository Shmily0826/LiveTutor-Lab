# MEMORY.md — LiveTutor-Lab / N.E.K.O Lab 长期要点

## N.E.K.O 沙箱启动配方（最重要，可复用）
- 从沙箱启动 `benchmarks/raw/neko-app/N.E.K.O.exe` 必须同时做三件事：剥除 `ELECTRON_RUN_AS_NODE`/`NODE_OPTIONS`、`USERPROFILE=C:\Users\Shmily`、加 `--no-sandbox`（否则 STATUS_BREAKPOINT 0x80000003，Job Object 连带杀 openfang+backend）。
- 必须用**常驻后台任务**托管：`scripts/neko_lab_hold.py`（干净 env + --no-sandbox + 退出自动重启）。普通命令行结束会回收整个进程树；ShellExecuteW 方案无效。
- 手动起的后端会被 owner_supervision（parent_handle）在启动器退出后带走；桌面端拉起的后端不受影响。
- 判定进程用 `name.lower().replace('.','')` 再匹配 "neko"（`N.E.K.O.exe` 含点）。
- 本机 HTTP 必须 `ProxyHandler({})`（沙箱代理会对 127.0.0.1 回 502）；`opener.open(req, timeout=…)` 必须关键字传参。
- 完整诊断链：`scripts/neko_lab_relaunch_{clean,trace,final}.py`；详细说明在 `docs/neko-handoff-2026-10-08-goal-wip.md` §7.5。
- **holder 不跨 agent turn（2026-10-09 实测）**：`neko_lab_hold.py` 的"常驻"只在单个 turn 内成立，turn 结束会被回收并带走整棵 N.E.K.O 进程树。新会话起步先 `curl 127.0.0.1:48911/health` 探活，不通就重新 `neko_lab_hold.py 43200`（23s 内四端口就绪），再确认只有一个实例。

## Study 插件运行时启用顺序（冷启动后默认全关）
- 仅切 `user_plugin_enabled` 会被推迟（"deferred until the master switch is ON"）。
- 正确顺序：`POST 48915/agent/command {"command":"set_agent_enabled","enabled":true}` → `POST /agent/flags {"user_plugin_enabled":true}` → 48916 `/plugins` 出现 26 个插件。
- **用完必须还原**为两者 False（交接时状态）。

## 教学上下文注入：唯一接缝（2026-10-09 第二轮定案）
- **所有教学 operation 的上下文都由 `_build_learning_context` 构造**（`entry_tutor_context_support.py`）。要加/改教学上下文，改这里 + 对应 prompt 组装，不要新建记忆系统。
- **三个入口根因不同，别当同一个 bug 修**（已实测）：
  - `concept_explain` 的 prompt 只渲染 `{text}` —— 完全不消费会话历史（会话记忆靠 `llm_prompts.build_concept_recent_context` + user 模板 `{recent_context}` 注入）。
  - `question_generate`/`answer_evaluate`/`summarize_session` 走 `_build_structured_messages` → `_context_json_for_prompt`，会渲染 allowed context JSON；问题是**优先级/预算**，不是缺失。
  - `answer_evaluate` 有必需字段保护（QA 超预算直接 raise，绝不从截断前缀判分），本来健康。
- **主题优先级必须由服务端定序**（`prompt_templates.STUDY_QUESTION_GENERATE_REQUIREMENTS` 13/14）：自适应目标 > 用户材料 > `knowledge_question_params`/`knowledge_guidance`。显式材料场景要剪除跨学科 `weak_topics/due_reviews/retry_wrong_question/candidate_evidence`（`_drop_cross_subject_question_params`）。
- `STUDY_PROMPT_CONTEXT_MAX_TOKENS["summarize_session"]` 从 2000 调到 6000；summarize 渲染前必须用 `session_history`（会话内）投影掉跨会话 `history`，否则会串味（LangGraph 的 phantom-memory 同型缺陷）。
- 改动插件后同步**三个根**：LIVE=`resources/bin/plugin/plugins/study_companion`、BRIDGE=`resources/bin/plugins/study_companion`、测试源=`benchmarks/raw/goal-isolated/study_companion`；用 `diff` 校验一致，再跑 `python -m unittest scripts.test_neko_lab_regressions`（20 项）。
- **热重载不用重启 N.E.K.O**：`POST 127.0.0.1:48916/plugin/study_companion/reload`；临时改配置用 `POST .../config/hot-update` + `mode:"temporary"`（不落盘，插件进程结束即失效）。插件服务全部端点见 `48916/openapi.json`。
- **已知缺陷（未修，需用户确认"学习会话"定义）**：`qa_records.session_id` 实际写的是单次 run_id → `sessions` 表每行 `question_count=1`、`ended_at=NULL`；`interactions` 无 session_id 列且是 50 行滚动窗口（每 10 次插入裁剪一次）。完整学习历史在 `mastery_snapshots`/`wrong_questions`/`fsrs_cards`。
- **语音旁路**：插件学习事件会经 proactive bridge 触发角色回复 → 应用自身 TTS（实测一晚 51 次 `tts:free`）。夜间做 Study 验证前先 `config/hot-update` 把 `study_companion.communication.enabled=false`；**该临时覆盖不跨插件重载**，每次 `reload` 后必须重新施加。
- **Screen Grounding 实测事实（2026-10-09 第二轮）**：① 区域捕获在本构建**不可用**——`capture_backend="auto"` 只解析到 dxcam，而 dxcam 的 `grab(region=)` 需要 `cv2`；`cv2`/`mss`/`pyautogui` 都没打包，只有 PIL/numpy/dxcam/win32gui，所以全屏路径（PIL `ImageGrab`）能跑、target 路径是死路。② 已加 opt-in `capture_mode="active_window"`（`_foreground_window_target` + PIL 裁剪，route 字段 `active_window_capture_route`）。③ **窗口裁剪收益有限**：学习窗口最大化时，噪声（标签条/书签栏/地址栏/悬浮面板）在窗口**内部**，裁剪只能去掉窗口外的少量内容；本机 Chrome 需要 top_ratio≈0.13 才能去掉书签栏（≈900px 里的 110px），且是应用相关魔数。④ `config/hot-update` 对 `ocr_reader.*` 报成功但**不生效**（`handler_called: false`），改 OCR 参数要重载插件。→ 结论：走 DOM/CDP + UIA。
- **桌面观测限制**：本机 GDI 全屏抓屏返回**全黑**；Electron `PrintWindow`（`scripts/neko_lab_window_shot.py`）只能渲染局部；可靠观测要走产品自己的抓屏管道（`study_ocr_snapshot`，全屏 8–23s）。真实 Study 面板入口未定位到 → UI 链路验收仍待用户指明入口。

## Stage 2 结论（2026-10-09 定稿，2026-10-09 peer review 降级表述）
- `capture_busy` 是**机制 1：标志卡住**——「最强假设」，尚未由独立运行时探针坐实（sequence.json round2/final 各含 1 个轮间残遮罩；"标志永不释放"读自候选源码而非冻结二进制）。证据：0 遮罩空置 120s 后请求仍 0.44s 返回 409（`goal-stage2-timing.json`）。
- 后端 bug 未修：409 同时桌面仍弹全屏遮罩；`_interactive_capture_active` 只置位不释放。属 Stage 4 正式源码集成范围。
- 插件侧已修（Stage 2.3）：`entry_ocr_entries.py` 回退白名单加 `capture_busy`，三个根同步（LIVE/BRIDGE/goal-isolated）；严格模式仍硬失败；回归 15/15；端到端 run `5ddf55da…` 验证降级生效。

## 主线已从 Study 插件转到「日常学习伙伴」（2026-10-14 起，2026-10-23 复核）
- 目标 A–F 完整日常可用（语音+Study+源码讲解+出题评分+材料指示+重启接续）；阶段推进记录在 `docs/daily-companion-{contract,plan,status,blockers}-2026-10-14.md`，阶段 62/75 通过后安全暂停过。
- 10-15~10-16 三轮无人值守修复（Claude/Codex）：M1–M5、W1–W5、Codex P1–P8、Claude R1–R6，成果全在 **`codex/daily-learning-companion`** 分支（远端最新 `7927040`，2026-10-23 已推）。
- **`master` 不是最新的，但主目录现在已经切到 codex 分支**（2026-10-23 整理后）：工作区唯一的 worktree、唯一分支上下文就是 `codex/daily-learning-companion`。master 停在 `f56642f`（含 10-13 的 136 个 barge-in 平行实现 + 3 个归档 commit），与 codex 分叉 139/116 未合并，master 独有实现（barge-in）尚未并入主线。
- 仓库曾有 3 个 worktree（主目录、`.codex/worktrees/daily-companion`、Temp 里的发布 worktree），2026-10-23 已清理为 1 个。**别再创建长驻 worktree**：分支一旦被别的 worktree 占用，主目录就 `checkout` 不了，只会制造"文件是 A 版、HEAD 是 B 版"的假脏。
- `scripts/git_triage_dirty.py` 是判断"脏改动是不是假脏"的唯一可靠手段（blob hash 逐文件比对目标分支），别靠 `git status` 的行数判断风险。
- **2026-10-16 用户已拍板停止加修复**：下一步是用户按 `docs/claude-acceptance-guide.md` v3 做定向复测第 5/3/2 步（约 20 分钟），之后只修最痛的一两件（首声 7–11s、自主高亮）。
- **运行时插件链路（2026-10-23 查清，别再搞错）**：`neko_desktop_tutor_host.py:274 prepare_product_plugin()` 每次启动都把骨架树 `benchmarks/raw/neko-app/resources/bin/plugins/study_companion/`（10-10 停更）复制到 **`<store>/plugin-code/study_companion`**，**随后用 `patches/neko-study-2026-10-10-product/payload/study_companion` 覆盖全部同名文件**，最后就地改 `plugin.toml`。所以真正跑的是仓库 payload——实测 `neko-daily-companion` 的 `__init__.py`/`models.py` hash 与 payload 完全相同，**10-16 的修复会生效，复测前不需要同步骨架树**。骨架树旧只影响两件事：payload 里没有的文件会残留 10-10 版；直接测骨架的测试（`test_neko_study_summary_scope` 走 `neko_study_plugin_methods_fixture` 的 RELEASE）会假红。
- 日常启动入口 `Start-Daily-Tutor-Voice.cmd` → `scripts/neko_tutor_start.py --store neko-daily-companion --voice --study-ui --learning-surface`；额度账本实读 `benchmarks/raw/neko-desktop-egress-cap`（2026-10-16 收尾后 DeepSeek 1825/2000，Lanlan.app 146）。
- 现状快照见 `.workbuddy/memory/2026-10-23.md`。

## 红线（长期有效）
- 不 commit/push；不读/输出任何 API key；绝不用初始备份覆盖 DB（保护历史 interactions + qa_records，id 24/29/33 在 `interactions` 表）；语音验收保持静音；重启前先证明 PID/路径归属。
- 用户限定评分样本 6–8 个，不得扩量；单夜 LLM 调用 ≤50 次。
- 夜间做 Study 验证前先关插件 `communication`（否则应用自身 TTS 会发声）。
