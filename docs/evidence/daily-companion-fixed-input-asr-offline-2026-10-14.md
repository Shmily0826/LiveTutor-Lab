# 固定内存输入：实际 Core 授权与 PCM 入队回归

2026-10-14。已完整读 contract/plan/status/blockers 最新阶段十二段。既有 Goal active；阶段十一0bcf5ca已发布，26真实场无provider输入是Main既有证据，本轮不重跑或推断其具体lease payload。额度594/2000、app57、tech0仅承接最新记录，不查询/修改账本。

本任务只新增 `scripts/test_neko_fixed_input_authority.py` 和本报告；生产 host/patch/manifest/probe/接续文件均未改。没有启动服务/API/供应商/Native/声音设备，无房间或虚拟 capture、回环、WAV播放或系统音量操作，没有派 Agent。

## 结果：SOURCE / OFFLINE PASS，8项

最终执行命令（项目根目录 PowerShell）：

```powershell
& 'benchmarks/raw/neko-product-host/.venv/Scripts/python.exe' -I -B -X utf8 scripts/test_neko_fixed_input_authority.py
```

最终 exit0：`Ran 8 tests in 0.158s / OK`。仅新8项，不运行旧 barge/phrase 全批；调整夹具隔离和清理后仅重验本文件。

实际部署 `main_logic/core/asr_runtime.py` SHA256 为 `b44ccbf261283e6f20396c7ce0de5d9004159b3aa460faf6c5b3068c7c83ad9e`；新增测试 SHA256 为 `3eed809e900ac5dea974b56857cebd5ab04d8b45b5318bb78023d61edd9cbec9`。测试调用真实源方法，不是始终True的授权函数。

|检查|实际结果|
|---|---|
|synchronized `owner=none`|真实 `_ensure_voice_input_session_authorized(current_connection)` 返回True；owner与generation仍none/1，真实 `_voice_input_accepts_pcm` 为False，真实 `_enqueue_audio_stream_data` 不入队、不启动worker。|
|合法当前 core lease|真实 lease_sync generation1、bool mute/focus和builtin core registry匹配；session授权True，PCM gate True，真实duration queue有1个frame，token含当次connection/generation且匹配当前，随后精确清理。|
|相同/低generation|none generation4建立后，3和4的core请求均False，owner/generation/route generation不变、不入队；5可恢复core。|
|旧connection|新connection重新claim+sync后，旧connection的session授权/socket重定向/revoke均False，不能清新owner；旧ingress token不匹配，新connection仍可授权。|
|mute/focus|三个bool组合均允许已有同步session授权但PCM gate False、不入队；下一严格递增无遮挡快照恢复且无旧帧重放。|
|registry身份不一致|lease owner为core但实际registry active consumer人为切到game，真实PCM gate拒绝；仅owner字符串不能准入。|
|game无当前route|真实lease切game并选择builtin game consumer；该角色没有active game route，实际registry不接受输入，suspend被调用，PCM不进入core queue；递增core快照重新选择core并恢复。|
|结束none/连接撤销|先前已入队frame在none transition被实际清除，旧token失效；当前connection revoke成功后id空、generation=-1、unsynchronized，旧connection授权False且不入队。|

源码关键位置：`_voice_input_accepts_pcm:1476` 校验真实registry namespace/name/capability及mute/focus/external suppression；`_enqueue_audio_stream_data:3459` 在入队前运行上述gate；`_apply_voice_lease_state:5158` 选择consumer、更新抑制、清旧PCM；`_revoke_voice_input_connection:5446` 精确connection撤销；`_ensure_voice_input_session_authorized:5478` 的synchronized早返回与PCM准入是两个条件；`_handle_voice_input_control:5512` 拒绝非严格递增generation。没有放宽这些生产方法。

## 夹具、隔离与一次导入副作用

复用 `test_neko_native_barge_in` 的 deployed HOST 与窄AST隔离方法。最终夹具从实际asr源码编译原 `AsrRuntimeMixin`、frame/duration queue/hot-swap buffer类，使用真实 `VoiceInputRegistry`、builtin Core/Game消费者及实际 `IndependentAsrRuntime`/token capture；`_voice_input_accepts_pcm` 和 `_apply_voice_lease_state` 明确断言为真实方法。

只有 provider lifecycle 的abort/suspend/resume被替换为可观察AsyncMock，worker启动被阻止以停在队列边界。不会运行音频preprocessing；实际 `VoiceInputAudioPipeline` 的processor是lazy，测试不调用process/捕获接口。只有固定160个内存整数，未产生测试录音或重复制作教学材料。

初版直接import现成 `tests.support.asr_fakes` 也8项PASS，但它拉入Core→Memory模块，触发应用文件日志初始化，并在Windows cp1252显示logging编码错误。这是实际发生的非预期导入副作用，已通知Main；没有删除、重置或覆盖既有用户日志。随后改为上述窄AST方式，最终新增检查拒绝 `main_logic.core` / `memory.recent` 已导入，避免重走此路径。最终运行只有既有ConfigManager配置读取/内存默认提示，没有Core/Memory日志初始化；原配置、用户历史均不在测试中修改。

## 支持边界与下一步

这是授权状态机和队列边界证据，**不是** frontend固定来源/controller实现、WS router整段来源身份、真实PCM upload/provider append、ASR/model、自然停顿、物理播放或真人通过。旧connection测试覆盖actual session授权/socket绑定/revoke/token，`_enqueue_audio_stream_data` 本身没有connection参数，不能借此声称旧socket完整router路径已测试。Game正向active route不在本文件支持范围，已验证的是实际无route时正确拒绝、不落入core。

Main前端参与者应使用同一controller实际生成的递增snapshot，绑定当次socket；不能借synchronized session-start成功当作core owner ack，不能手写大generation或伪造isRecording。固定输入结束必须通过现有snapshot切none/撤销，mute/focus/game/更换connection保持既有围栏。本Agent没有猜测或增加前端API。文件已冻结，Main负责后续frontend/整合及是否安排必要有界真实场。
