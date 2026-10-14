# 零ToolCall显式答题：Native正式评分最小设计审查

2026-10-15。承接human-grading-routing-review及plan阶段22最后边界，只读实际host Core、Omni transport/tools/responses/必要arbiter与activation方法。没有新代码、tests、manifest、records、账本或用户库改动，没有服务/provider/设备/mic/capture/loopback，未重复任何已通过测试。唯一新增本报告。

## 推荐路线与当前缺口

最小可实施的是：**真实accepted ASR固定本轮owner→可信Study status取得pending身份→原study_answer正式评分→受原owner保护的合法文本relay**。不能通过静态prompt、伪FunctionCall回执或重新播放PCM补这个链。

数据评分路径已有组件，主要新增工作限于ASR owner传递、显式答题准入/单轮任务、输出hold与正式结果relay。**全部Native声音安全闭环仍受旧自由响应取消/新relay关联证据约束**：未宣布response的proxy如果无法确认旧输出终结，不能按timeout或下一包音频释放hold。首版可以保留正式成绩并显示真实feedback，同时明确本轮Native语音未完成；若要继续声音须先建立可证明的终结或独立有界无PCM连接隔离，不把局部协议未知变成假PASS。

## 当前实际接口（存在，而非计划中的API）

| 文件/符号 | 实际能力及最小使用方式 |
| --- | --- |
| `main_logic/omni_realtime_client/_transport.py:3426–3440` message_ws/message_generation/receive_owner_is_current | 此recv循环本来的连接权威；不能回调之后从self.ws重新抓一条新连接冒充。 |
| 同文件`3918–3943` ASR completed、`519–529` _deliver_input_transcript | 原no-VAD scope advance在deliver之前；目前只传transcript及game route identity，没有Native provider/scope owner。最小新增在advance后、第一次await之前固定ASR owner并透传。 |
| `main_logic/core/turn.py:2084–2161` handle_input_transcript | 实际admission、源game route一致性先拒绝；takeover/echo检查及原缓存/显示随后处理。只有accepted普通voice分支才可启动Study job，不能从任意bus文本或后台transcriptDisplay补调。 |
| `main_logic/core/lifecycle.py:2353–2354,2685–2686` Native transcript callbacks；`tool_calling.py:369–373` _make_tool_call_handler | 两处目前直接绑定Core方法，没有固定source client。可按已有tool handler的闭包方式绑定实际Native source，旧client回调不能使用新self.session；同时维持旧兼容回调。 |
| `main_logic/omni_realtime_client/_tools.py:126–188` _capture_tool_task_owner/_tool_task_owner_is_current/_tool_task_connection_is_current | 现成connection generation、provider ws/session和tool scope fences。ASR无provider function response，需要ASR-specific owner处理见下；不能采纳被真新输入退休的owner。 |
| 同文件`239–297,414–452` _track_tool_task/_create_tool_task/_advance_tool_scope/note_user_turn_started | 已有受新输入与connection退役取消的任务集合。可运行本次评分job，不新建长期队列；不能用_start_raw_tool_call来补不存在的provider调用。 |
| `main_logic/core/asr_runtime.py:1802–1837` _capture_voice_session_activation_generation | 同步metadata权威，含当前实际`_voice_lease_connection_id`、ingress session/audio epoch、lease generation、route/profile/permission/pipeline身份。不是启动capture；可固定Core activation并在await/发送后复核。 |
| `main_logic/core/tool_calling.py:375–427` _on_tool_call | 现有registry、真实source plugin metadata、current invoking_session、可信角色_ctx覆盖、material binding接收；fallback本地执行也应经过它。 |
| canonical `study_avatar_tools.py` study_session_tool/status、study_answer_tool | public held双ID/question_state/current course/session，private四字段_expected_question拒绝status后换题。correction_of走现有同题retry，不靠旧attempt重评。 |
| `_response_arbiter.py:681–698` enqueue | 已有event_sender、admission_check、pre_commit、精确ResponseTicket，支持已有一条队列逐send保护。无需新队列/DB。 |
| `_transport.py:980–1105` send_event/send_guard | send前、semaphore等待后及重试前复核；外层入口一次检查不够。 |
| `_responses.py:1419–1469` inject_text_and_request_response；`_tools.py:1326–1355` owned event_sender及cancel_ticket | 已有plain user text＋response.create/ticket的传输及精确结果/取消模式。但现proactive enqueue不带原grade owner；不能原样把晚成绩交它。 |

上述`main_logic/…`路径均相对`benchmarks/raw/neko-product-host/`；canonical相对`patches/neko-study-2026-10-10-product/payload/study_companion/`。本次Root没有.codegraph，用定向源码定位，未扫完整仓库。

## 按顺序实现（最小四处接入）

### 1. ASR receipt固定owner，回调不能等待网络/终结

在_transport ASR completed的现有scope advance之后固定原message_ws/message_generation/current tool scope和可用item_id，沿绑定source-client回调交Core；id缺失时仍保留同连接单调scope，不伪造provider稳定ID。Core同时固定真实activation/lease连接，并按现有admission、route、takeover、echo拒绝边界接受。

Core此时只做同步窄意图匹配、owner/hold登记、_create_tool_task，随后立即返回，让recv继续读。**不能在handle_input_transcript里await远端SDK评分或cancel terminal**：_transport正在await该回调，同一循环无法读取终结/新的ASR，会形成死锁或延长冻结。SDK status/model等待和cancel drain都在受scope取消的job内。

ASR receipt不是FunctionCall receipt。现_ToolTaskOwner默认turn_pair_fence_applies=True，host/provider pair可能是上一条provider response的快照；不能把这个旧pair当当前ASR身份证明。应为exact当前free/no-server-VAD ASR路径建立输入owner，只使用实际connection/scope/ws并保留Core activation；可以复用_ToolTaskOwner数据与checks的专用pair-exempt形式，但不全局关闭普通工具的旧pair fence。_start_raw_tool_call_now:956–963已有针对未宣布响应的局部pair-exempt先例，其触发是已收到provider response_id，不能冒充此次ASR已经有同样ID证据。

显式意图首版可窄到“我回答刚才/当前题＋请判断/评分”以及明确同题更正；只在匹配副本处理本场实际中文字间空格，answer完整传原话/数字/标识符/两句原因限制。普通图片问对错、解释旧答案、不要评分、无题或模糊引用不启动正式grade。当前ASR分片仍会退休旧job；这不是全自然停顿/完整句聚合的解决方案，不重新设计PCM/VAD/onset。

### 2. 在原owner下读权威pending，再执行原评分

getter时点是job启动后、任何paid grade之前；用当前trusted `plugin:study_companion` registry的study_session(action='status')。检查工具来源，固定course/session/qid/attempt及question_state；只投影这些必要字段，不把整个历史/私有答案传回provider。每个await后检查原Native input owner＋Core activation。

普通答案要求pending且四身份完整；更正要求明确修正当前已评分题，传correction_of原双ID，retry入口再次判wrong/partial/无reservation。getter不可用/不合法/没有pending不付费评分。getter只提供一刻的current，_expected_question四身份负责status→grade期间题/课/会话替换；二者都需要，不能改用某个保存的旧tool owner或latest任意题。

然后经Core _on_tool_call执行本地study_answer（包括原answer、四pin，必要时correction_of）。内部本地call_id可作registry追踪，但**永远不作为服务器FunctionCall回执ID**。Core此分支要携带原ASR owner供material binding捕获，而不是走_capture_study_material_tool_owner的else分支在异步返回时晚抓当前owner。原_ctx可信角色覆盖仍保留；模型自述pin/ctx不是宿主授权。

同ASR只登记一次job；fallback和随后真实模型study_answer需要共享本轮结果/原attempt reservation，避免一个正式grade后又发“already evaluated”自由结论。原grade cache保护成绩次数，结果relay还需只一次。新输入退休时不再读取最新pending重新准入；取消后已提交SQL可以保留，但旧job不得播报到新输入。

### 3. 立即hold自由输出，精确取消与终结；不伪onset

显式答题matched之后、status等待前，原client安装短的connection/scope/input-owner输出hold；只影响这一学习grade claim。它必须同时拦截_text/audio.delta、audio_transcript.done的已播放例外和旧output buffer flush，不能只关_audio.delta后让旧错判以文字/最后transcript补出。_transport3971–4014已有交付门，3944–3967的_audio_already_spoken例外需要同一hold；不要任意复用永久_interrupted/skip开关，导致正式结果也被吞。

取消是产品已识别的本轮评分控制，不是新的用户speech onset：不调用note_user_turn_started第二次，不伪造barge-in，不重放PCM。原cancel_response(wait=False,send_guard=原owner)发送可复用；_response_arbiter.cancel_current:989–1005已能处理unowned server response并有有界idle等待，但其_send_event没有此次owner参数，调用前/等待后检查不能保护send semaphore中的晚发。最小应给这次取消发送接原owner guard，且暂停/限定同lane竞争，防取消落到新输入。

pause_dispatch/allow_ticket_while_paused/resume_dispatch（792、877、884）可用，但owner字符串只是label；恢复不是按token保护。必须在本次record still current时才允许自己的grade ticket/恢复，不让旧finally解除下一轮pause。不创建第二队列，使用现arbiter ticket、admission_check、pre_commit和event_sender。

**终结缺失/无响应ID限制：**wait_until_idle可能在尚未观察provider response时立即返回，不能把它当服务端旧自由答案一定不会随后出现；timeout也不能释放hold。若不能证明取消终结或response-owner边界，保留正式grade并展示公开feedback，本轮语音明确未完成。不因量具“不忙”就猜下一段是grade。

已有Core _begin_native_barge_in_handoff:4419–4448包含实际PCM pre-roll/replay，不能原样挪作评分控制；material _replace_study_material_native_connection:270后的game_route_speech_cancel明确不可逆退休physical token，不能先发它再用同token说grade。若Main选择受控无PCM换连接作为缺ID线路的声音隔离，须显式新controlled transition、有界一次、无真新输入时才准许continuation；不能伪material event或提升被真新输入退休的owner。这属于另一个需要证据的窄分支，不建议首版隐藏在cancel timeout里。

### 4. 合法relay仅来自真实grade；每一步守原owner

只有正式result非degraded/ok、current qid/新attempt及course/session回读相符，才构造公开feedback/verdict的plain input_text＋response.create。直接复用原arbiter.enqueue，不直接调缺原owner的proactive helper：在event_sender每次send用原owner/activation，admission_check/pre_commit同步否决队列中的退休任务；失效就cancel精确ticket，不能cancel_current杀下一轮。

typed四pin/state identity若需要最终producer确认，使用现权威getter并在await后再查owner；material binding/变更control沿现Core通道协调，不信origin/旧control自述是current。relay不携私有reference answer/rubric/学习历史，只说实际grade返回的公开结果与未评分错误。new user输入发生在SQL提交后时保留旧成绩、丢晚relay，不恢复旧state。

free初始化_transport779–799只有tools，没有forced named tool_choice能力证明。_tools1277–1294明确free function_call_output必须server真正发过call_id；不能用虚构ID交_send_tool_results_batch。已有create_response(starts_user_turn=False)不退休当前scope，但其enqueue也没有原owner guard，不能原样调用。plain relay合法不等于provider会严格逐字朗读；模型只读真实成绩、不改verdict/句数仍需后续实际服务证明。

## 六组必要回归（不重跑旧全套）

1. **真实方法零ToolCall正例**：actual Native ASR branch→Core accepted callback立即返回，中文真实字间空白/English explicit answer各最小输入→真实SDK getter/grade/fresh SQLite。原held attempt已评、QA和status一致、原answer完整，接收循环仍能读terminal；不使用恒True admission假集成。
2. **准入负例**：无pending、getter不可用/未知来源、不要评分/仅解释/普通图问对错/quote旧答案，零paid grade/零新QA。ordinary非Study语音、原barge handler不变。
3. **等待race与归属**：status或model等待时题/课/session切换、旧client/lease/activation/new inputscope变化，旧任务退出；_expected_question拒，不采纳最新题；提交前无假grade，提交后保留原QA但零晚relay。ABA回原qid但新session仍拒。
4. **重复与更正**：同ASR重复event/迟到真实study_answer与fallback并发，一次正式grade/一次relay；明确wrong/partial纠正同qid新attempt→correct两QA，普通已评重放及正确题修正不新建grade。复用现retry入口，不重出题。
5. **协议/交付**：本地socket/actual arbiter量具验证合法plain message+response.create，无虚构function_call_output；原自由text/audio/最后transcript在hold下不泄露；缺terminal/ID不release；错误/queuefull/timeout非无限重连，失败说未评分或已保存但语音未完成。
6. **精确最终send**：ticket已queued后新输入、send semaphore里连接/activation变化、cancel/terminal错属，都零晚send；旧finally不resume新pause、不cancel新ticket；真实grade replay只一次、ordinary interruption仍由原路径处理。已有17/24等底层已过检查只在相应代码改变时重验。

完成这些SOURCE/OFFLINE/LOCAL SDK后，由Main安排必要单场provider证据：固定输入/原owner→正式tool/SQL/status→只有真实grade reply→Native PCM及停止旧自由答案。设备播放与真人仍分别待验，不开mic/loopback。若取消/关联因proxy行为仍局部阻塞，先交付权威成绩与诚实文字回执，记录具体恢复条件，继续其它Goal工作；不把受限首版声音当已修全Goal。

本报告完成后冻结，无新执行或修改其它文件。
