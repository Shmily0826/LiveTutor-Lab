# 真人答题未进入正式评分：窄源审

2026-10-15。已完整读取contract、plan、status、blockers；记录中的旧paused状态由Main本轮转达的明确继续Goal指令更新理解，不自行改共享记录。仍禁止mic/capture/loopback；Main独占在线和额度。本任务只读canonical Study工具、必要Core/Native源码及限定private日志/既有status receipt，唯一新增本报告。没有启动应用、provider、浏览器或音频，没有读用户SQLite、配置密钥或执行测试，没有改变历史。

## 结论

**确认的实质缺陷：这轮有明确答当前题意图、真实ASR和直接角色回复，但没有观察到正式Study评分入口执行。** 工具已注册且本场能调用Study出题；持久题目并未消失。现有角色schema/提示要求调用study_answer，但运行路径没有对此类回答施加可靠的入口约束，允许Native直接作口头判断而不产生学习评分记录。

不能由现有证据确定服务端模型为何选择直接说话；也没有证据把本轮定为“评分SQL失败”或“评分任务被迟到ASR取消”。当前最小修复应针对**明确回答held题时的路由**，复用原study_answer→study_evaluate_answer，保留所有题目/材料/owner校验，不能根据口头wrong倒填评分。

## 已核实际证据（不披露学习全文）

private `daily-human-native-observer-20261015-01.jsonl`最后一条user_transcript：wall `1791977250.933`、原文长度67、socket_id=1。只在分析内去空白后检查，确实保留“回答、刚才、判断、对不对、箭头、从右向左、最多两句”等本轮指令成分；没有输出完整转写。原文中文字符之间存在空格，连续中文substring匹配会失败。这是本场真实格式，不能使用普通无空格fixture替代它来证明新路由能接到实际输入。

同轮 `1791977250..7254`窗口有1条user_transcript、9条gemini_response、9条audio_chunk，首audio_chunk wall `1791977252.440`。这些是Native接收事件，不作为本报告新播放/真人验收；口头判错及未抢答反馈来自既有human-feedback报告。

实际host append `benchmarks/raw/neko-desktop-host.log`：

| 行 | 本轮限定事实 |
| --- | --- |
| 76849 | 00:27:13当前audio/realtime session tools snapshot含study_answer、study_quiz等Study工具。 |
| 76889 | 00:27:30Core接受并向前端发送user_transcript，len=67、ws_connected=True。 |
| 76890 | 00:27:31直接角色首文本送达，len=4。 |
| 76895 | 00:27:32首response.audio.delta，bytes=11016。 |
| 76900 | response.done；该窗口没有观察到study_answer/study_evaluate_answer Trigger、Study callback或评分task退役记录。 |
| 76944 | 00:27:49后续study_status查询。 |

00:21:57–00:22:00的同场日志`76467,76483–76484`有study_quiz实际Trigger/callback，证明不是“本场所有Study工具均不可用”。00:27:31附近另有DeepSeek HTTP200，日志没有请求用途/完整body；不能把无名称的HTTP调用视为评分证明。

既有private held与grade-observation的status_receipt.data经本地只读投影核对：qid均为`q_29378ea2b6ca42b1995bc63288807456`，attempt均为`a_f248bbbd8f524c3396daf040b11b8e4a`；question_state均pending、last_answer_evaluation均空。grade observation的既有history投影kind中没有answer_evaluate。本报告只核receipt，没有重新查询原库；结束后SQLite attempt_evaluated=false/evaluation空是Main已经报告的实际证据，独立保留其来源，不能冒称本Agent重验。

该观察支持“未进入评分入口”的高置信定位；普通host日志不是完整provider wire，因此没有把未观察function_call提升为“服务端绝对未产生任何相关事件”。本轮正式追加评分指令没有完整新轮证据，不能另造其失败结论。

## 运行路径为什么能绕过

### Study入口本身正确衔接，但必须先被调用

canonical `study_avatar_tools.py`的study_answer decorator/schema（读到版本约`1080–1091`）已经明示：判断当前题、保存学习历史、学习者答题后立即调用；answer是唯一必填参数。无需模型编造qid/attempt来满足当前public schema。

`study_answer_tool`（约`1093–1132`）先捕获course/session snapshot及输出target，读取当前持久held题，再把两ID注入原`study_evaluate_answer`；它没有创建新题或另建评分系统。原entry的identity/reservation/cache及history写入机制已有，未发现本轮缺少这些ID导致拒绝的证据——没有观察到wrapper被进入。

`study_session_tool(action='status')`（约`693–725`）返回真实public current_question/question_state，可以恢复题；但这是另一个需要被模型调用的工具。角色静态context并不会凭这份schema自动获得权威当前pending状态。不能把“状态getter存在”当本轮角色已经查询过，也不能将角色记得旧题当current判断。

### Core/Native桥没有强制Study评分fallback

实际Core `main_logic/core/tool_calling.py:375–427`的_on_tool_call仅在模型发出ToolCall后执行registry。可信Study allowlist含study_answer，旧invoking_session会拒绝；_ctx由当前角色覆盖，正确的注册和身份边界应继承。它不会从一段直接回复自动生成评分调用。

实际Native `_transport.py:3918–3943`收到input_audio_transcription.completed后推进必要scope并deliver transcript；`519–529`将转写交给绑定Core callback。实际Core `turn.py:2084–2328`处理admission、route identity/takeover、活动记录、插件user-context广播、普通缓存与前端user_transcript。这里可见的关键词fallback是mini-game invite（2262–2267），没有Study答题转为正式评分的分支。不能把该mini-game fallback当Study现成路由。

Native真正派工具由`_transport.py:3677–3748`的function_call_arguments.done进入_start_raw_tool_call；speech gate/late-ASR owner patch及`_tools.py:1155–1208`的相同解释singleflight处理**已有**工具调用，不会补造一个缺失的study_answer。因而这轮没观察Study call时，不能通过延长quiet或更改工具collector解释这个缺陷。

`_tools.py:1106–1153`支持发送工具列表，free分支仅更新tools；没有当前强制选择study_answer的代码。GPT/Grok的auto选项也不等于必调；本审查不猜free代理支持强制tool_choice，不能以未验证provider参数作为修法。

### 角色context只给建议，不能成为落库保障

host `TUTOR_ROLE_GUIDANCE`（约`515–551`）已包含“Grade a learner answer with study_answer”，以及Study图片、总结须工具、原证据规则。这说明不应归因为完全漏写评分工具说明。但只是一条静态指令，没有“pending题状态已权威核实→这轮必须评分”的执行条件。

`apply_tutor_role_guidance`（约`583–619`）尊重用户preset/自写guidance；本任务不读取角色配置，因此没有确认本场provider具体收到哪份persona最终prompt。该未知不能反向归罪用户配置，更不应覆盖用户persona来修评分。注册/成功出题证据已足够先修本轮答题路由缺口。

## 建议的最小修复（待Main实施与验证）

1. 将明确“回答刚才/当前题，并要求判断”的输入引到原study_answer。先使用现有权威Study status/held题快照，只有current course/session下真实pending、qid/attempt非空才准入。仅凭有题或一句“对不对”不够：普通图片判断、请解释错答案、出新题、引用他人答案、模糊代词都不能自动评分。
2. 中文字间空白仅在**意图判断副本**中规范化；原转写、数字、代码、答案和格式要求保留，传递到现有评分entry。不要直接删原answer全部空格造成代码/英文词边界损坏。当前schema answer之外不单列长度要求，若新路由分开答案与请求，须明确把“最多两句原因”等本轮约束传递，不能仅截一个方向词后丢掉约束。
3. 窄fallback需要当前输入的connection/provider session/scope/ASR epoch与可信角色，沿原tool生命周期、cancel和owner检查执行。不能从display self.websocket或过去tool owner借身份；不能在scope退休后复活任务；没有当前pending或权威getter不可用时诚实提示，不做无证据付费评分。一次输入最多一次正式grade，和模型随后发出的相同调用协调，继承原attempt reservation/cache而不另建DB/队列。
4. 特别防“读status的旧题A→等待后当前已变B”：fallback必须携带并核expected qid/attempt/course/session；当前wrapper自行读取最新held只能保护其调用开始后题替换，不能证明ASR回答属于那道新题。可最小增加可信expected identity参数/校验，再复用原entry双ID；错误identity应拒绝，不自动改用B。私有_ctx/expected不得信任模型自述，Core仍覆盖角色身份。
5. 正式判定前抑制本轮Native自由口头评分；它否则可能先说wrong，随后正式工具给相反结果。使用原本轮response/output cancel机制及严格owner，不能cancel下一轮、借材料reconnect无限CONNECT、重放PCM或伪onset。若在所选hook到达前已有provider音频，必须把这个时序限制明确记录，不能声称原音频未曾播放。
6. 小范围增强schema/角色context：明确答held题必须调用study_answer，study_explain/自由口头判断不能代替评分；回复只用正式verdict/feedback，失败则明确未评分。仅改prompt不是确定性修复，仍需上述真实路由证明。

若Main先选择仅在已有模型ToolCall里转换误选study_explain为study_answer，那不能覆盖本场：本轮未观察到任何Study ToolCall。修法必须包含直接Native回复的显式答题路径，或诚实将其保留为尚未修复。

## 最小离线复现与后续证据判据

本Agent未跑tests。Main可用已有实际Core ASR/ToolCall fixture及fresh任务SQLite定向验证，不读写原daily历史、不要求真人重复朗读：

- 当前源码的接受ASR callback＋没有provider ToolCall事件：显式答题仍只入Core缓存/显示，评分registry调用数为0，题保持pending。使用真实方法，不能把admission/registry恒True当集成。
- 新路由的真实字间空白中文ASR：pending原题得到一次study_answer，原qid/attempt正式记录user_answer/verdict/score，attempt_evaluated和last_answer_evaluation真实变化；只改布尔或展示不算评分。
- same-ASR模型迟到相同调用不产生第二QA；grade in-flight真新输入/角色/连接替换不会把旧结果送新owner；原普通onset/cancel保持。
- status后qid/attempt/course/session替换，以及no pending/只读判断/请解释而非答题，均不能把旧话评分到新题或触发新付费grade。
- 用已有entry的0分/错误答案与拒绝/失败分支核正式回执；grade失败不可返回“已评分”或更新掌握度。晚音频抑制与真实可听输出需Main后续独立设备层证明，离线任务不能替代。

本轮源码定位不要求重跑整套已过教学。最终恢复条件是：同类真实Native答题调用正确工具→SQLite原attempt评分→status回读一致→角色转述工具判定；不是一段口头纠错正确，亦不是最终报告exit0。未修代码、未形成新offline/model/device/human PASS。本报告完成后冻结。
