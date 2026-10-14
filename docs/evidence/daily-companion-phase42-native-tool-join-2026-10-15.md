# 阶段42：隔离 Native 工具同轮续接

日期：2026-10-15。当前为 SOURCE / OFFLINE；独立最终26项通过，尚未生产接线、部署或在线验收。完整需求与权限仍以 [contract](../daily-companion-contract-2026-10-14.md) 为准，Goal 保持 active。阶段40/原49/50的运行时 PARTIAL 不由本报告改成通过。

## 问题与实现

阶段40原 Native audio ticket 占用单 lane，实际工具结果又 enqueue 第二个 ticket，双方等待。新隔离 `scripts/neko_native_tool_join_patch.py` 组合阶段40草稿，在实际 provider 工具入口捕获原 slot 的唯一对象，经现有工具 owner、唯一允许的 ASR scope +1、unannounced owner 重建及 collector 传递。结果在原 lane 串行写回，不另 enqueue、不额外 response.create、不重放 PCM。必须先等待原输入完整 actual write；本地 sent 不冒充 provider ACK。

每次实际写前后核原 slot/current/driver epoch/Core authority/原 sequence/ws/generation 与原工具 owner。并行 batch 必须同 origin、所有 entry current、call ID 集合完整；未知、重复、超过32或缺成员均不能当完整成功。实际 send_event 必须 literal True；部分失败不回退重发。待工具与待内容开始分开，保留绝对30秒上限和8秒写预算，普通无工具5秒等待不变。后续真实 ID-bearing audio/text 与匹配成功 terminal 才能结束原 ticket，function-call response ID 不冒充 audio terminal ID。

初审独立发现 P2：原 handler 对所有 raw APIs 的缺失 call_id 合成 glm_*，新 capture 曾误当 wire ID。已在隔离 actual `_transport.handle_messages` 保留 event 原始 call_id 到 ToolCall.provider_meta，Native capture 只接受真实非空有界字符串且与实际调用 ID 等值。缺 wire ID 在执行工具前失败并关失败连接；真实 `glm_` 前缀 ID 可正常使用，不按前缀猜。普通非 Native 路径原合成 ID 兼容保留。

原 Native slot 已开始内容或已完成后，迟到 raw 工具不能借普通 tool_result lane 重新执行；当前明确 fail closed。此限制是单 outstanding 输入的受控原型，不是完整多轮工具协议支持。

## 本地验证

实际源先复制到 TemporaryDirectory，canonical patch / AST / patched state / 二次幂等核验后编译 arbiter、tools、transport；QueueSocket fixture 运行 actual Core/client/handle_messages/raw task/collector/sender。工具 callback 为本地 fixture，无模型、网络、音频设备。

| 集合 | 结果 | 范围 |
|---|---|---|
| 新工具续接24项 | PASS，21.127s | 实际handler工具/并行/ASR +1、>5秒、完整输入前不执行、部分PCM、write False、早terminal、newPCM/锁等待/ws替换、普通lane与SDK不越权、绝对期限、normalizer未知编辑、wire ID缺失/合法glm_、32/33、取消兄弟、混origin、真实8秒write timeout、内容开始/完成后迟tool拒绝 |
| 阶段40原20项 | PASS，6.882s | 在新compiled arbiter/tools/transport下运行，原 known-blocker断言由新正向实际链路取代；不重复声称已修多ASR |
| 原phrase20项 | PASS，6.606s | 使用新 NativeToolJoin fixture承载原 PhraseTransport cases |
| 普通 NativeHandoff12项 | PASS，4.905s | 替换新 arbiter/tools/handle_messages，原普通打断、旧连接、回放、onset保护 |

合计76项 Main SOURCE/OFFLINE，通过不等于物理可听或真人体验。最初4项与后续16项通过只作开发历史，不叠加成不同最终cases。中间22项运行有1个测试断言 ERROR：缺wire ID正确fail-close后 `_current` 已清，旧断言读取None；已改为保存原owner并等待fatal，最终24项通过。没有把这个错误删去或说成运行时已通过。

新24命令：`benchmarks/raw/neko-product-host/.venv/Scripts/python.exe -X utf8 -B scripts/test_neko_native_tool_join.py`。该main只选本类新cases，避免继承旧 known-blocker。回归通过 unittest 枚举 `audio.AutomaticAudio.__dict__` 的20个非known-blocker，在 NativeToolJoin 上运行；phrase20把原 PhraseTransport 的test methods映射到同fixture；普通12在 contextlib.ExitStack 下替换 `_client/_responses.RealtimeResponseArbiter`、OmniRealtimeClient的实际tools methods与handle_messages再运行 NativeHandoffTest。不是在未加载新原型的旧模块上重复跑旧测试。

## 指纹与安全范围

以下为24项中间冻结版；最终26项指纹与审查结论见文末，保留中间缺陷与修复历史。

| 文件 | SHA256 |
|---|---|
| scripts/neko_native_tool_join_patch.py | ce2186431e71284bd99dbbcb9bc79035dc20e550da35c5683aca2132b3f4e122 |
| scripts/test_neko_native_tool_join.py | ee4489aeaa551b3f8a32b0a6c2d768147569a5c6ade2d2fd0a46f3a7c35c443e |

生产 patch chain、producer、两宿主目标、manifest、默认实验开关均未动。现运行版本仍39/41；本轮 source gate 实际 PASS。原账本 bargein-autocheck-20261012 实核 DeepSeek810/2000、app76/null、tech0/0，未重置或新增外部调用。未初始化麦克风、capture、loopback，未用扬声器或改变音量。Root原脏树、空index、用户学习库/历史、只读Sky Scout保留。

## 待复审与下一步

[设计](daily-companion-native-tool-join-design-2026-10-15.md) 与 [独立实现审查](daily-companion-native-tool-join-implementation-review-2026-10-15.md) 分开。实现审查在冻结上述bytes后进行，当前不能据Main76项直接批准部署。

待明确：pending工具期间取消的完整恢复/失败时限、producer与arbiter各30秒计时起点、写中退休/工具取消清理。短窗newPCM不写旧结果，只证明隔离，不证明新轮完整恢复。LANLAN仍缺严格 input-to-tool因果标识，第二ASR/第二response/第二工具round、延迟旧事件不在已通过范围。若这些阻止安全上线，保留隔离草稿、记录恢复条件并转A/C/D/E其余工作；不因此结束整个Goal。任何后续真实模型、Native播放、实际设备或真人结论需独立证据。

## 最终26项冻结与取消P2关闭边界

独立复审在24项后实际发现另一P2：held工具→新PCM令producer调用 cancel_ticket(wait=False)，旧start等待未观察interrupt_event仍按30秒占lane，完整下一phrase等8秒后失败。已新增interrupt_event waiter，经原 `_cancel_after_timeout` 的cancel grace/escalation处理；auto+interrupted不能采用adoptable response，绝不直接放lane/假terminal。

初修一度使等待结果写回时替换ws的原负例 FAIL：旧cancel升级关闭新socket。该失败没有删测试绕过；现由工具入口向原slot保存connection-only资格，取消入口及cancel-grace升级前重核原ws/generation，不能对替换socket升级。原工具scope、新PCM等执行归属仍独立核，不靠connection-only授权结果。

Main三项定向取消/替换测试 PASS7.069s；此前定向初测另一次socket.closed断言发生在fatal已置位但异步physical close未完成时，断言改为实际等closed且finish_writer。新完整phrase在无合法provider terminal时按原3秒grace安全失败关闭、断言<4秒，旧PCM不重放、新PCM不发、输入不假标成功。取消grace内换socket则旧ticket失败、新socket无write/不关闭。此为SOURCE/OFFLINE安全失败，不是不断连恢复通过。

最终冻结：

| 文件 | SHA256 |
|---|---|
| scripts/neko_native_tool_join_patch.py | ceb906653b2fdcd143c3467915d4cd98536512876f163272eab662460167474a |
| scripts/test_neko_native_tool_join.py | 23070f99c386e6f23bd34891f6dedaaaa7fda59f8cf2f9fdb88b464e6fbc32c4 |

该bytes独立完整26项 PASS28.074s（Main此前24项/定向3项不叠加）；Main在最终bytes组合运行原自动20+phrase20 PASS13.520s、普通handoff12 PASS4.816s，最终78个不同cases。审查未见本次增量剩余具体P1/P2，结论限隔离原型SOURCE/OFFLINE，无上线/模型/物理/真人新证据。

两个30秒仍是各自起点，producer watchdog可能先于arbiter cancel grace安全失败，未宣称共享截止或超慢工具体验完善。多ASR/第二round、本地资格非provider严格因果、已开始内容/完成后迟工具明确拒绝均保留。运行版本未接新原型，production producer58bf…5d07b、gradepatch ad82…3f3b7be、host manifest40c8…3da71原SHA实核；SourceGate PASS，无live host/场/自有48911/48916/9234 listener，账本810/76/0。

下一阶段先准备可回退的隔离实验接线及精确部署方案，default phrase/AUTO仍OFF；只有current bytes、canonical/normalizer、manifest、SourceGate及相关回归一致才允许受控单场，不能把本阶段78项当原50真实失败已修。若实际协议资格不满足，停止该线路无效重试并推进其余A–F；最终human仍等核心成熟。


阶段42发布核验：8精确allowlist已commit/push 0ec30ad7aea5ce939079a252f0e51785fabd5ab0 到codex/daily-learning-companion，remote同SHA、publisher clean、Root index空；master仍f1e8f3f5605659f0526e43bc3b85c60ae46c85fb。无raw/DB/WAV/密钥/备份发布；contract原SHA与SourceGate再次核验通过，原ledger810/76/0。无live host/场、音频设备与系统音量未操作。下一43从冻结patch ceb906…67474a/test23070f…bc32c4与phase42报告接续，先准备隔离实验接线/回退、canonical/normalizer/manifest/Gate一致性和必要回归，default phrase/AUTO OFF；有界安全failclose不冒连续恢复，未真实模型/声音/human验收。全部A–F与局部阻塞转线、原账本不重置、禁mic/capture/loopback、实际证据完成条件保留，Goal active。
