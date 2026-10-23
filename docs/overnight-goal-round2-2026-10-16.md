# 夜间任务书（第二轮，预计 6–10 小时）：把第二次验收修到可以请用户做

你是接手 LiveTutor / N.E.K.O 日常学习伙伴项目的开发者。在 D:\CODE\project\LiveTutor-Lab 无人值守工作。直接在这个根目录工作：运行依赖只存在于这里的 benchmarks/raw/。不要新建 git worktree，不要切换分支。

## 先读（按顺序）
- docs/claude-goal-2026-10-15.md：目标与红线，继续有效。
- docs/claude-goal-status.md、docs/codex-overnight-status.md：当前状态；你要接手并维护。顶部状态各不超过 30 行，历史只追加。
- docs/claude-acceptance-guide.md：真人验收脚本，所有工作向它倒推。
- docs/evidence/ 下 claude-w1…w5、codex-wa…wd 报告：已通过的项不要重做；先读 codex-wa（第 4 步空回合）和 codex-wd（延迟、重启接续）。

## 第 0 步
确认 benchmarks/raw/daily-companion-audio-policy.json 的 audio_allowed 是 false（不是就先改回，原文件备份在 benchmarks/raw/evidence/claude-acceptance-policy-before.json）。整夜不得开麦克风，不得使用任何真实或虚拟采集设备、回环，不得改系统音量。扬声器只在固定 WAV 的 output-only 场里用，只用用户预设的 4%。

## 外呼额度（由用户在启动前填写；留空则整夜不发起任何真实模型调用或 Native 连接）
账本 benchmarks/raw/neko-desktop-egress-cap，轮次 bargein-autocheck-20261012，不重置、不提额、不换轮次。
本轮上限：DeepSeek 新增 ____ 次（建议 250），Lanlan.app 新增 ____ 次连接（建议 40）。
每场开始前和结束后核对账本并记入状态文件。同一失败最多重试一次；服务超时就退避，转去做本地工作。额度没填或用尽后只做离线工作，并写明哪些项因此没法端到端验证。

## 背景（已知的事实，不要重新论证）
1. 第一次真人验收（2026-10-16 凌晨）暴露：语音模型用底层 study_code 回答源码问题，没有"正在查看源码……"提示，第 4 步追问含糊；第 5 步评分没落库（已查明：Native 把首答误带 correction_of，已由 fe03e38 修复，Native 与文字 SDK 都有 错答 0→纠正 100 的落库证据）；在"学习材料"窗口换 HTML 不会改变角色看到的图（角色看到的是提交到 Study 的图）；重启后问"上次讲到哪"走 recall_memory，没读 Study 课程总结；打断后到第一声约 18 秒，其中 9 秒在"工具结果提交后到首个 provider 音频包"之间。
2. 第 4 步（带两处约 0.9 秒停顿的追问）在 Codex 上一轮的独立场和唯一重试里都是空回合：无工具、无回复、无音频。停顿暂扣现状：保留前 300 ms、暂扣其后 1000 ms；昨晚日志里 0.98 s 的停顿被压到约 0.28 s，provider 仍然拆成两条识别。可调环境变量：NEKO_PAUSE_HOLD、NEKO_PAUSE_HOLD_MS、NEKO_PAUSE_HOLD_KEEP_MS（见 benchmarks/raw/neko-product-host/main_logic/omni_realtime_client/_transport.py 约 1924–1968 行）。
3. 宿主角色指导（scripts/neko_desktop_tutor_host.py）前段要求源码教学走 study_explain，末段仍写"具体源码行使用 study_code file"，与新工具说明冲突。
4. 已知与本任务无关的 7 个历史失败测试：test_neko_autocheck_readiness、test_neko_tool_result_lifecycle、test_neko_first_asr_ordering、test_neko_late_asr_tool_patch、test_neko_study_singleflight、test_neko_study_speech_gate、test_neko_material_audio。除它们外不得出现新失败。

## 工作项（按顺序做；某项受阻就记录原因转下一项，不要停下整个任务；每项做完才写报告和发布）

### P1 角色指导冲突
把 scripts/neko_desktop_tutor_host.py 里"具体源码行使用 study_code file"改成与 explain 路由一致（口头讲解/行含义/假设改动/追问一律 study_explain，study_code 只在查资料时用）。这是启动脚本里的一句文字，不触碰打断、仲裁或语音传输。先写离线测试（断言角色指导里不再出现与 explain 冲突的指令），改后核对宿主补丁校验与 SourceGate。若发现这句话同时落在 neko_voice_host_patch.py 的 hunk 里，立刻停下，转"待 Opus 复核"。

### P2 第 4 步空回合（本轮最重要）
a. 只读：用 codex-wa 的三个原始场文件（benchmarks/raw/evidence/codex-wa-native-*.json）和 claude-w5-step4-voice-1/2.json 对比"会工作的第 2 步"和"空回合的第 4 步"：识别条数、第二条识别到达时 response 是否已开始/已结束、有没有 function_call、response.done 是否为空。把结论写成短表，区分事实与推断。
b. 暂扣参数扫描（只改环境变量，不改代码）：用 benchmarks/raw/voice-input/daily-w5-step4-pause-20261015.wav（两处 0.9 s 停顿），在新的任务 store 上，output-only。候选：KEEP_MS ∈ {300, 100, 0} × HOLD_MS ∈ {1000, 1500}，先跑 (100,1000)、(0,1500)、(100,1500)，再决定要不要补其余；每组最多 2 次、总共不超过 8 个 Native 场。每场记录：识别条数、是否出现工具调用 study_explain、是否有音频、回答是否接上上一段代码。同时用一个无停顿的对照句确认暂扣不会让普通输入变慢超过 1 秒。
c. 若某组参数稳定通过（连续 2 场识别 1 条、有工具、有回答），把它作为 Start-Daily-Tutor-Voice.cmd 的默认值，并写明"打断是否受影响"：重跑既有打断相关测试（test_neko_native_barge_in、test_neko_realtime_barge_in、test_neko_pause_hold）。若没有稳定通过的参数，如实写成 provider 侧限制，不要把"偶尔成功"写成通过。
d. 不做自动补发请求，不碰 response arbiter。

### P3 第 2 步讲解深度
中文原句"讲一下 weather_service.dart 里非 200 响应怎么处理，两句话。"上一轮的回答只有一句，没讲第 26 行解析不会执行。判断是教师提示、工具结果的 relay 还是 Native 角色复述丢了第二句。先用文字 SDK 的教师回复确认教师是否给了两句；再看 Native 复述。能在 payload 层（tool 的 relay 说明、reply 结构）修的就修，并用固定 WAV Native 场复核 2 次。

### P4 指示：让角色在"指给我看"时真的调用 study_point
验收第 6 步要求"指出某个关系"，目前没有任何一次角色自主指示被观测到。检查 study_point 的工具说明与角色指导：学习者说"把 X 到 Y 那条箭头指给我看/标出来"时应先 study_point(kind=status) 取得可用选择器，再 selector/rect 指示。合成一个中文固定 WAV（只写文件，用 scripts/make_w5_fixture_wavs.ps1 的写法），在学习材料窗口选中 forward 图（benchmarks/raw/evidence/diagram-input-forward.png）的场景里跑 output-only Native，检查 probe 报告里的 surface_guide_attempts 是否有 accepted。最多 3 个场。若角色始终不调用，改工具说明/角色指导的措辞再试一次；仍不行就如实记录。注意：Study 里角色看到的图（提交的图）和材料窗口里被指示的图是两套，要在报告里分开写。

### P5 重启后的接续摘要（借 DeepTutor Learning Journal 的结构，不另建记忆系统）
目标：重启后问"我们上次讲到哪了"，角色能说出上次课程、讲过的源码文件和行范围、最近一次出题和成绩、建议的下一步。
- 数据来源只能是现有 SQLite（sessions、interactions、code_question、qa_records、wrong_questions）。新增一个不调用模型的 resume brief（数据字段，不是新表），由现有 study_session status 返回，或作为 study_summary 的无模型分支；工具说明里写明"泛问上次/进度用它，不要用 recall_memory"。
- 先写离线测试（多个会话、多个课程、旧行没有 call 字段、没有历史时的诚实回答），再实现。不删、不改旧记录。
- 验证：新任务 store 里文字 SDK 场（讲源码→出题→答错→重启→泛问→追问 404）；再用固定 WAV Native 场复核 1–2 次（中文 WAV"我们上次讲到哪了？"需新合成）。

### P6 延迟：打断后的 9 秒
只读 + 小实验。先用已有日志拆"工具结果提交 → 首个 provider 音频包"，对比工具结果大小（reply、relay 长度）与该间隔。若发现 relay/结果体很大，做一个 payload 层的 A/B（缩短 relay 说明或 reply 结构，各跑 2 个固定 WAV 场，同一问题），只在有明确改善（中位数减少 ≥ 1.5 s）且回答质量不降时采用。无改善就不改，写成 provider 侧。

### P7 干净课程的一键准备
写一个只作用于"新建任务 store 或复制出来的库"的准备脚本（不碰 benchmarks/raw/neko-daily-companion），演示：新建课程、提交 Sky Scout 架构图（benchmarks/raw/evidence/diagram-input-sky-dark.png）、确认角色看到的是这张图。再把"用户自己在 Study 窗口里怎么做"的点击步骤写进验收说明（不要改用户日常库）。

### P8 完整彩排与验收说明 v2
全部完成后，用新任务 store 按验收说明 1–7 步做一次完整彩排：能用固定 WAV 的用 WAV（Native output-only），其余用文字 SDK；重启一次。每步给出：用的是哪种证据、结果、等待时间。更新 docs/claude-acceptance-guide.md 的期望和已知限制。明确哪些步骤仍只有文字证据。

## 高风险停止规则（重要）
需要修改 benchmarks/raw/neko-product-host 下的宿主文件（新增或修改宿主补丁）、触碰 response arbiter / 打断 / 语音传输逻辑，或修改 scripts/neko_voice_host_patch.py 时：只要没有充分把握就不要动手。在 docs/claude-goal-status.md 顶部"待 Opus 复核"一节写清：问题、证据、拟议方案、风险；然后转去做其它工作项。payload 层（patches/neko-study-2026-10-10-product/payload 下）和 Start-Daily-Tutor-Voice.cmd 的环境变量可以自主改。给 study_code 增加"正在查看源码……"提示需要改宿主补丁，本轮不做。

## 每次改动都必须通过
- 在 scripts 目录用 benchmarks/raw/neko-product-host/.venv/Scripts/python.exe -B -m unittest <模块>，设置 PYTHONIOENCODING=utf-8。每个 test_neko_*.py 模块各用独立进程运行（整套放同一进程会被隔离守卫串扰出假错误）。
- 改 payload 时：先核对 payload、product manifest（patches/neko-study-2026-10-10-product/manifest.json）、已部署副本 benchmarks/raw/neko-daily-companion/plugin-code/study_companion 三方旧 SHA256 一致；备份旧副本到 benchmarks/raw/evidence/ 新目录（不提交）；部署；复核新 SHA 三方一致；更新 manifest 条目；在 scripts 目录调用 neko_desktop_tutor_host.verify_source_audio_gate() 必须通过，neko_voice_host_patch.py --check 必须全部 patched。
- 若确实改了宿主（原则上不改）：独立补丁脚本，锚点不得落在 neko_voice_host_patch.py 的任何 hunk 内，加入 apply_voice_host_patch 启动链，更新 host manifest，neko_host_rebuild_check.py --write 与校验必须 31/31。

## 红线
- Sky Scout（D:\UoA\S2\COMPSCI 734\project\Sky Scout\sky_scout）只读。
- 不删除、不清空学习数据和用户历史；不 reset、clean 或 stash 根目录工作树；日常库 benchmarks/raw/neko-daily-companion 与原日志只读（要用数据就复制一份再用）。
- 证据分层写清：离线 / 真实文字模型 / output-only Native / 可听性（待用户）/ 真人（待用户）。不要把离线或排程结果写成可听或真人通过；不要把"没有出现拒绝句"写成成功；不要用硬编码答案让测试通过。

## 节奏与记录
- 整夜保持节奏：长任务放后台，不空转轮询；同一问题失败两次就记录并转下一项；某组 Native 场连续失败就停下该线路。
- 每完成一个工作项，在 docs/evidence/ 写一份短报告：改了什么、证据、数字、未解决项。
- 每完成一项，在发布工作树 C:\Users\Shmily\.codex\worktrees\daily-companion\LiveTutor-Lab 里精确复制相关文件，先做密钥扫描，commit 并 push 到 codex/daily-learning-companion：不合并主分支，不强推，不提交 raw、学习库、录音、备份、密钥。
- 如果所有项提前做完，不要为了跑满时间发明新任务；写结论后停下。

## 结束条件
全部工作项完成或都有明确的受阻记录后，在状态文件写一段结论："是否可以请用户做第二次验收：修了什么、证据层级、哪些没法验证（尤其是语音端到端）、需要用户判断什么、待 Opus 复核项"，并列出验收前用户需要做的准备（新建课程、在 Study 提交图片并点 Explain、调大麦克风输入音量/离近一点、关掉其它占用 48911/48916 的实例）。然后停下：不要开麦克风，不要开始真人验收。
