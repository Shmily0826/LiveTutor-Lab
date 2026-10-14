# 阶段37：完整Native观测与终态

## 已交付结论

本阶段是量具修复的 SOURCE/OFFLINE PASS，未启动模型、Native、浏览器或任何音频设备；不追认场49全链通过。6个源码/测试文件已完成Main与独立窄审，58项（18 telemetry＋27 acceptance＋13 probe）通过。原500事件renderer ring不扩大，Python连续采集保留至12000条，丢序/重载/改写/计数不符均拒绝；本地sequence不是provider utterance identity。

独立审查发现并实际AST复现一个P2：末段grace或SDK/截图await时observer失败，异常原先可能被finally gather吞掉，留下旧snapshot。已修为异常同步记录native_observation_error并设置failed/ended后重抛；每轮3秒grace后和最后截图/SDK查询后fresh capture，前后核task健康。最终check到cancel无await，正常主动cancel/gather/置None后才end_session。四项实际AST异步负例覆盖grace gap、末尾fresh gap、snapshot await期间task失败和正常取消。独立closure见[审查报告](daily-companion-native-observation-review-2026-10-15.md)。没有剩余具体P1/P2。

终态判据仅在完整sequence/frames/bytes及真实同token source_ended/queue0/done、后无新增PCM/text/active播放时，保留稍后空队列cancel之前的正常结束证据；缺历史或任意cancel仍拒绝。原49 raw与PARTIAL保留，短反馈22→7字符仍UNKNOWN，见[边界报告](daily-companion-feedback-boundary-review-2026-10-15.md)。物理声音和human均未验。

最终SHA256：telemetry `3d87fe07ee45b3ccebb8ca4f63e4b4a9b148e9a17664afba10535f25603e598f`；probe `2f38d62d9fc548789ae2e8e95b2ebbf6f8b5f0a6244d272126f298352c7c0290`；acceptance `f6b921e4bc855602c286daaca6caf3fbdcab90f16832dc4b95c2966aaf33f079`；对应tests `645cef6693aba5258c0e118ac1bddccad458510b0d38c2581a2ef03e06720075` / `6ed8614320f7bc3c0f8553a5797be4a504d6ccf9d18e9972814260f09d9114dc` / `59b542c71e3bb4e09baa504df33e1545255246c117f7b2888eee2a86e398242f`。

账本当前核对仍bargein-autocheck-20261012：DS785/2000，app74/null，tech0/0；未重置。无live host/exec。下一阶段38先补既有WIRE_TRACE下不含正文的len/hash诊断，区分正式reply、owned relay实际write、provider原始delta、Omni callback和Core发布；先离线核实际调用点/隐私/不影响原路由，再仅必要在线。A–F、AUTO默认OFF、集中human条件继续。


阶段37启动：上一阶段发布7e3c233c204660b6401a20814896cf256ab08acc以及49实际唯一grade/同conn是progress，不是wait。已完整重读contract/plan/status/blockers，源码及ledger785/74/0当前核对，Root index空/publisher clean，无live exec/host。Main仅本地修量具，不重复付费跑49，不使用任何音频设备。

Main观测草稿5文件：NativeTelemetry原500ring增加严格本地observer_sequence和device remainingSeconds/updatedAt；NativeTraceHistory逐快照积累最多12000events，同安装时间/连续seq/重叠内容/总PCM frames+bytes一致，发现漏轮/重载/容量/计数不一致立即拒绝，不补造事件/不重置binary计数。初始、sessionready、observe都接同History，3轮snapshot保留真实累计历史，仍只task renderer/8API保护，不接管用户Chrome。不是provider utterance/ASR authority。

Native terminal判据保留旧final sourceended；只有新增完整seq/counters历史、实际device sourceended/queue0/正确token/done、后无PCM或文字或active状态，才把后来空队列speech_cancel与已正常结束分开记证据，不允许任意cancel冒正常结束。Main telemetry18+grade acceptance27+preflight9离线PASS（JS真实INSTALL在no-device fixture重放750events、gap/改写/counter/overflow拒、latecancel负例）；独立observation-review进行中。未重算原49，真实新采集/物理/human仍未验。

正式反馈短文本根因UNKNOWN：独立feedback-boundary-review实际AST封装/relay表达式/Omni flush/Core handle/send与真实emotionregex '<(.*?)>'均完整保持22chars/hash，未复刻49异步时序；单delta数量不能证明provider原文短。Main下一补既有WIRE_TRACE受控len/hash边界（reply/实际relay/write/providerreceive/callback/Corepublish/Native），不记正文、不新routing，先offline再考虑唯一必要线上。默认AUTO_GRADE仍OFF，其他A–F和本人集中验收继续；账本不重置。


阶段37发布核对：12精确allowlist已push源码/证据commit 62dfc8a025e92030be4498172a20ddaf65bec1ca；remote codex/daily-learning-companion同SHA，publisher clean，remote master仍f1e8f3f5605659f0526e43bc3b85c60ae46c85fb，Root index空。当前SourceGate全指纹/隔离helper导入再次PASS，无host/设备启动。原contract SHA不变，账本785/74/0。本阶段是progress，Goal active，A–F余项及49 PARTIAL保留。
38定向接续：现有scripts/neko_spoken_turn_patch.py已管理_wire_trace.py的spoken诊断（初始化由launcher调用），可优先复用RealtimeWireTrace，避免另增runtime helper/记忆系统；record_recv的first-delta节流前应记录每个真实delta的无正文长度/hash及实际response/物理generation，不能只记录首delta；Core entry/queue/WS以及实际relay payload应分开hash，按真实边界接入且诊断失败不影响路由。当前尚未修改该实现、manifest或host源码，不凭设计冒已交付；先最小离线/独立review再必要线上，不盲重复49。
