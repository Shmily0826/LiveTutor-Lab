# Phrase adapter 新实现：只读复审发现清单

日期：2026-10-14。先完整读取 contract、plan、status、blockers。独立只读 `scripts/neko_phrase_input_patch.py`、`neko_phrase_input_transport.py`、`test_neko_phrase_input_transport.py`，以及实际候选 Core/session_lifecycle、asr_runtime、Omni transport/audio 的接入片段。仅新增本文；不修改源码/测试/manifest/其他报告，不运行测试、host、API、online、音频、账本或Agent。

What this change does: 新默认OFF adapter在实际DSP/VAD/onset后保留未发送phrase，取得明确Core输入授权，异步有界写raw PCM，分别记录本地接受与transport写入。正常日常线路和真实普通打断仍要保留；本次9项新离线、12项受影响普通native通过是 **Main报告的已有方法测试**，不是本审查重跑或模型/设备证据。

## Must fix：四项具体P2

### 1. legacy hot-swap batch 被实际Core标为single frame

**位置：** 候选 `main_logic/core/asr_runtime.py:4797–4806` 的 `phrase_frame=session_ref._native_phrase_mode_allowed()`；同文件 `_flush_hot_swap_audio_cache` 的joined批调用；`NativePhraseUplink.bypass_frame`。

**场景与问题：** legacy flush最多join五帧PCM、用最后一帧captured_at与首帧speech probability，仍经 `_route_microphone_audio_unfiltered`。当前Core只看mode_allowed便把 `_native_phrase_single_frame=True`，所以实际joined输入不会进入为batch准备的bypass；direct transport测试的single_frame=False不能证明这个真实Core批已保护。其VAD/时间来源不满足单帧collector假设，已有prefix和新buffer还可能形成不完整phrase。

**最小修复：** Core phrase_frame同时核 `not self.is_flushing_hot_swap_cache`；整段旧batch/其handoff输入走原单次路径，不混已写prefix和未发送suffix。补真实Core flush相关negative，不能只直接传False给client。

**跳过后：** opt-in支持范围与实际Core调用不一致，可能在旧cache交接中错误收集或误分quiet。

### 2. authority遗漏Core前端websocket对象

**位置：** `neko_phrase_input_patch.py` 的 `CORE_HELPERS._native_phrase_input_authority`；候选 `core/session_lifecycle.py:346–362`；driver `read_snapshot/current`。

**场景与问题：** callback owner_token只有 `(ingress, activation)`，snapshot另存的是client.ws/provider socket。保持这两个token/physicalconn但替换 `Core.websocket` 对象，read_snapshot仍相等，旧flush仍可成为current。实际音频目标/前端连接的对象所有权没有进入该快照；game getter没有补这个检查。

**最小修复：** 将实际Core.websocket对象加入immutable owner_token，在Core实际授权与write accounting回调共同核对。补真实callback在frontend socket替换时拒绝旧snapshot/不归新owner的negative。

**跳过后：** 仅provider socket/generation相同会被误当完整owner相同。该发现确认的是可复现源码条件，不声称本轮已发生设备误播放。

### 3. 普通close没有立即retire phrase缓存和writer

**位置：** 候选 `_transport.py:4552+` 的普通close及 `_detach_for_close`；patch目前仅给 `_on_connection_attached` 与 `_close_failed_transport` 加retire；driver preroll/watchdog生命周期。

**场景与问题：** 只有false帧的preroll没有watchdog；普通close后不立即清除。直接client.close且Core record还current时，close首个 `_cancel_frame_copies` await期间provider ws仍在，旧writer也没有同步retire。只依赖之后ws detach或100ms watchdog观察不能保证close的第一个让出点前已停止。

**最小修复：** 普通close首await前同步retire当前phrase driver，按原connection资源边界取消writer/清preroll；别让晚cleanup碰新owner。补preroll close和semaphore阻塞writer early-close两个实际negative。

**跳过后：** 关闭流程仍持有旧输入，且有close-await期间写入窗口；不能凭失败close hook声称所有close都退役。

### 4. 旧provider等待deadline可以杀掉已接受的新输入

**位置：** `NativePhraseUplink.accept`、`watch`、`waiting`和`note_boundary`。

**场景与问题：** A flush结束，waiting=(t0,sequenceA)。A无terminal；约29秒时学习者真实新speech B到来。writer已done，accept允许建立B的buffer，却保留A waiting；约30秒watch按A旧deadline fail，终止B当前buffer/连接。B自己的20秒collector期限尚未到，当前input marker已变化，使旧A terminal也不能释放它。

**最小修复：** 在明确真实positive speech、当前输入sequence确已变化时，只退役旧waiting计时；不伪造server boundary、不清provider buffer、不提升旧tool owner。或者必须明确拒绝B并诚实提示，而非先接受后让旧deadline取消它。补controlled monotonic + 实际driver方法的A-wait→B-input negative。

**跳过后：** 新问题可能被上一回答的超时终止，破坏连续学习。

## Main采纳状态：尚未独立确认修复

四项已直接发送Main。Main确认全部采纳，将分别做websocket authority、legacy batch bypass、close首await retire、真实新input仅退休旧waiting deadline，并加实际negative。本报告冻结时这些为 **Main待实施/运行验证**，不是本审查已经看到修复后的PASS。

Main另已主动处理两项已知边界：fail只置fatal没有close；动态route/capability切换时pending未发送缓存仍残留。Main拟精确核原ws/generation先close、status有界；dynamic mode有pending时明确失败。报告不抢改或声称这些处理已完成；它们也不能通过sourceNine被外推。

## 已确认的可复用保护

- 新Core共用 `session_lifecycle._bind_owned_output_callbacks` 实际安装独立phrase authority/accounting callbacks，没有误用game route getter；normal/pending构造仍走该绑定。record/current/active/native/corelease/input权限/fatal/providerws/physicalgeneration已有具体守卫，补上述Core socket即可更完整。
- Core actual `effective_output_commit` 同时用于stream_audio调用和False/None映射，collector接受的None返回LOCAL_ACCEPTED，不在帧入缓存时累加 `_omni_mic_audio_bytes`；raw flush成功才调用明确accounting回调。
- driver flush是独立task、8秒上限，epoch与snapshot守卫；实际 `send_event(send_guard=current)` 在semaphore等待后和最终写入前复核，物理新socket/connection不能靠旧batch继续发送。取消/失败不重试原batch。
- arrival-derived sample start/cursor只作用collector，旧audio_timeline_at/onset时基没有全局改写。watchdog使用monotonic只做现实运行上界；collectorseal仍由真实feed样本进展推动，没有拿延迟worker wall直接tick提前seal。
- clear在buffer/writer/provider等待仍owned时受保护；owned真实response boundary按expected input sequence释放。sequence只是已有输入marker，不是provider utterance ID。未宣称ASR片段必然一个或付费tool必然一次。
- pending/replay有明确原single-write路径与retire/bypass思路，连接attach会退役旧collector；但真实legacy batch入口和普通close仍须上述negative闭合。

## 有限审查结论

Verdict: 默认OFF保持；在四项P2及Main已知fail-close/dynamic-mode边界实施、实际方法negative通过前，不进入新的opt-in在线/设备场。只读审查到此收口，不扩raw tool排序逻辑或继续大范围搜索。

Not checked: Main后续修复/新增negative执行、provider burst/ASR事件、first-ASR工具顺序、模型末尾语言/noquiz/nosave约束、实际Native PCM/WASAPI、真人。Main原9/12测试和patch CLI check只属于源码/离线；本报告无新增运行证明，也不完成长期Goal。
