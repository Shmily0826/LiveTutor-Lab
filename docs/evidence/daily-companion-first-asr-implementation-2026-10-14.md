# 首条语音工具早于 ASR：限定修复与证据

完整任务见 `docs/daily-companion-contract-2026-10-14.md`；现有 Goal active。原 voice16 首题保存但没有朗读的失败保留，不能因数据库有题称学习者已听到。

## 实际触发与修复

voice16 固定输入结束后2.117秒到达 quiz 调用，225ms后首条 ASR 退休旧scope。旧两秒等待没有覆盖该调用；工具已经执行，随后按正确的owner保护被取消。时间证据见 `daily-companion-voice16-epoch-review-2026-10-14.md`。

仅对免费 lanlan.app、无 server VAD、当前连接没有收到过 ASR、已观察到尚未识别语音的 Study 调用，在最后语音后的0–8秒暂缓执行。必须有连接建立时的foreign-scope基线，当前值相同；call后观察到新的语音序号或last-loud变化即拒绝。0.4秒内收到ASR、回调就绪、恰好一次预期scope推进，才捕获该新scope的owner执行。原已执行任务仍正常退休，不复活；连接、provider、socket、foreign输入、第二ASR、fatal、barge handoff继续拒绝。缺ASR或队列满，不进入付费工作。

这是首条输入的有界时序兼容。观察序号不是utterance ID；不保证所有opaque provider调用与ASR的身份配对。后续prefix、长句自然停顿、超过8秒的输入仍待处理。opt-in speech gate仍默认OFF，原onset、PCM和普通打断不修改。

## 审查及实际离线结果

Main运行 first-ASR8项、ordering7项、opt-in gate14项，均PASS。覆盖225ms原时序、1.999/2.000/2.001秒边界新语音负保护、call前foreign输入、缺ASR/满队列、连接替换/第二ASR/fatal/handoff。ordering测试通过真实`state/apply_to`验证canonical重复调用幂等、重复helper/未知edited helper拒绝且原bytes保持。

原审查两P2已收口：首输入负保护覆盖两秒两侧；helper normalizer在already-patched早退前校验。既有只读Agent复审无该限定增量的新阻断问题；它未自行运行测试。完整审查见 `daily-companion-first-asr-ordering-review-2026-10-14.md`。

从N.E.K.O原revision `1d814cf32fba8c02b5727d2890710e4e7b8ece24`的Git LF源码真实重放两个changed targets，AST/二次幂等/与candidate和runtime逐bytes匹配，启动source audio gate PASS。仅改两个目标及manifest对应sha，无关TTS修改保留。

| 目标 | 部署 SHA256 |
| --- | --- |
| `_tools.py` | `41c50034fbba268f58214df34e5f167fb2f45b906d8d8bd4d854ec4922cc05cc` |
| `_transport.py` | `9ce6a44928b967b1260aff49c0be217b6727bb47c357c70228222111bbccb28c` |

## 设备验证进行中

voice17 exec82095，复用既有隔离store/反向图/三个fixed WAV，单场回环上界311秒，host更长有界。主Agent独占在线/账本。启动前552/55/0，启动后app56，room mic=false、volume_changed=false；不能在终态/语义/完整回环检查前声称通过。原始JSON/WAV只本地，不发布。

Phase7源码尚未发布，现有远端feature仍537e573。最终结论以终态报告和status最新追加为准；人体验仍待明确“准备好了”。

## voice17终态补证

exec82095终态，首参数迟固定语音结束2.182s、ASR又迟130ms，首题9PCM/18设备响声bins；三工具均实际调用，311秒完整回环覆盖末轮，577/56/0/no online。限定设备链通过，措辞/summary错误与人体验仍未过，详见phase7-teaching-device报告。
