# 材料替换后旧 Native 音频取消：限定接口审查

2026-10-14。只读核对canonical Study payload、宿主当前运行树源码和既有patch generator；仅新增本报告。不运行测试、CodeGraph、在线请求、音频、宿主、账本或进程操作，不干扰主线same-session语言场景，不修改Sky Scout/图片/HTML材料。

结论：当前Native material guards保护了取证、解释完成、数据库提交、live seed、返回与未调度的叙述；**不等于已排Native音频被取消**。最小可靠复用是“带材料身份的控制通知 + 匹配当前输出owner + 复用现有连接token精确取消与有界连接重建”，其中重建不能照搬真人barge-in的PCM回放。若要求同一物理连接立即继续新材料，则需额外输出身份与陈旧帧围栏；现有连接token不能直接充当材料token。

## 已有修改点与事件缺口

| 位置 | 现在做什么 | 与音频的关系 |
| --- | --- | --- |
| product `study_materials.py:10-25` | identity=SHA256(image + NUL + OCR/text)，同时绑定course/session；检查expected是否当前 | 不含音频owner；不含controlled surface的active_material_id或CodeGraph版本 |
| `entry_tutor_explain_entries.py:146-156` | submit_image在现有_lock内保存image/text，取得expected_material，写既有kv | **没有**旧identity→新identity的host控制通知；随后模型耗时期间已有音频仍可能播放 |
| product `__init__.py:797-830` | start/restart加载本课程材料，设置session/course/image/text | 换课/重启改变identity；没有Native取消通知。即使图片字节相同，新session/course也需要分开判断 |
| `study_avatar_tools.py:833-871` / explain entry / context finalizer | observe与锁内核对，模型/落库后再验，旧结果不更新新live seed | 主线9项离线Guard涵盖请求竞争；测试本身明确没有真实设备播放 |
| stock `entry_communication_tutor_events.py:14-70` | general_response_completed/solution_completed通过StudyEventBus调度叙述 | payload只有content/sections与可选target，**未携带material_context**；schedule成功不证明已送达或未在之后换材料 |
| stock `_event_bus.py:81-180,301-346` | 有silent/communication开关、节流、64队列和异步push_message | 教学respond/read事件不是可靠取消控制；日常部署默认communication.enabled=false，不能依赖它存在 |

现有screen_context_changed是OCR上下文通知，不是Native输出取消；本审查未发现已有材料替换控制事件可直接启用。Study网页的本地revision/AbortController也不能跨窗口清掉Native播放器缓冲。

## 可复用的宿主 / 前端接口

所有下列宿主路径相对 `benchmarks/raw/neko-product-host/`；实际交付应改generator/overlay，而非只改一个运行树。

1. **现有插件到main事件通路**：`plugin/server/messaging/proactive_bridge.py:348-529`保留push_message.metadata，派生可信source_kind=plugin、source_name=plugin_id，支持ai_behavior=blind→silent；`app/main_server/character_runtime.py:_handle_agent_event`消费该proactive_message。blind + visibility=[]可不显示、不注入LLM，但bridge只有text/media或HUD时才生成event，因此控制消息需要一段非空固定marker文本，不能仅发空parts/metadata。在main侧早于普通聊天/叙述处理截获指定来源的控制metadata，再return。此为**可实施复用建议**，当前不存在材料控制handler。
2. **工具结果绑定点**：`main_logic/core/tool_calling.py:_on_tool_call`持有invoking_session，真实registry.execute返回后可读ToolResult。当前结果没有把material_context绑定到宿主Native输出；需要插件成功结果附小型identity字段，宿主仅接受可信study工具来源，并记录该工具所属session/connection/scope/output身份。模型产生的metadata不能当可信owner。pending模型期间的旧结果已由现有guards保护，先覆盖成功结果对应的在播旧音频。
3. **退役工具任务**：`main_logic/omni_realtime_client/_tools.py:_advance_tool_scope`使scope递增，取消当前task/batch并标retired；`note_user_turn_started`调用它。它不会清前端音频。材料控制应用独立reason，不能伪造真人speech事件；调用后要处理尚未回应的tool IDs，沿用已有abandoned/no-continuation释放逻辑。
4. **provider响应取消**：`_transport.py:3299 handle_interruption(connection_still_ours=...)`带connection围栏，但仅_is_responding时执行，主要处理生成状态/terminal欠账；已有audio queue仍独立存在。`cancel_response()`在free/Gemini不等价于物理provider连接隔离，不能只发一次就声称旧音频已停止。
5. **精确Native播放器取消**：`scripts/neko_native_barge_in_patch.py:203`的cancelNativeConnectionPlayback(token)，由app-websocket的game_route_speech_cancel分支调用。它停止匹配token的scheduled sources，过滤解码/等待blob队列，并永久加入retiredNativeConnections；迟到decode/frame不能再播放。**token是physical connection身份**，不是某句话或材料；原路径随后close+connect，获得新的native_connection_token。
6. **已有有界close/connect和frame顺序**：native patch `_recover_native_barge_in`先取session-swap锁，再取 `_ensure_audio_frame_send_lock`发送精确cancel，close旧source，调用 `_restart_message_handler_after_session_reconnect(..., start_listener=False)`，connect新连接。每个await之后检查session/socket/activation generation。真人路径还验证/replay PCM候选，这部分不适合材料替换。
7. **通用user_activity与TTS清理**：`core/notify.py:116 send_user_activity(interrupted_speech_id)`能通知前端，app-websocket:1971实际清所有当前scheduled/queued audio；`core/tts_runtime.py:_interrupt_tts_now/_let_tts_interrupt_land/_finish_tts_clear`处理本地TTS队列。两者不能单靠一个旧speech_id保证不会清新音频：host必须先核current owner，并与frame/输出切换串行。不要调用`interrupt_ordinary_speech_for_takeover`作为shortcut：它要求_takeover_active并涉及manager-wide状态；也不要调用_reset_native_audio_turn，因为它清输入PCM，不是材料输出取消。

## 最小分阶段方案

### A. 先建立跨进程材料身份通知

在submit_image与课程/session setter的原_lock内，捕获完整before/after context；只有已接受的变更才生成控制记录，在锁外发送。不要在invalid image/拒绝expected_course时取消音频；相同image+text且同course/session的重复提交可幂等，不取消。

记录只包含plugin实例随机boot_id、递增change_seq、target角色、before/after的course/session/hash及reason，不放图片、OCR正文、钥匙或绝对路径。由插件自己的ctx.push_message发送固定marker、ai_behavior=blind、visibility=[]和control metadata，独立于教学叙述的communication开关与30秒cooldown。提交失败必须显示/记录“材料已接受、音频取消未送达”，不能伪称停止；没有target/旧输出绑定时不广播取消所有角色。

宿主在既有事件消费点校验host派生source_name/channel与control kind；检查boot/change_seq、before身份等于已绑定教学输出身份、连接/session/socket仍是捕获owner。晚到A→B事件不能取消已经在讲C的音频；重启后的旧boot事件拒绝。必要时重新查Study当前轻量context确认after，不能把push_message submitted当cancel ack。消费控制时先同步封住旧输出，再await网络/队列动作。

### B. Native free路线的保守首版

复用连接token取消和已有有界session-swap骨架：准确旧owner通过后，scope退役、旧source禁止继续输出，frame锁保证cancel不拆header/blob对，向捕获Native socket发送旧connection token cancel；旧连接退役，并在需要继续Native学习时只进行**一次**有界重建。新连接的token由原connect产生，新材料通过现有Study工具重新取证，不复用旧reply。

单独的material-replacement方法可以复用相同基础操作，但不要直接调用_begin_native_barge_in_handoff：它要求实际speech候选、MicLease/PCM回放、可能触发新的CONNECT，也会对输入缓冲做处理。材料变化不能伪装成真人发声，不能重放旧课程PCM。保留普通真人打断路径；在swap/mic讲话竞争时遵从既有swap/activation owner，不抢新连接。

若不准备此时重建，可先将旧Native连接明确退役/停止，把状态显示为“材料已更新，语音待重新就绪”；这只能交付“旧音频停止”，不能声称同连接无缝恢复。恢复失败、限流、超时停止重试，按服务退避；连接计数由主线管理。

### C. 同连接连续恢复需额外身份，不能假省改动

直接发送现有native_connection_取消又保留原连接，会使新材料音频仍命中永久retired token而静音。随意在同连接旋转该token则改变physical owner合同，已in-flight decode与playback反馈可能被误认证。只设置_interrupted或调用send_user_activity也不够：free Gemini后续事件可能释放_interrupted，迟到旧生成音频又被当当前发出。

若产品要求不重连，应新增**输出response/epoch**身份而保留physical connection token，逐frame/异步decode/playing source带epoch，并让取消只退役旧epoch；重新准入必须证明是真实新响应，不能按“隔了一段时间”或新材料hash把旧delta升级。provider缺稳定response/item身份时，这条路线仍有协议级限制，应作为后续方案，不能冒称现有owner接口已解决。

## 文件范围与最小验证

- canonical product：`study_materials.py`（通知记录/身份helper）、`entry_tutor_explain_entries.py`（成功setter通知）、`__init__.py`（课程/session变更通知）、`study_avatar_tools.py`（成功结果身份）。若覆盖communication queued narration，再overlay `entry_communication_tutor_events.py`携带相同context，并在真正叙述准入处核对；只在emit前检查不够。
- 宿主patch generator：扩充已有 `scripts/neko_native_barge_in_patch.py` 或同机制的新小generator，涉及 `app/main_server/character_runtime.py` 的blind控制早拦截、`core/tool_calling.py` 的可信工具结果绑定、`core/asr_runtime.py` 的独立material cancel/swap helper；按现有generator升级两运行树并刷新manifest。不要写未经生成器覆盖的临时部署改动。
- 已有app-websocket/app-audio-playback取消接口可直接服务“退役旧物理连接”首版，无需UI全面重写；若改同连接epoch，则必须同时改这些delivery/decode/queue点及header生成，不能只加产品四文件。
- 先做无外部请求的真实方法场景：成功/无效/相同材料提交、换课、A→B→C晚事件、旧boot、不同角色/socket/session、取消发生header已发blob未发、cancel后迟到decode、cancel await期间新的owner、失败通知/超时、普通barge-in交叉。所有预期都是准确旧owner退役且新owner不受影响。
- 后续由主线仅安排一次必要实际设备场景：旧材料回答已开始/已排音频→换成现有另一PNG→看到准确cancel及回环旧声停止→新token/新材料回复。必须分开SDK/源码Guard、DOM缓冲停止、回环实际停止、真人听感；静音或窗口就绪不是全部通过。无需重跑已有材料guard九项或E几何批次。

## 当前交接边界

本报告是接口/方案审查，未实现取消、未新增测试通过、未新增设备或模型验收。主线continuity10英文→中文已取得部分证据，但Sky既有HTML虚线“天气未命中”被读作“天气命中”是密集小字失败；它与本取消审查独立，未为此读/改图或源码材料。只新增本文件，冻结交付，原数据、共享源码、账本和运行进程均未动。

主线在最后审查后补单一destructive-commit分支：cancel已发送导致旧physical token永久退役时，如果同连接仅新user epoch到达，不能静默保留fatal或清flag冒称可继续。现在在精确旧physical owner仍相同的条件下关闭并明确『材料已更新，语音未能恢复，请重新开始语音。』，无自动connect；如果真实新connection已接管仍拒绝晚cleanup。第22项离线负例验证这一待显式重启状态，未冒称无缝接续或设备通过。原P2的静默黑洞源码/离线路径已解除，本条是主线新增证据，不冒充子Agent重新跑测试或设备验收。

## 新宿主patch与离线量具：限定增量审查

随后主线新增 `scripts/neko_material_audio_patch.py` / `scripts/test_neko_material_audio.py`。本轮仅阅读这两个文件并追加本报告，不修改源码/测试或学习记忆Agent的产品文件，不运行测试、宿主、音频、在线模型或账本。主线提供的初始13项结果是**patched实际方法 + owned fake provider/socket离线通过**；本审查不是独立重跑，未部署/真实模型/设备结果不能由此认领。

### 已实现且审查未发现主路径错误的部分

| 重点 | 实现与测试证据层 |
| --- | --- |
| actual batch owner / unannounced turnpair | `_capture_study_material_tool_owner`优先取 `_tool_batch_entry_by_task[current_task()].owner`，验证call ID及abandoned；不重采原实际batch的turnpair。已有针对“重采会返回错误pair”的离线测试，保留同一owner对象 |
| 可信binding | 仅study_explain、registry来源plugin:study_companion、当前Native free无server-VAD/session/lease有效；成功reply中的binding严格核v/boot/seq及小型context，is_error/degraded/ok=false不绑定。identity不给provider继续消费，避免模型改写provenance |
| control先于result | control先存每boot最新seq；迟到tool结果绑定后重新应用更新seq的control。boot最多4份、旧seq不能覆盖新seq，A→B通知漏掉而后B→C也能退役A；新C binding不会被迟到B取消 |
| 材料匹配范围 | explicit text binding可只有course/session，同课仅换图片不会误取消；换course/session仍取消。完整图片context含material hash。事件需可信plugin来源/指定target/blind/空visibility，拒绝后直接return不落入普通LLM处理 |
| 当前scope/connection/socket/activation | `_apply`在启动swap前按actual owner核这些字段，并拒绝barge-in pending/已有material replacing。针对不同scope/connection/socket/activation/session及barge的负例存在 |
| 当前binding工具被scope退休取消 | swap是独立create_task，先登记完成回调，再note_user_turn_started，外层await shield；绑定调用者被cancel不会把swap一起cancel。已有owned fake provider延迟connect的负例证明设计意图 |
| frame与有界恢复 | swap锁后再取原frame锁，保证cancel不拆audio header/blob对；旧token准确发送，source.close、listener drain、单次connect、listener restart。正常源码只有一个connect位置，没有for/retry或PCM replay。超时路径至多补一次cancel并关闭自己的失败连接 |
| connect异常后的清理 | connect的finally更新owned_connection，使自身connect已推进generation后抛错时仍清理这一连接；测试明确closes=2/connects=1，停止重试、swap锁释放后再disconnected。不能由这个fake provider结果推出真实proxy支持/扬声器已经停 |

普通onset、VAD门槛、PCM处理和barge-in回放函数没有被新patch改写；新增控制调用原note_user_turn_started退役工具，不伪造说话帧。

### 本审查发现与主线修复中的窗口

**P2 同连接新输入接管后，旧swap仍执行。** 最初current()只核session/socket/activation/route，不核新用户turn。等待swap/frame锁期间同连接新输入推进scope，旧材料任务仍能cancel/close。直接固定tool scope不可行，因为正常source.close与connect也主动退役scope。主线已添加独立 `_study_material_user_epoch`：仅原note_user_turn_started追加同步计数，_apply自己retire后取epoch，swap current逐await核对；新增等待frame锁时新input及late listener restart两个负例，还有实际note方法不因普通provider scope退休而加epoch的检查。**源码核对已解决此身份缺口**，本审查没有执行新增测试；主线通过数量另录。

**P2 同连接新owner可能继承材料任务设置的fatal。** _apply在等锁前设置 `_interrupted = _fatal_error_occurred = True`。若新input推进epoch使swap.current为false，任务返回且failed_ours=false，finally只清material-replacing，不撤销自己安装的两旗。原新增等待frame负例只核没有send/close/connect，没有核fatal残留；fake Provider的note方法不清fatal，源码上可见此残留，真实PCM也有fatal拒绝路径。已即时通知主线：采用材料专属输出抑制latch，或精确记录自有gate的安装/撤销而不撤销真正provider fatal、barge-in或新owner gate；补“新owner继续可用、无材料fatal残留”检查。**当前阅读版本尚待修复**，不能据离线数量标全通过。

**P2 listener await之后需再次核物理connection。** 最初drain listener返回后只核current()，它不含connection比较；同source/socket/activation下物理connection已被其他任务替换时，旧material任务可能再次connect覆盖它。final listener返回后也要核current及owned_connection，再设置session_closed_by_server=false/success。已通知主线两个位置独立加connection围栏，不可盲目采当前connection当自己的。当前阅读版本已加**final listener返回后**connection核对，**drain→connect之前**仍待补。

以上是限定源码层发现，不是实际用户事故；审查未安排新的在线尝试。发现已实时反馈，不因本项局部缺口结束长期Goal。

### 尚未由这组离线测试证明的部分

- product事件实际生成→plugin bridge→target manager、成功SDK结果的binding字段与真实batch lifecycle还需主线整合；这组测试替代了registry/transport/provider/socket，不能冒称跨进程通过。
- browser永久退役旧connection token、晚decode停止、设备回环旧声停止、新连接实际恢复均没有本轮实际证据。
- boot/seq可防陈旧通知，但不提供控制消息送达ack；主线产品sender失败/异步换课需仍明确状态，不把submitted当音频停止。
- material cancel会重建physical connection；不回放PCM意味着更换期间的语音输入不能默认为已完整保留，需界面就绪与真实输入/播放分别核验。仅一次connect不等于免费或语音稳定性已通过。
- 目前binding仅study_explain，Study quiz/answer、独立communication queued narration与controlled surface源码选择不在自动覆盖范围；不能把这一实现扩称所有学习音频都按材料取消。

## 最终限定复核：等待阶段与晚完成围栏

主线后续修订上述generator及离线测试，本审查仅重新读取这两个文件的相关位置。下列新结论覆盖上节同位置的“尚待修复”，不抹去发现过程。

- **等待锁时残留fatal/interrupted已解决（源码/离线）**：_apply不再设置provider fatal/interrupted，改为专属output_hold={connection,user_epoch}；Core._tts_output_is_current仅暂停对应旧Native输出，输入不因材料等待被fatal阻断，TTS不受该hold限制。finally只清仍是自己安装的hold对象。新增等待frame时新input负例断言fatal/interrupted=false及hold释放；实际tts_lifecycle方法fixture检查旧输出暂停、新input或TTS可继续。主线报告19项离线通过，本审查未重跑。
- **listener到connect及final完成身份已解决（源码/离线）**：drain await后核current和原connection，再connect；只接受exact original+1，不把更高generation盲目收作自己的连接，失败清理的owned_connection被限制在自有范围。final listener await后核current/owned connection再设置恢复成功。两项物理connection接管负例存在。
- **cancel send await后误关闭新连接已解决（源码/离线）**：frame锁内发送旧token后，释放锁、source.close之前再核current/原connection；主线新增send期间替换connection负例，旧任务不close/connect新physical owner。
- **失败状态await后误断开新连接已解决（源码/离线）**：释放swap锁后发送失败status，返回后再次核current/owned connection才disconnected_by_server；主线新增status发送期间新connection接管负例。主线报告最终21项离线通过，本审查未独立运行。

normalize只接受已知draft helper的精确SHA，未知改动拒绝，当前helper不二次重写；这是源码核对。双runtime精确更新、4新host目标fresh LF replay/AST/deployed byte/idempotence通过是主线提供的部署检查，不是本审查启动或验证当前服务。产品Agent11项通过属于独立产品侧证据，本轮未阅读/修改其4个独占文件。

### 已提交取消后的同物理连接新input：需明确恢复边界

最后发现并即时反馈另一种不同于上述“等待阶段”的条件：若frame锁内已设置fatal/interrupted、已发送永久退役旧token的cancel，而send await期间**只发生user epoch推进、物理连接未替换**，新增current检查会退出；failed_ours因epoch变化为false，不close、不重建、不发失败status，材料hold虽释放，当前旧连接仍可能fatal且token已永久retired。已有21项中的send负例覆盖physical connection确实替换，没有覆盖仅新input推进。

此为源码层条件性风险，未在线触发、未声称真实用户已遇到。已建议主线补一个send callback仅note_user_turn_started的定向离线场景，确认结果是明确可恢复状态：在仍精确拥有旧physical connection时有界退役/提示重新就绪，或取消开始后不把旧连接内到达的输入视为成功接管；不能只清fatal，因为renderer token已永久退役。新的真实physical owner始终不得被旧任务关闭。

本轮限定复核到此冻结，不追加在线、音频、host或测试运行，也不扩大审查。已修位置可标源码/离线通过；跨进程真实模型、已排Native音频DOM停止、实际设备旧声停止与新材料恢复仍PENDING，不能因21项或部署哈希通过升级。上述最后恢复边界由主线决策/后续证据接续。
