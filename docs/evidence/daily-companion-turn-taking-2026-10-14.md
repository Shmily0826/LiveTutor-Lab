# 自然停顿分轮调查与诊断候选

日期：2026-10-14，Pacific/Auckland。先读完整 contract、plan、status、blockers，保留既有真人普通打断证明。本阶段只做针对性源码、已有固定输入与既有日志调查；不启动宿主、音频、网络模型，不修改 VAD/取消/播放行为或共享补丁。

## 结论与支持边界

当前 `free` / `lanlan.app` 走 StepFun 形状的 WebSocket session，而非直接 Google SDK。在 `candidates/N.E.K.O/main_logic/omni_realtime_client/_transport.py:755` 的 free 分支，实际配置为 `turn_detection={"type":"server_vad"}`，没有沉默时长字段。`_client.py:511` 的 `_has_server_vad=False` 只表示代理不发送 OpenAI 形式的 `speech_started/speech_stopped` 事件；它不证明远端自动活动检测已禁用。直接 Gemini 路径的 `_gemini_support.py:212` 仅 MANUAL 时发送 `automatic_activity_detection.disabled=True`。

Google 官方 Live 协议确实提供 `AutomaticActivityDetection.silenceDurationMs` 和 `endOfSpeechSensitivity`，这些分别控制结束语音前的非语音持续时间和结束敏感度。原生支持不证明 Lanlan 的 StepFun→Vertex 代理会映射这些字段。[Google Live API reference](https://ai.google.dev/api/live#AutomaticActivityDetection)。本仓客户端未实现这种映射，也未找到可核对的公开代理映射源码。因此本阶段没有盲发 `silence_duration_ms` 或 Google 嵌套配置，没有把字段回显叫作服务实际采用。

当前可交付是**最小可重放诊断候选**，不是自然停顿已修复。功能调参仍需代理所支持参数或实际回执/边界测量证据。

## 本场已有证据

只读 `benchmarks/raw/neko-desktop-host.log` 的 launch `20261013T124927Z`、NZDT 01:49:27–01:51:44 窗口：

| 事件 | 日志行 / 时间 | 结论 |
| --- | --- | --- |
| 输入识别回调 | 47046 / 01:49:51 / len75 | 汇总中的93/9之前还有75；不能直接忽略 |
| 输入识别回调 | 47072 / 01:50:01 / len93 | 本地将代理 completed 事件直接交给回调 |
| 第一次 study_explain | 47076 / 01:50:02；47084 / 01:50:06.977 200 | 请求到回调返回约4–5秒，启动日志只有整秒精度 |
| 输入识别回调 | 47112 / 01:50:38 / len9 | 缺少底层 item/response 关联，不能断言是同一轮的尾片还是另一次识别 |
| 第二次 study_explain | 47122 / 01:50:38；47137 / 01:50:42.388 200 | 请求到回调返回约3.4–4.4秒 |

75→93 是否为同一 utterance 的更完整版本、重复事件或三个独立片段，现有日志不能确定。`_transport.py:3869` 将每个 completed 输入事件直接送 `_deliver_input_transcript`；当前固定场景未启用足够结构 trace，不能仅用回调长度反推服务分轮机制。

`benchmarks/raw/voice-input/daily-study-picture-20261014.wav` 为已有 SAPI 固定输入，不是录制房间麦克风。离线读取 wave header 得到12.272426秒、22050Hz、mono PCM16；driver 再加1秒前静音、3秒尾静音，与场景报告16.266秒输入时间相符（有重采样/分块取整）。10毫秒窗口的 raw RMS幅度量具：

| 阈值 | 首/末非静音 | 两段内部低幅度停顿 |
| --- | --- | --- |
| RMS100 | 0.200–11.494秒 | 4.111–4.989（0.878秒）、9.997–10.885（0.888秒） |
| RMS500 | 0.239–11.474秒 | 4.051–4.999（0.948秒）、9.967–10.885（0.918秒） |

这是幅度分段，不是 RNNoise 的语义语音判定。`_audio.py:186` 的本地静音清除使用 RNNoise 4秒回调或持续本地静音/4秒门槛；`_client.py:421` 的 local quiet 为2秒。内部两段停顿不到1秒，没有证据它们达到本地清 buffer 条件。服务端早分轮与这些停顿相容，仍属于**待验证推断**。增加本地 quiet、grace、PCM缓冲或延长输入静音不构成该线路的修复，也会混淆原普通打断证据。

原 `voice-fixed.json` 输入相对时基与 loopback first_loud 使用不同 origin；未做跨时基减法。主 Agent 的下一场统一 wall/monotonic/原生窗口 clock 后才能给输入结束→ASR→工具→首音频→实际播放的完整延迟。

## 候选实现与离线通过

新增 `scripts/neko_spoken_turn_patch.py`，仅在现有 `_wire_trace.py` 增加结构诊断：

- 客户端请求与 provider 报告区分；是否包含 `turn_detection` 单独标记。没有字段的 `session.updated` 不宣称参数接受。
- 仅白名单的数值/布尔/已知枚举参数；支持已有 flat/nested turn config 的检查，不发送任何新配置。
- 若服务实际提供 speech_started/stopped，则记录 `audio_start_ms/audio_end_ms`；completed 输入只记录字符数，不保留文本。
- 现有 send/recv trace 增加 monotonic 时间，与原 wall时间并列；保留 cid/gen/item/response关联、现有delta计数和audio append节流。

原客户端 trace模块 Apache-2.0，继续使用其日志/异常保护/结构白名单。候选不触碰 `_shared`、transport、RNNoise、取消、owner、PCM handoff和播放算法。默认只检查，必须显式 `--apply` 才写，源码锚点变化时拒绝；主 Agent 决定是否纳入共享部署补丁。

```powershell
& benchmarks/raw/neko-product-host/.venv/Scripts/python.exe -I -B scripts/test_neko_spoken_turn_patch.py
& benchmarks/raw/neko-product-host/.venv/Scripts/python.exe -I -B scripts/neko_spoken_turn_patch.py --root candidates/N.E.K.O
& benchmarks/raw/neko-product-host/.venv/Scripts/python.exe -I -B scripts/neko_spoken_turn_patch.py --root benchmarks/raw/neko-product-host
```

离线测试 **5/5，通过0.032秒**：重放幂等/未知版本拒绝、请求与provider报告区分、Google/nested字段白名单且无密钥/非有限值泄漏、边界offset/字符数保留且不存内容、双时钟及原audio append节流。双root只检查返回 `patch_available/policy_changed=false`；两份当前trace源码SHA256相同 `6c40e194d0c37ed3795ab93ad18bed9e32d3234e5902709f149a6534c3e594ce`，未应用候选。

## 下一次最有信息量测量

主 Agent 若采纳，显式应用诊断后开启既有 `NEKO_REALTIME_WIRE_TRACE=1`；使用原固定WAV，不新造测试材料。同步输入开始/末非静音/输入结束、底层transcript completed item IDs/字符数、session request及provider报告、clear/commit/response.create、工具完成、first delta、native播放回执。若服务缺少VAD/接受参数回执，如实记录 missing，不补造。

判断分支：输入仍在进行时出现不同 item 的 completed 且无本地commit/clear，支持远端分轮；同item连续75/93支持增量/重复通知而需查代理语义；本地clear先于尾句则定向检查已有静音缓存清理。取得线路支持的参数后才做单个有依据的候选对比，同时用受影响普通打断回归守住 speech onset→旧答抑制→新答的链路。

状态：源码/离线诊断通过；真实模型分轮修复、设备播放专项、真人自然停顿体验均未通过。本阶段新增付费调用0、额度调整0、线上宿主/音频进程0。主 Agent 继续其他Goal工作，代理参数支持缺口不构成整体阻塞。

## 统一时基证据后的最小 MANUAL 支持探测候选

随后只读主 Agent 的 `benchmarks/raw/evidence/daily-companion-20261014-native-timing.json`：provider 三次 completed 为 wall 1791896988.056（75字）、6994.017（93字）、6995.527（9字），固定语音末非静音为6994.506859；第一条在说完前约6.451秒到达。该窗口没有客户端 `input_audio_buffer.commit/clear`。因此早 completed 位于代理/远端链路，不由本地 quiet 清除触发；provider 未给 item_id，75/93的具体增量语义仍未知。最新统一时基结果与本报告先前的缺口区分，旧失败保留。

现有内部 `signal_user_activity_end()`（`_gemini_support.py:281`）在 MANUAL 模式复用原 response arbiter，按 `input_audio_buffer.commit` → `response.create` 顺序发送，等待原ticket，再记录输入边界。free connect原本就有 `is_manual→turn_detection:null` 代码；客户端注释不是proxy行为验收。主机公开WebSocket原本没有 `end_audio_turn` action；独立ASR的seal会调用内部方法，但当前free native不走该链，不能假设现有前端会自动seal。

新增 `scripts/neko_manual_turn_probe_patch.py`，**默认关闭，仅实验用途**：

1. `_transport.py` 在已有connect校验前调用新增 `_select_free_manual_turn_probe()`，只有 `NEKO_FREE_MANUAL_TURN_PROBE=1`、route=`lanlan_app_gemini`、`_is_free_proxy=True` 三项同时成立才选择原 MANUAL。环境关闭后connect恢复试验前模式；tech、directGemini和paid路由不选择此模式。
2. `websocket_router.py` 新增 `_manual_turn_probe_enabled()` / `_dispatch_manual_turn_probe()`；在既有voice-path分类、普通dispatch、superseded voice-owner窄dispatch三个锚点接入实验 `end_audio_turn`。**直接复用现有 `_owns_voice_connection()`，不使用 manager.websocket/display socket 判断麦克风owner**。只接受audio/native、匹配实验route/模式的实时session；有限request_id避免同一probe重发commit。
3. 同一个输入socket发送 `{"action":"end_audio_turn","request_id":"manual-support-1"}`，调用原 `signal_user_activity_end()`，不另建队列、端点检测或VAD。10秒本地dispatch上限，失败不自动重试，原session/mic owner改变会记录原因。`manual_turn_probe` ack带wall/mono和generation；**ack证明本地dispatch，不证明provider接受MANUAL**。

候选只生成增量补丁；本子 Agent 未apply，未改变实际候选树/部署。锚点：transport `async def connect` / `self._native_audio = native_audio`；router `def _is_voice_path_message` / `if action in {voice_input_control,voice_identity_control,pause_session}` / 普通与superseded两处 `voice_identity_control`分支。所有源码先AST校验，未知版本拒绝。

`scripts/test_neko_manual_turn_probe_patch.py` **6/6离线通过，0.587秒**：默认关闭及精确路由、显示socket改变后合法voice-owner仍可commit、disabled/stale/wrong-route/重复请求拒绝、实际原MANUAL方法的arbiter发送顺序、重放幂等/两dispatch锚点、await期间session替换及失败文本不泄漏。双root默认检查均为 `patch_available/enabled_by_default=false/automatic_endpointing_added=false`。这些不替代完整WebSocket owner回归或provider支持验收。

主 Agent 的最小support场景应在固定WAV末非静音后约1.2秒发送end，并裁掉旧driver的3秒尾静音，避免2秒本地quiet/4秒RNNoise清理先清缓存。观察：session请求显式null；人工end前有没有completed/工具/回答；end后原commit/create顺序有没有出站，随后是否只对完整语句出一轮有效解释。若null仍产生早completed，或commit不产生有效回答，保留失败并停止该候选；不进行无限重连。

**尚未新增 RNNoise 自动结束**。support通过后最小挂点是既有 `core/asr_runtime.py:_send_native_audio_pcm`：那里已经把RNNoise判定变成 `speech_active` 并交给实际session.stream_audio。可以在成功发送后，仅对确认支持的MANUAL free实例，按captured_at跟踪最后speech verdict，非语音约1.2秒且本轮有语音时单次调用原seal；新语音取消尚未seal的quiet候选，并按现有session/generation退休。该规则在本固定材料中保护约0.9秒内停顿；不能宣称覆盖任意更长自然停顿。必须保留已有onset/cancel路径，不改其门槛或延后普通打断，不缓存整个语句。当前只明确适配位置与后续条件，不在无proxy支持证据前实施。

本补充仍为离线/源码候选，新增外部模型/音频调用0，未改额度或开启房间麦克风。主 Agent 决定整合和一次受控在线support probe。
