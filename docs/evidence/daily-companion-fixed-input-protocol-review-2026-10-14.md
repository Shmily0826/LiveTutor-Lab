# 固定输入控制协议窄审

2026-10-14。已完整读取 contract、plan、status、blockers、audio-work。Main 最新交接阶段十五已发布 `e34c2f94725f968dca523b87be70be18c5b59ff5`；四记录中较早“准备发布”文字不能覆盖该交接。当前允许必要时用户所设约4%扬声器，仍禁麦克风/物理或虚拟捕获/回环；本子任务没有任何服务、API、模型、设备、声音、测试、账本或用户数据库操作，也没有派 Agent。

只读 Root 实际 runtime router、ASR 最必要 callee、固定来源生成器、actual capture controller、Native observer 和两个直接模板；Root 无索引时沿用 rg。只读取 public output-only/fixed-input/review 及 phase14 blockers 中27/28/29摘要，没有扫描录音、读取raw DB或原学习 history。唯一写入本文件，**SOURCE REVIEW，不是新的实际准入或自然停顿验收**。

## 当前精确结论

1. 当前固定来源通过实际 controller 发送的 `lease_sync` **没有确定的缺字段/错误字段**。generation2/core 的本地 receipt 不能证明服务端收到同一帧或此时仍归该连接，但不能据此猜更大 generation。
2. `invalid_or_stale_control` 是几个互不相同的校验失败共用 reason；它不直接表示 registry、mute、focus、provider、PCM 或 VAD 拒绝。27记录不足以唯一归因服务器计数回退或多 renderer。
3. 有一个可确定的 observer 选择 P2：只把 chat 排后，没有排除 chat。pet未ready时，chat共享模块可满足当前 predicate 并被选为“audio renderer”。这是源代码条件性错误；**未证明27/28/29实际选择了错误 renderer**。
4. 在现有资料下，最小可执行推进是实际 JS→router→ASR 的纯离线联通序列与更精确的非敏感拒绝快照；不需要 paid CONNECT、完整WAV重放、修改MicLease准入或增加音频权限。

## 服务端准确的拒绝条件

`benchmarks/raw/neko-product-host/main_routers/websocket_router.py:1439–1455`（当前显示 owner 路径）及 `869–899`（全局session被新窗口替换、仍有voice lease的窄路径）都调用实际 `_handle_voice_input_control`，把任意 False 映射为 `VOICE_INPUT_CONTROL_REJECTED / invalid_or_stale_control`。两处传入 event、lease_generation、owner、hard_muted、focus_suppressed；engaged由router单独处理，不作为ASR方法参数。

`main_logic/core/asr_runtime.py:5521–5577` 的 False 分支只有：

| 条件 | 精确位置 | 含义 |
| --- | --- | --- |
| `int(lease_generation)` 抛 TypeError/ValueError | 5523–5526 | 缺省 -1 不是此分支；字符串/非数字形状不一定都同类。 |
| 转换后 `generation <= self._voice_lease_generation` | 5527–5528 | 同 generation 重放或低计数都拒绝，不能按同counter幂等重发。 |
| normalized event不在7个既有事件内 | 5529–5539 | lease_sync、hard_mute/unmute、focus_suppress/resume、game_takeover/release之外拒绝。 |
| lease_sync owner不是none/core/game | 5540–5543 | 缺owner也拒绝。 |
| lease_sync hard_muted或focus_suppressed不是bool | 5544–5548 | null/缺字段/0/字符串false均不能代替真实bool。 |

校验后先写 generation/synchronized，再 await `_apply_voice_lease_state` 并返回 True。mute=true、focus=true、owner=none 是**合法但不允许PCM的状态**，不会单凭其值返回这个拒绝码。registry是否匹配、preview隔离、route可用性和PCM suppression在后面的入队/transport判据检查，不能把该reason当作那些失败的证据。

方法在验证前设 `control_seen=True`；一次非法 control 后不能再假定 legacy未发control的启动兜底仍有效。`_ensure_voice_input_session_authorized:5488–5489` 对 synchronized 返回True，不等价于 owner core或PCM准入。原8项ASR离线证据已经覆盖none可启动但不入队，不应再将session_started认领为成功。

## 与实际前端字段逐项对应

`scripts/neko_output_only_patch.py:39–64` 的 begin登记本地 `{id,socket}`，调用原 refresh，再读state；没有设置isRecording或打开捕获。实际已部署 `static/app/app-audio-capture.js:334–388` 的 sender：

```javascript
{
  action: 'voice_input_control', event: 'lease_sync',
  owner: state.owner,
  hard_muted: state.hard_muted, focus_suppressed: state.focus_suppressed,
  engaged: state.engaged, lease_generation: voiceLeaseGeneration
}
```

`currentVoiceInputControlState` 的mute/focus都是 `===true` 布尔计算；fixed source令owner=core、engaged=true（349、433）。`sendVoiceInputControlState` 在 fingerprint改变或force时递增闭包内 private counter，随后发布receipt counter；`fixedInputState` 的再次refresh在状态未变时不重发同counter。

新的正常socket-open：`app-websocket.js:2835–2853` 只对仍为S.socket的对象发 `voice-input-socket-open`；capture `381–388` 重置该连接私有计数并force发 idle generation1。router `1416–1426` 忽略 never-engaged 的 engaged=false idle帧，不夺voice claim。begin后发布 core/engaged=true generation2，claim首次 `_begin_voice_input_connection:5312–5334` 把server scope初始化为-1，因此在无其他事件的正确单连接序列中，generation2应通过。end释放生成下一owner-none snapshot；它是合法撤销，不是错误。

`sendFixedInputControl`（generator `81–96`）发送start/end/end_audio_turn/ping，本身不造第二套 lease generation。实际PCM只从固定票的确切socket提交，1–480 int16，原普通upload判据仍检查；不需要在每个PCM JSON再添加lease字段，入队token由服务端当前控制面形成。unknown command/过期票/换socket仍拒绝。

所以不能建议“补缺的engaged/mute字段”“把counter改成时间戳”“忽略拒绝”或将isRecording设true。当前最关键缺口是**真实跨层消息对应关系的证据**，不是已经被定位的字段错误。

## 连接和计数竞态：哪些已可排除，哪些仍待证

router `961–1017` 先区分global display/text identity和voice lease。只打开新chat窗口使global owner变化，不等于voice失效；仍持voice者通过窄helper控制/上传。新窗口真正engage才claim并重置voice scope，旧voice者后续不能重新抢回。旧连接被拒/关闭通常走 `CHARACTER_SWITCHING_TERMINAL` 或 vacated丢帧路径，**不能只用invalid_or_stale_control等价判断“旧connection”**。

在当前代码中，多renderer各有独立闭包计数，不能共享或搬用别的renderer的counter；但新的合法claim会先重置server为-1。因此“两个窗口各从1开始”本身也不足以推出stale拒绝，必须证明具体哪个帧落在同一voice connection scope。辅助窗口idle engaged=false不会新claim；已engaged窗口停止时的false则可合法更新自己的lease。

socket-open同步若被重复在**同一OPEN socket**触发，会重置client counter，后续gen1/gen2可撞server已经接受的gen2；这可以离线构造，正常onopen是否在27重复发生没有证据，不应当作实因。最小防护如确有复现可把计数reset绑定首次新socket对象，force resync只递增既有counter；不能未经联通复现就扩大修改原普通录音。

单socketrouter按消息顺序await控制再接收PCM，但另一socket可在callee await期间claim。现有`_apply_voice_lease_state`带transition保护，不能用离线methods各自PASS代替完整outer router handoff证明。新增量具必须采当前连接scope并验证旧来源失效，不加PCM replay或伪onset。

## P2：Native目标predicate允许chat兜底

`scripts/neko_native_telemetry.py:76–94` 仅筛当前task debug port上host48911的page，排序 `('chat' in url, url)`，随后选择 `socketReady==1 && !!window.appAudioPlayback` 的第一个。非chat pet若没ready，循环会继续到chat。

`templates/chat.html:644,656,662,690` 同样加载state/playback/capture/websocket；index对应410/427/433/460。因此 `appAudioPlayback` 存在不能证明pet renderer，chat可以满足predicate。这与注释“chat only proxy text”不构成权威身份检查。begin还能在chat的独立controller登记本地core；之后同角色socket会按原router规则争夺/被拒，不能视作输入设备问题。

可复现纯桩：给attach target list包含pet URL（socket未ready）和chat_full（socketReady=1、appAudioPlayback=true），stub其CDP返回；当前代码返回chat observer，不会抛notready。既有`test_neko_native_telemetry.py`主要验证send/id/expressions，未见该attach双target负例。

最小修法：绑定该task launch预期的pet URL/renderer身份，chat明确排除；只允许该pet目标的bounded readiness观察，pet未ready则报告notready，不降级别的renderer。保存选中target-id、safe URL、task-native boot/source、socket实例局部id；不查询用户Chrome，不按title或排序猜归属。这项在无CONNECT的stub/静态HTML条件即可验证，不需为了验证选择而开启音频会话。

## 原27/28/29证据的界限

- public `daily-companion-fixed-input-2026-10-14.md`：27本地active/id1/gen2/core/capture=false，服务端上述拒绝，随后停止，未完整WAV/ASR/教学/PCM。拒绝时完整control trace与incoming/current server计数未保留。不能还原未知payload或判定其中哪条校验失败。
- public `daily-companion-blockers-history-through-phase14-2026-10-14.md:25`：28 renderer未ready，29 observer bounded Timeout；没有session_start/PCM，账本未变。两次不提供27的lease实因，也不证明provider离线/自然停顿失败。
- 当前observer INSTALL跨socket累计events，而probe `309–314` 检查整个trace有任何拒绝即停；trace未给控制事件socket-id或固定票关联。早于begin的旧status/后来换socket的status可混为本轮失败证据。这是保守停止，不应删拒绝或继续发送；在新诊断中需明确标本次ticket开始时间、当前确切socket与对应recv范围，不把累计status一律归到新core frame。

## 下一最小离线验证与诊断增量

不重跑原15＋8全部功能批次。补一个真正跨层联通量具，使用已有actual JS VM fixture和actual router/ASR窄方法，capture API全throw；fake WebSocket只收集控制JSON，不构造音频设备或本地监听服务：

1. 把JS实际发出的 idle1/core2/state重复读/release3交给router同连接分支及真实callee；验证idle不claim、core2接受/registry core、state重复读无多余control、release3撤销。可仅用少量固定int16数组验证入队，不读/播整WAV。
2. 同scope接受gen2后重送实际同gen2，应确定得到stale；删除bool/非法owner分别产生shape失败。拒绝原因本地可与准确branch对应，不靠统一reason猜测。
3. 两renderer：pet持core时chat passive idle不改server；chat真正engage后旧pet不得借票/旧scope发送；旧voice仍合法但display更新时控制只作用旧voice路径。只测试这两个相邻身份边界，不增加自动重连。
4. 同socket重复open/reset和真正new socket reset分别复现；只前者可能计数撞同scope，后者在合法claim的新scope应接受；await期间handoff后旧PCM失效。
5. attach pet-notready/chat-ready必须fail-notready，两个ready只选精确pet；旧trace拒绝不可声称是新ticket的server响应。

若仍不能复现27，Main可在当前两处控制调用边界加入仅output-only/task-opt-in的sanitized诊断：event与字段type、incoming parsed generation、**调用前** current generation、当前voice connection是否为sender、owner/synchronized、明确拒绝branch。成功后await返回需复核仍同connection/generation，再记录accepted；不把旧snapshot作当前权威，不把诊断ack当ASR/工具完成。不要存PCM/密钥/聊天文本，也不新增DB/队列。

优先保持外部既有code与bool兼容，可增加有界details或task日志，不放宽校验。所有后续真实场由Main安排，在有新增诊断证据前不重复27 paid连接，更不重播WAV碰运气。

## 指纹与冻结

本轮只读SHA256：router `885f46820dedd424cad6b09e96be7ec299577b727b9582fde66b01dd8c134539`；ASR `b44ccbf261283e6f20396c7ce0de5d9004159b3aa460faf6c5b3068c7c83ad9e`；actual capture `918b4741fce4fe8396f8b0dc0dad7c764c5e413693cad630e1080fbb9876a641`；generator `d790de76de7626d678c2e4722c5c7efd70c88ed5e619dcc3081ee4ad9f0c0f11`；observer `d573eeb8f40499b0c7145931f1f768bc60104b39d642230e70dda99b2df32f88`。

当前SOURCE可确认协议齐全与observer条件性P2，实际27根因仍未唯一确认；provider准入、自然停顿、输出播放、human均不由本报告升级为PASS。仅新增本报告，冻结；Main负责最小修复/量具、manifest、部署、额度与必要实际场。

## 增量复审：同socket计数与跨层量具

Main新交接的初版跨层3项已复现 normal idle1/core2/release3、同socket重复open发低generation被server拒绝，以及新socket重建gen2成功；该复现仍**不是27实因**。Main随后加入guarded计数修复，并报告actual Node16、router→ASR新4及两树replay/source gate通过。本 Agent只读该增量源码和断言，没有执行测试或调用设备/服务。

当前`CAPTURE_ANCHORS`增加私有`voiceLeaseSocket`及sync前分支。只有readonly capture-blocked标志为true、已记socket仍与S.socket严格同对象时，重复open走`sendVoiceInputControlState(true)`，按已有counter递增；真实新socket仍设置socket并走原reset逻辑。ordinary模式标志不成立，仍按原逻辑reset，存该私有socket不改变ordinary控制结果。旧socket事件的`socket!==S.socket`和非OPEN拒绝在新增分支前保留；旧固定票换socket永久失效也保持。

`patched_capture`仍剥离完整精确anchors恢复known base SHA；新分支或helper被未知修改、重复、残留时无法恢复基线。旧known drafts迁移只接受原完整字符串，再核全文件base；apply先在内存计算web/capture并检查helper，随后写文件，没有放宽“看到marker即接受”。两树actual capture此时SHA都为`e9a53e8f552c2a3c12e6193baaaa04b683fa6d1c8ea26cbf40cc5ded5f669280`，generator为`8d43dec38f6568c3c4064db9dbdab6b0db07807d167349f7322c9af9973bec82`。

新量具确是actual controller JSON→actual router `_claim_voice_input_connection`及**current** control branch→actual ASR registry/queue；没有把授权函数mock为alwaysTrue。`neko_fixed_input_fixture.mjs`从原actual VM fixture提取，capture/output构造器全部throw，计数captureCalls；`neko_fixed_input_sequence.mjs`只输出JSON与小int16数组，不读WAV。`test_neko_fixed_input_protocol.py`在imports前建立temp并设置NEKO_STORAGE_*；Main交接初次import曾读旧store配置且未改历史的事实保留，不能把当时行为说成从未读取过旧配置。当前源码改为temp初始化，原基础fixture仍AST隔离Core/Memory，ASR lifecycle abort与worker启动是桩。

量具明确不包含完整router的outer display/old-connection guard、真实ASR transport、provider、renderer或操作系统设备。branch是AST直接抽取current分支body，test通过不代表新旧窗口夺权围栏已经联通验过；两个connection字符串和每connection dispatcher提供的只是该窄claim分支scope。真实samegen重放的第四项仍要求server拒绝`invalid_or_stale_control`，服务端没有被改为重复counter可接受。

### 残余P2：重复open的force sync仍可清掉进行中的输入

计数回退条件在before-PCM序列已收口，但当前同socket分支使用force=true，会额外发一个合法新generation；这不是无副作用的状态读取。actual ASR `_handle_voice_input_control:5570–5575`对所有accepted control传`force_abort=True`；`_apply_voice_lease_state:5202`无条件调用`_invalidate_voice_pcm_sync`，后者`5110–5127`退役utterance并清queue/cache；`5249–5251`随后abort/wait_idle。

可确定的离线反例：实际core2→实际小PCM入队→同socket重复open发core3。第三帧现在会被接受，但已有PCM和utterance被清、abort被调用；前端fixed票仍active，后半句可以继续发送，完整输入已不再有保障。当前新same-socket test只在无PCM时执行，断言generation3/无拒绝，未覆盖该风险。此处为SOURCE条件性P2，不是声称真实27或当前WAV已发生这个清理。

最小建议：同socketguard分支使用`sendVoiceInputControlState(false)`。与上一fingerprint完全相同的通知不再发新control、不改变counter/queue；若真实owner/mute/focus状态已变化，原fingerprint判据仍递增并合法清理；genuine新socket保留原reset，server实际重放同gen仍拒。不改变server准入，不让旧票复活，不重放旧PCM。

必须定向检查：core2＋已入队PCM后同socket重复open不产生control、不清queue、不多一次abort；真实新socket仍reset且old票拒绝；状态真变化仍正常递增/退役；ordinary重复open保持原行为。若Main本轮只修初始before-PCM计数，需明确中途duplicate open仍未保护，不能写整个该条件已关闭。

当前复审结论：**counter rewind的初始条件SOURCE/OFFLINE收口；完整进行中重复通知仍有上述P2待修**；原observer P2和27因果不确定保持。报告增量冻结，唯一改动仍为此报告，没有执行新量具或操作设备/服务/账本。

## P2关闭复核：重复通知不再额外退役PCM

Main已按上述最小方案修复；本次再次只读精确分支及新增断言，未执行测试。guarded、严格相同socket对象的重复open现为`sendVoiceInputControlState(false)`。原fingerprint不变时不send、不递增counter；真实mute/focus/owner变化仍由原fingerprint发送新generation，按原合法控制失效输入。genuine新socket仍reset+完整force首帧；ordinary模式仍走原reset，旧socket事件/非OPEN先拒绝，旧固定票不会因该分支复活。服务端方法未放宽，实际同gen2控制重放仍要求拒绝。

`neko_fixed_input_sequence.mjs`新增顺序确为core2→actual小PCM→sameSocket duplicate open；`test_neko_fixed_input_protocol.py:69–77`核只有idle1/core2两控制帧、server lease2、queue仍1、abort仅initial claim一次及无reject。不是仅检查counter值的弱替代。Node新增changed-mute例核新counter、hard_muted=true、旧票sendfalse；guarded unchanged/ordinary reset分别保留断言。Main报告跨层4及actual Node17 PASS，归 **Main SOURCE/OFFLINE**，本Agent仅核源码和用例，不独立重跑；outer display/old guard、真实transport/provider不在该量具证明范围。

generator迁移只匹配整个已知unpublished force-sync anchor＋完整addition，再替换为false版；替换后仍剥离全部exact anchors、核原完整`CAPTURE_BASE_SHA`。unknown修改不会因局部true/false替换获得放行。Main交接首apply拒未知force草稿、未覆盖，随后才加入精确迁移的过程保留，不声称此前自动接受或绕过预像检查。

最新generator SHA `379b2ae2f1247d152d6abd47eb9f3e706bfdb538b5fda2c22fe7260f44e2fea7`；两actual capture树同SHA `1428d0be9bb6eddf0b2710c22cf4903d62efdc08638a79cdc2011588747b7c8e`。本项 **SOURCE REVIEW CLOSED**。上节旧force导致queue清理的条件性发现原样保留，不再是当前该分支的P2。

Main另报告一次root-only、silent/offline Native自身root/socket1/modules/controller/guard ready，未begin、输入、模型或使用音频设备，launcher已按owned身份清理。它只证明该次观察面就绪；不外推为sameSocket device、provider准入或27根因已确定。本Agent没有运行该观察，原27失败不改。报告再次冻结，仍只有本报告追加，其他源/测试/manifest/用户数据/账本只读。
