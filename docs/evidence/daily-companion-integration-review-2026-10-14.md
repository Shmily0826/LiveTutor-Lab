# 日常学习伙伴集成审查（2026-10-14，NZDT）

What this change does: 本阶段将可靠的 Study 图片入口接到日常课程和角色工具，将明确偏好存在现有 SQLite 中，并提供固定启动目录。按单个学习者、一个宿主和角色/网页双入口审查。以下为审查时的源码快照，主 Agent 正在修复；行号用于定位发现时的问题，不表示修复后的结果仍失败。

## Must fix

1. **旧全局语言覆盖新保存语言**（`patches/neko-study-2026-10-10-product/payload/study_companion/study_avatar_tools.py:337`、`:403`）
   - What this is: 原语言工具在 `StudyState.teaching_language` 保存全局语言，新偏好工具在现有 `kv.learning_preferences` 保存语言。
   - Problem: 用户先设置全局英文，再通过新偏好工具明确保存中文，结果返回 `saved=zh-CN`，实际生产 `_study_effective_language` 返回 `en-US`。旧 state 优先级压住新 kv。
   - Fix: 统一全局来源，读取顺序使用课程语言 → 新 kv 默认 → 兼容旧 state 默认 → 初始语言。主 Agent 已开始调整该顺序；仍需修后真实方法回归。
   - If we skip it: 工具确认已记住中文，但后续教学仍用英文。

2. **临时偏好返回成功却未进入下一次教学**（`study_avatar_tools.py:397`、`:370`；路径同上）
   - What this is: `remember=false` 应让当前教学采用临时要求，同时保持长期设置。
   - Problem: 保存 detailed 后调用临时 brief，返回 `brief`；下一次生产 `_study_language_directive` 仍注入 `"length": "detailed"`，没有 `brief`。仅让角色在后续问句里复制要求，不能证明后端当前实际采用。
   - Fix: 使用仅实例存活的下一次教学覆盖，并在 context 构造时合并与消费，禁止落库。已按主 Agent 的追加分工修改 context/prompt：`learning_preferences_scope=turn`，明确本轮覆盖 saved；主 Agent 负责偏好工具与语音 directive 的设置、课程切换清理。
   - If we skip it: 临时篇幅、讲法和是否出题可能被旧长期合同覆盖。

3. **角色换课后网页仍可把旧图片提交到新课程**（`patches/neko-study-2026-10-10-product/static/main.js:1313`、`:2032`）
   - What this is: 网页上传成功后保留 `studyInputImageValue`；角色也可独立切换课程。
   - Problem: 网页的 `startCourseSession` 清旧图，但刷新状态 `setStatusLine` 只更新课程标签。A 的图片保留在预览，角色切 B 后再点击 Explain，会走 `study_submit_image` 并把 A 图片写进 B 的持久材料。
   - Fix: 状态课程 ID 改变时清旧预览、输入、previousExplanation 与答题上下文；提交前重新核对 preview 所属课程，避免未刷新状态时直接提交。
   - If we skip it: 新课使用上一课的图，并且污染新课重启后恢复的材料。

4. **换课清 state 后仍带入旧 OCR 图片缓存**（`patches/neko-study-2026-10-10-product/payload/study_companion/__init__.py:823`、`entry_tutor_context_support.py:783`）
   - What this is: 会话切换恢复目标课的显式图片；没有显式图片时，context 会退回 `StudyOcrPipeline.latest_vision_snapshot`。
   - Problem: A 的截图在 30 秒缓存期内切到没有图片的 B，state 虽然为空，最终 B context 仍含 `A_OLD_CAPTURE`。离线实际生命周期及 context 方法已复现 `course=B/image=A_OLD_CAPTURE`。
   - Fix: 切课时清现有 pipeline 的视觉快照，或给缓存绑定课程并拒绝不匹配。主 Agent 负责 `__init__.py` 清理；context 既有显式 state 图片优先保留。
   - If we skip it: 没有图片的新课程看似使用新材料，模型却收到旧课的截图。

## 证据与验证边界

上述语言、临时篇幅、跨课缓存复现只执行实际产品方法和新建临时 SQLite，未调用模型、音频、宿主。先遇到的测试夹具问题已单独报告主 Agent：`test_neko_daily_materials.py` 的 Store 实参缺少 seed/logger；其 `DailyHarness` 的继承顺序还会用 `ProductHarness` 的固定中文 stub 盖过真实语言方法。后续复现显式绑定生产语言方法，不能把第一次 stub 输出当作产品语言证据。

追加的 `test_neko_learning_preferences.py` **6/6 通过（0.580 秒）**，新增检查 saved detailed/主动出题 → 本次 brief/不出题 真正进入 system prompt → 下一轮恢复 saved；临时设置不落库。这是 context/prompt 层离线证明，工具设置和真实模型效果仍待主 Agent 集成验收。

固定入口 `Start-Daily-Tutor.cmd` 使用隔离 store、同一预算轮次、Lanlan.app unlimited、无 Lanlan.tech 放行。只在临时 cap 文件验证 Sink：同轮恢复已用 DeepSeek271/app30，app 再预扣到31，tech0仍拒绝；未接触线上或真实账本写入。真实账本只读时仍为 DeepSeek271/app30，授权 cap2000/null/0。不限 CONNECT 的序列化与继续记数在该隔离检查成立；重连退避和设备会话未做当前动态证明。

提交图片保存及返课恢复读取沿用现有 Store，没有发现删除原学习历史的操作。图片保存错误的恢复、浏览器实际点击、网络中途失败、模型回答遵循、设备播放和真人体验不在本次已通过范围。

Verdict: 先修复并复验 1、3、4，以及完成 2 的工具接入，再做真实模型阶段验收。四个问题不是整个 Goal 的全局阻塞。

Not checked: 线上模型、设备音频、真人体验；没有扩大到未指定模块或清理未知进程。本审查新增外部请求 0，临时 SQLite/cap 文件已由临时目录清理。

## 后续定向审查：源码表面、图片课程竞争与原生目标

此段为主 Agent 新增集成后的复核，前文为历史发现快照。只读指定源码；另按追加分工仅修改 `scripts/test_neko_image_course_guard.py`，没有修改产品源码、打开宿主/浏览器/网络或音频。

授权/凭据边界：`study_code_tools.py:553` 发布的是既有 `_code_filter`、`_code_leak` 后的 evidence，surface未新读源文件或绕过CodeGraph授权；`_publish_code_surface` 仅允许显式127.0.0.1 URL并禁用环境代理。`neko_learning_surface.py:113` 对源码行和标签做HTML escape，材料通过内容hash ID及当前选择绑定，旧版本被替换后不能继续guide。未发现这条新增展示路径旁路既有源码/凭据过滤的实质问题。源码表面HTTP/浏览器测试fixture会启动监听，不满足本次纯离线限制，因此未重跑它们；用仅内存surface对象复核escape和版本行为。

定向发现与修复结果：

1. **相同源码重复发布会打断材料选择和指示**：发现时 `show_code_evidence` 删除所有code条目后重加同ID，仍按stale列表把active切回首架构图。主 Agent 已加相同material_id幂等返回；仅内存复核相同project/commit/evidence重复发布后，active仍为同code ID，pointer保留，script标签保持escaped。此问题已由当前源码修复；未冒充真实浏览器点击验收。
2. **图片保存后换课的竞争窗口**：发现时 `expected_course_id` 只在保存前校验，释放锁后解释可以取新课程上下文却携带旧图片。主 Agent 已捕获提交时course/session，将request session传给context构造，并在解释开始、context返回、模型返回后检查；延迟结果的 `_record_tutor_result` 不再污染新session实时seed。追加实际方法离线检查 **4/4通过，0.057秒**：preflight后变课不保存、构造context期间变课/同课换session不调模型、模型完成时变课不finalize、旧session结果不改新实时seed/events而当前session结果仍记录。历史仍绑定原request session，原学习历史未清空。
3. **原生观察可能选择非音频页面**：发现时 `NativeTelemetry.attach` 仅按本机48911页面url排序，INSTALL无socket也返回observer。纯离线mock根页面与实际音频页面并存时选根页面且socketReady为空仍成功，证明目标验证缺口。主 Agent 已加每个候选的ready socket和 `window.appAudioPlayback`检查；修后离线mock跳过并关闭非音频根目标，选择ready chat。现有源码确实在 `static/app/app-audio-playback.js:2177` 导出该能力；历史timing实际url是 `/chat`，不因早先“pet拥有PCM”的注释而否认这份已记录设备证据。真实当前native目标未在本轮重新打开检查。

`test_neko_native_telemetry.py` **2/2离线通过，0.124秒**，验证并发协议ID及JS解析/无麦克风请求；新增target筛选使用单独纯离线mock复核，无CDP网络连接。受影响图片guard差异检查通过。旧版本指示的几何浏览器检查、真实模型课程切换、实际device播放仍由主 Agent统一安排，未重复已通过批次。

Verdict: 本次定位的三处具体问题已有主线修复及上述定向离线证据，未发现新的授权/凭据过滤旁路。图片课程和原生目标的线上结果仍须按对应证明层记录，不把离线guard当成真人体验。本子任务新增外部请求、额度调整、宿主/音频进程均0。
