# Phase 6 教学入口与 SDK 量具窄审查

日期：2026-10-14。先完整读取本 Goal contract、plan、status、blockers；最新主线消息优先于记录中的 voice15 pending 状态。主线告知 voice15 已 terminal：539/54/0，旧 socket 文字拒绝，无工具/PCM；voice16 三固定 WAV 正在执行。本审查未读取账本、未干扰进程，**voice16 pending 不计设备验收**。

What this change does: 评分使用被保存题目的固定内容，并将异步模型结果、原 session 历史和当前 live 题目分开保护。SDK 和失败量具使用实际插件协议/SQLite以及明确的 loopback 模型 stub；假输出 owner 不代表真实 Native 或设备。

## 范围与结论

只读以下五文件，读取必要连接段落；未审查完整33文件 allowlist：

- canonical `entry_tutor_answer_entries.py`
- canonical shared `entry_tutor_context_support.py`
- canonical `llm_prompts.py`
- `scripts/neko_material_sdk_probe.py`
- `scripts/neko_daily_failure_probe.py`

五文件的 SHA256 比对确认主项目与 `C:\Users\Shmily\.codex\worktrees\daily-companion\LiveTutor-Lab` 的待发布副本一致。没有运行测试、宿主、SDK/API、在线模型、音频、账本或子 Agent；只新增本报告。

**有限范围内没有发现新的、能由具体场景成立的必修 P1/P2。** 下列修复在当前源码中有对应守卫；既有主线离线/本地 SDK 证据不被本次只读审查升级为独立运行、实际模型、设备或真人证据。

## 评分四处保护

| 审查场景 | 当前代码及结论 |
| --- | --- |
| 已有图换成另一张后，普通回答仍针对被保存的题 | answer entry `74–83` 首次 await 前捕获 course/session subset；`253–262` 无显式 vision 时覆盖 `vision_enabled=False`、空图片、空 vision snapshot、空 OCR。shared builder `781–801` 虽可读取 saved image，但后续 `context.update(extra)` 使 grade 的明确关闭生效，再构造模型上下文。普通 grade 不会默默拿新 saved 图评旧题；显式 vision 是另一条受调用者 context 约束的分支。 |
| course/session 在 history 查询、模型等待或提交前变化 | answer entry `217–227` 确认 resolved session 和 captured context；`266–277` 模型前后确认；shared finalizer `928–952` 以原 request session 写 history，并在相同材料/状态锁内检查 context 后做短提交。`297–298` 以及反馈/返回前守卫拒绝过期结果。合法已提交原 history 不清空或改归新课程。 |
| 同 course/session 的当前题在旧 grade 等待期间被新题取代 | entry 先确认 question_id/attempt_id、expected answer 和 topic，并以 attempt pending 防并发重复评分；shared `_record_tutor_result:840–855` 在原 question/attempt 不再一致时不更新 live seed、recent events、last verdict。entry `344–359` 只有原 attempt 仍在屏幕上才缓存已评状态；`375–403` 在反馈和返回前再次确认题身份。旧已提交 history/tracker 仍指向请求的 question payload/session，不能给新题贴旧 verdict。 |
| 当前 active session 为空却传入 foreign session，或 ensure 改变已有 session | `217–227` 不是只对非空当前 session 做比较：最后要求 `current[session_id] == resolved requested session`。初次启动仅在原 expected session 为空且 course 未变时接收合法 ensure 的新 session；foreign id 或非空原 session 的替换在 `_build_learning_context` 和模型前拒绝。 |

最后一项不等同于 Core 的 invokingSession/role admission：后者不在本次五文件范围，不重复声称独立确认。最新 status 所记 Core dispatcher 拒绝/空 ctx 的离线事实仍归主线。

原 attempt 恢复缓存分支 `136–148` 位于初始材料检查后且没有中间 await；异常/取消清除 pending 只匹配原 attempt。这里没有发现能越过已核身份把另一题缓存作为当前答案的具体新路径。

`entry_tutor_context_support.py:1086–1209` 的知识记录使用原 extra context 里的题、course 和 session。保存旧题 tracker 是保留原证据的行为，不等于向新题 live verdict 写入。mastery event/answer narration 的后续异步队列来源校验仍属于已记录、默认 OFF 的独立叙述待办；不能用 entry 返回前守卫宣称已经保护 queue 中或已生成的声音。

## 模型上下文与私有来源

`llm_prompts.py:93–129` 新增 material_context、source_material_context、_material_context、_study_material_binding 的递归过滤；顶层仍按 allowed fields。因此 history metadata 和 question payload 中嵌套的材料 origin 不会因为被存入原历史就在下一轮 prompt 中全量出现。真实评分仍保留 question/expected_answer/answer，模型才能评估；这些评分必需字段与面向用户的题目答案泄露不是同一个接口。

该结论覆盖当前 JSON dict/list 形状和这四个精确字段，不是任意字符串文本的秘密扫描。没有新增宽泛对象序列化或另一套记忆系统。

## SDK / 失败量具的证据边界

`neko_material_sdk_probe.py:43–94` 明确使用 patched Core harness 的 fake provider/output owner，接真实 registry/envelope/remote-dispatch/SDK HTTP。docstring、`core_fixture` 记录和 `121` 字段均声明没有 Native/provider/device；结果 `153–154` 为 `PASS_*_SDK_LOCAL_STUB_ONLY`。不能将 `core_bound_current_owner` 解释成真实设备绑定。

其三工具检查覆盖每工具 binding 存在、host-only binding 剥离、spoken field、原 arguments 不变；`25–40` 直接只读 SQLite，要求唯一 grade/QA 对应 quiz question_id/attempt_id，summary 使用同 session/material context。评分 avatar 本来省略 ID，量具通过 DB 核身份，没有继续误要求 reply 携带 ID。`144–147` 的 `sdk_accepted_control` 只判断 producer status=`submitted`，名称和用途是 SDK 提交接受，**没有声称 queue stop/cancel/静音**。其 PASS 不验证教学语义、ASR、实际 owner/token、PCM 或 WASAPI。

`neko_daily_failure_probe.py` 仅提供有界 loopback HTTP stub 和已有宿主 probe，launch_plan 返回 argv 而不执行；外部 egress 用隔离 deny sink，固定 dummy credential、fresh fixture store、原 ledger hash 不变。该防护是量具设计，当前审查没有执行或另查账本。

`226–233` 失败判据要求 degraded/unavailable、诊断/诚实回复且无题/评分字段；`300–307` 检查失败后三工具的 DB counts 不变、原 pending attempt 未丢失/消费/遗留 reservation；`308–317` 恢复同 attempt，只增加一个 QA，随后可再次解释。结果明确 `PASS_REAL_BACKEND_LOCAL_STUB`，报告 proof 字段也声明不是实际模型或播放。它证明 local HTTP 503 的协议/DB 恢复，不能外推所有超时、断网、供应商限流、真人或设备恢复；drop 模式可用但该 run 场景没有借它声称全网络覆盖。

## 发布意见

Verdict: 在此五文件和已说明分支的源码审查范围内，可随 Phase 6 继续发布；无新增必修 finding。其余 allowlist、真正模型质量、长 quiet、voice16 terminal/PCM/完整 WASAPI 和最终真人由主线分别验收。voice15 已失败事实保留，不能由本地 SDK PASS 覆盖。

Not checked: 本轮不运行任何测试或实时服务；不独立复验现有离线结果、SDK3/4实际 logs、Core admission 源码之外文件、pending voice16、实际音频取消和默认 OFF narration queue。报告冻结，只有本文新增，其他文件保持冻结。
