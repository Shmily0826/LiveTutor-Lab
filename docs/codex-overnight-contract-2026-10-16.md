你是接手 LiveTutor / N.E.K.O 日常学习伙伴项目的开发者。请在 D:\CODE\project\LiveTutor-Lab 无人值守地工作一整夜，修复昨晚第一次真人验收暴露的问题。直接在这个根目录工作：运行依赖只存在于这里的 benchmarks/raw/。不要新建 git worktree，不要切换分支。

【先读】
- docs/claude-goal-2026-10-15.md：目标、红线、自主规则，继续有效。
- docs/claude-goal-status.md：当前状态。顶部"当前状态"不超过 30 行，历史只追加。
- docs/claude-acceptance-guide.md：真人验收脚本，所有工作向它倒推。
- docs/evidence/ 下 claude-w1 … claude-w5 报告：已通过的项不要重做。

【第 0 步（必须先做）：关掉语音权限】
benchmarks/raw/daily-companion-audio-policy.json 里的 audio_allowed 因为昨晚的真人验收被设成了 true。你开始工作前先把它改回 false，原文件备份在 benchmarks/raw/evidence/claude-acceptance-policy-before.json。整夜不得开麦克风，不得使用任何真实或虚拟采集设备、回环，不得改系统音量。扬声器只在固定 WAV 的 output-only 场里用，且只用用户预设的 4%。做完第 0 步在状态文件记一行。

【外呼额度（由用户在启动前填写；留空则整夜不发起任何真实模型调用或 Native 连接）】
账本 benchmarks/raw/neko-desktop-egress-cap，轮次 bargein-autocheck-20261012，不重置、不提额、不换轮次。
本轮上限：DeepSeek 新增 ____ 次，Lanlan.app 新增 ____ 次连接。
每场开始前和结束后都核对账本并把数字记入状态文件。同一失败最多重试一次；服务超时就退避，转去做本地工作。额度没填或用尽后，只做离线工作，并在状态文件写明哪些项因此没法端到端验证。

【背景：昨晚真人验收发现的问题（证据来自宿主日志 benchmarks/raw/neko-desktop-host.log 的 2026-10-16 00:15–00:23 一段、日常库 benchmarks/raw/neko-daily-companion/N.E.K.O/plugins/study_companion/data/study_companion.db；这两处都只读，绝不修改、不清理）】
1. 语音模型回答源码问题时调用了底层的 study_code，而不是 study_explain(material_source=project_code)。后果：
   - 第 2 步没有出现"正在查看源码……"提示（scripts/neko_study_wait_notice_patch.py 只给 study_explain / study_quiz / study_summary 配了提示）。
   - 第 4 步（"如果改成只在 500 以上才抛，404 会怎样"）用中文整句做 explore 查询，回答含糊，没用上昨天修好的"追问复用上一段源码窗口"和"字符串形式的 code_requests"路径。
2. 第 5 步两次 study_answer 都在同一秒内返回、没有评分，qa_records 是 0 条，interactions 里也没有评分记录，所以"成绩被记住"没有做到。日志里 "[study-material-audio] result binding present=False valid=False reply=False"。原因未知。怀疑与日常库当前课程是遗留的 human-picture-a-20261014（题目由 Study 里遗留的合成 WEX/NUD/REZ 图生成）有关，但没有证据。
3. 用户在"显示学习材料"窗口里换了 HTML，角色仍然讲旧图。原因：角色看到的是提交到 Study 里的那张图，材料窗口只是给学习者看和指点用的。验收说明对此写得含糊。
4. 重启后问"我们上次讲到哪了"，回答只提到图的方向，没提到 404 那段代码。
5. 打断本身约 1–1.5 秒完成，但新问题从开口到第一声约 18 秒：识别约 3 秒，工具约 5 秒，工具返回到第一声约 9 秒。
6. 第一句话的麦克风输入峰值约 270，低于阈值 500，识别有误。属于环境，不需要改代码。

【工作项（按顺序；某项受阻就记录原因，转下一项，不要停下整个任务）】

W-A 让语音模型走讲解通道
- 改 payload 里 study_code 与 study_explain 的工具说明（patches/neko-study-2026-10-10-product/payload/study_companion/study_avatar_tools.py 和 study_code_tools.py）：study_code 只用于查资料；学习者口头问"这段代码怎么处理/这一行是什么意思/如果改成……会怎样/再讲讲"，一律用 study_explain，material_source=project_code，并说明追问可以省略 code_requests。
- 先查这些说明是否还被宿主或 Native 侧另存了一份（比如 scripts/ 或 benchmarks/raw/daily-phase21-native-tool-schema.py 一类），如果有，写进"待 Opus 复核"，不要改宿主文件。
- 先写离线测试，再改。有额度时用一两个固定 WAV 的 output-only Native 场验证：
  · 第 2 步中文原句"讲一下 weather_service.dart 里非 200 响应怎么处理，两句话。"
  · 第 4 步带两处约 0.9 秒停顿的追问（WAV 在 benchmarks/raw/voice-input/daily-w5-step4-pause-20261015.wav；中文第 2 步 WAV 可用 scripts/make_w5_fixture_wavs.ps1 的写法合成，只写文件，不播放、不采集）。
  通过标准：宿主日志出现 TRIGGER entry='__llm_tool__study_explain'，第二场没有 "请指定一至三个有界源码范围后再讲解"，追问接着上一段代码回答。

W-B 查清并修复"评分没落库"
- 把日常库复制一份到 benchmarks/raw 下的新目录（只读复制，不动原库），在副本上用离线 Harness / 文字 SDK 复现 study_answer 立刻返回的原因。重点看 study_answer_tool 里的早退路径：课程上下文校验（material_context_current、source_material_context.course_id 与当前课程比较）、QUESTION_CONTEXT_CHANGED、study_retry_question、study_evaluate_answer 无反馈时直接 return payload。
- 修好后让评分失败时给出角色能说出口的原因（"这道题和现在的课程对不上，请重新出题"之类），不要沉默。
- 先写离线测试：遗留课程 + 图片出题 + 回答的完整路径。有额度时，在全新的任务 store 里用文字 SDK 场验证出题→答错→纠正→qa_records/wrong_questions/mastery 追加。
- 不删、不改任何旧学习记录。

W-C 验收说明与干净课程
- 修改 docs/claude-acceptance-guide.md：第 6 步写明"换图要在 Study 窗口里提交图片，学习材料窗口只用于看和指点"；增加"开始前新建一个验收专用课程并提交 Sky Scout 架构图"的具体点击步骤；列出昨晚发现的已知限制；"评分偏严""中文整句 explore 不可靠"保持。
- 不要修改用户的日常库来帮用户准备课程；只写步骤。若要写准备脚本，只能对复制出来的库或全新 store 运行。

W-D 只读分析：打断后的等待、重启后的接续
- 用日志把"工具返回到第一声约 9 秒"拆开（工具结果大小、provider 生成起点、arbiter 排队），写进 docs/evidence 的短报告。是提供商侧就如实写，不要硬修。
- 分析"我们上次讲到哪了"走的是哪个工具、取了哪些历史、为什么没提到源码问答。只写设计建议（可以借鉴 DeepTutor Learning Journal 的"学习目标/上次总结/下次重点"短摘要，但不另建记忆系统），本夜不实现。

【高风险停止规则（重要）】
需要修改 benchmarks/raw/neko-product-host 下的宿主文件（新增或修改宿主补丁）、触碰 response arbiter / 打断 / 语音传输逻辑，或修改 scripts/neko_voice_host_patch.py 时：只要没有充分把握就不要动手。在 docs/claude-goal-status.md 顶部"待 Opus 复核"一节写清：问题、证据、拟议方案、风险。然后转去做其它工作项。payload 层（patches/neko-study-2026-10-10-product/payload 下）的修改可以自主完成。
特别地：给 study_code 增加"正在查看源码……"提示需要改宿主补丁，本夜不做，只记录。

【每次改动都必须通过】
- 相关离线测试加原有回归：在 scripts 目录用 benchmarks/raw/neko-product-host/.venv/Scripts/python.exe -B -m unittest <模块>，设置 PYTHONIOENCODING=utf-8。每个 test_neko_*.py 模块各用独立进程运行（整套放同一进程会被隔离守卫串扰出大量假错误）。目前已知 7 个与 payload 无关的未通过模块：test_neko_autocheck_readiness、test_neko_tool_result_lifecycle、test_neko_first_asr_ordering、test_neko_late_asr_tool_patch、test_neko_study_singleflight、test_neko_study_speech_gate、test_neko_material_audio；除它们之外不得出现新的失败。
- 改 payload 时：
  1. 先核对 payload、product manifest（patches/neko-study-2026-10-10-product/manifest.json）、已部署副本 benchmarks/raw/neko-daily-companion/plugin-code/study_companion 三方旧 SHA256 一致；
  2. 备份旧副本到 benchmarks/raw/evidence/ 下新目录（不提交）；
  3. 部署，复核新 SHA 三方一致；
  4. 更新 manifest 条目（sha256、旧 sha 字段、一句话说明）；
  5. 在 scripts 目录调用 neko_desktop_tutor_host.verify_source_audio_gate()，必须通过；neko_voice_host_patch.py --check 必须全部 patched。
- 若真的改了宿主（原则上本夜不改）：用独立补丁脚本，锚点不得落在 neko_voice_host_patch.py 的任何 hunk 内，加入 neko_desktop_tutor_host.apply_voice_host_patch 启动链，更新 host manifest，跑 neko_host_rebuild_check.py --write 和校验，必须 31/31。

【红线】
- Sky Scout（D:\UoA\S2\COMPSCI 734\project\Sky Scout\sky_scout）只读。
- 不删除、不清空学习数据和用户历史；不 reset、clean 或 stash 根目录工作树；日常库 benchmarks/raw/neko-daily-companion 与日志只读。
- 证据分层写清：离线 / 真实文字模型 / output-only Native / 可听性（待用户）/ 真人（待用户）。不要把离线或排程结果写成可听或真人通过。
- 不要为了让测试通过而硬编码答案；答错就改机制，不改题。

【记录与发布】
- 每完成一个工作项，在 docs/evidence/ 写一份短报告：改了什么、证据、数字、未解决项。
- docs/claude-goal-status.md（也可新建 docs/codex-overnight-status.md 并在前者里加链接）顶部状态不超过 30 行，历史只追加；"待 Opus 复核"一节放被停止规则拦下的事项。
- 每完成一项，在发布工作树 C:\Users\Shmily\.codex\worktrees\daily-companion\LiveTutor-Lab 里精确复制相关文件，先做密钥扫描，commit 并 push 到 codex/daily-learning-companion：不合并主分支，不强推，不提交 raw、学习库、录音、备份、密钥。
- 整夜保持节奏：不要空转轮询；长任务放后台；同一问题失败两次就记录并转下一项。

【结束条件】
工作项全部完成，或都有明确的受阻记录后，在状态文件写一段结论："是否可以请用户做第二次验收：修了什么、证据层级、哪些没法验证（尤其是语音端到端）、需要用户判断什么、待 Opus 复核项"，并列出验收前用户需要做的准备（新建课程、提交图片、调大麦克风输入音量）。然后停下：不要开麦克风，不要开始真人验收。
## 用户于 2026-10-16 批准的执行补充（优先于上文和旧 contract）
- 用户明确说“ok批准，开始吧”。完整原任务保留于上文。
- 本轮 DeepSeek 新增最多 200 请求；起点 1201，累计停止线 1401，原全局 2000 上限不变。Lanlan.app 起点 105，本轮连接不限；Lanlan.tech 仍为 0。原轮次 bargein-autocheck-20261012 不重置、不换轮次。
- Codex Goal 不设 token 上限。额度充足不构成重复已通过测试的理由；同一失败最多一次有界重试。
- 本轮只做 W-A 至 W-D；新任务的禁止麦克风、采集设备和 loopback 优先于旧 contract 的回环授权。固定文件 output-only 可以使用用户预设 4% 扬声器，不改系统音量。
- 日常学习数据、历史和原宿主日志只读；唯一部署例外是 benchmarks/raw/neko-daily-companion/plugin-code/study_companion 代码，须先备份、核验旧 SHA、更新 manifest、核验新 SHA。
- 开工记录具体失败测试及原因；7 个历史失败模块不能整体豁免，新失败同样算回归。
- W-A 检查 Native 实际 schema 与实际调用，不以工具说明测试替代语音路由证据。需要修改宿主则登记待 Opus 复核；本轮不改宿主、arbiter、打断和语音传输。
- W-B 不预设遗留课程是根因。SQLite 用只读源连接的 backup API 做包含 WAL 的一致性快照，只修改副本或新 store。
- 状态文件 docs/codex-overnight-status.md 为本轮唯一实时状态；旧 docs/claude-goal-status.md 加链接，旧历史不覆盖。
- 每次上下文压缩和 Goal 自动续跑先读本 contract、状态、相关证据与 git diff，再继续；保留用户脏工作树，不切分支、不建新工作树。
- 每项通过必要验证后在既有发布工作树精确复制、扫描、commit/push codex/daily-learning-companion。不合并、不强推、不提交 raw/数据库/录音/备份/密钥。
- 本轮交付是修复/验证/诊断与发布；阻塞必须有证据、恢复条件，继续其他独立项。全部可做项交付后总结是否适合第二次验收；不能把受阻、预算耗尽或夜间结束写成产品通过。
- 第 0 步已完成：audio_allowed 从 true 改回 false，其余策略字段未动。