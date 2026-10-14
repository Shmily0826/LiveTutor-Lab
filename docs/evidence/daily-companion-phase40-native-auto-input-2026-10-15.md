# 阶段40：原生自动响应与输入归属（草稿隔离，未部署）

完整契约仍为 [contract](../daily-companion-contract-2026-10-14.md)，A–F 未缩减；Goal active。阶段39的真实场50保持 PARTIAL，原件与 sidecar 不改。本轮没有新在线场、模型请求、设备初始化或声音；房间/物理/虚拟麦克风、capture、loopback 均未使用，系统音量未改。

## 本轮实现及边界

在既有 arbiter 单队列/ticket/owner 内新增显式 automatic_audio 模式，仅许可已知 lanlan_app_gemini route 的非空 audio.append 及正整数原 input_sequence。第一 write 前安装 owner，完整批次写完才 ticket.sent；既有 seen-ID/server-ID/quarantine/单 lane/cancel 保护保留。不伪造 conversation.item、server VAD、ASR ID、provider ACK，不额外发送 response.create，不重放 PCM。

transport 只从该实际响应 owner 读取原 input_sequence，不再在迟到 content 到达时把新输入序号复制给旧响应。该路径的输入 boundary 仅由完整本地写入后的 ticket.done 成功且原 epoch/ws/generation/Core authority/input sequence 仍当前的 waiter 退役；UI 的 host-turn guard 未移动。失败、缺 status、id-less、仅 terminal 或错 response ID 不算成功；本地 fail-open 仍产生超时失败，不能冒 provider 完成。普通路径与默认 OFF 开关未改。

范围明确为首个有实际 ID-bearing content 的自动响应；同 PCM 的第二 ASR/响应不能无证据继承该 ticket，也不能清除后继输入。因此本轮不是自然停顿分轮、追问教学语义或完整场50的已通过证明。

## 当前离线证据

`python -X utf8 -B scripts/test_neko_native_audio_dispatch.py`：40 tests PASS（13.365s），20 新归属/拒绝/取消测试加20现有 phrase 回归；使用临时 canonical 重放后的实际 arbiter 和 transport 方法、真实 Core/client queue-socket fixture。合成 provider 事件和内存固定 PCM 不是真实模型/设备证据。

覆盖完整写后真实 terminal、write await 内早 content/terminal、分块早 terminal 拒绝、真实第二 socket write 失败、permission/frontend/socket 替换、新正 PCM/原 onset marker、host-turn UI 保护、未知二次响应、seen/server/id-less/functioncall ID 拒绝、失败/statusless terminal、strict profile、实际 arbiter fail-open 超时，以及 busy text owner 前排队的 phrase 取消不影响无关 owner。原 burst 测试在第二批前补真实 fixture content/done，避免用手动输入标记冒充响应队列完成。

两份实际宿主文件各自复制到临时目录后 canonical/AST/state/二次幂等通过。未部署时 SourceGate 如期拒绝 changed phrase helper fingerprint；不能在此状态启动宿主。独立审查已终结：40 tests PASS（13.246s），但额外 actual 工具返回路径确认 P2 互等，不能部署；详 [实现审查](daily-companion-native-auto-implementation-review-2026-10-15.md)。

## 草稿指纹与部署前基线

| 文件 | SHA256 |
|---|---|
| scripts/neko_native_audio_dispatch_patch.py | c2aaef9d9abde2f7b7620566b08ccb0bc914d62d99a16788919cfb293bf96dd2 |
| scripts/neko_native_grade_patch.py | ab70802f345f1635e6de3827d021cd70eb925d06ba018f9bb082a165b715577d |
| scripts/neko_phrase_input_transport.py | d247be713381aae91a71608441f9a06d3be0b5ccb868a8b667c9d70f44ce548b |
| scripts/test_neko_native_audio_dispatch.py | 0b3726aebd504b38d4a7ec68271c5a1c912e6520af093f0fe02b1d52216898b0 |
| scripts/test_neko_phrase_input_transport.py | 0be8d99fd113e01b059212247725381ac5a80da710d118fb0154c8ce1243b64a |

两 host 当前 arbiter SHA f041135b335a22655bffe14a0856d11f105aa50b56355a0921ec853e7be9aaff；transport 78df4190470f8d6ec43ae94c2995fa1eef9b3e30a59b3673418b32c6ddacdd65；deployed producer 58bfe9f9513d45b6cb92a4adcedb4d81014e5a85c02870a3f712ac5407f5d07b。临时 patched arbiter 5cc8a257b0e5823daa574577e0d4f0da39a521abea299ba96a4d661a06f72a07；transport 31529359a50debe915c272d29f551ebb7395fef145bf07eef865a4a16acb7408。部署只在独立审查后按原 SHA 验证、独占备份和 exact replacement；未知差异停止，不覆盖。

## 额度、进程与接续

本轮实核原账本 bargein-autocheck-20261012：DeepSeek810/2000、app76/null、tech0/0，未改账本。上一场 launcher44128/Native33564 已不存在；本轮仅已终结的本地 Python unittest，无 live host/online scene。

下一步：工具 continuation 设计缺口留明确恢复条件，先推进 A 图片小字编码入口；不新开线上场。其他 A–F、自然停顿、多响应和集中真人验收继续保留。

## 独立发现与安全隔离终态

真实 `_send_tool_results_openai_realtime` 在 native 自动 owner 等 started 时将 function_call_output 排入同一 lane；LANLAN functioncall ID 不可充当 audio ID，而草稿拒绝 terminal-only，结果 native 等工具产生的内容、工具又等 native 放行。40个正向/负向测试未覆盖这条实际教学路径；不能拿它们掩盖 P2 或宽放 ID。

Main 未部署任何宿主文件/manifest。已把本轮 producer 原 bytes 独占存 `scripts/drafts/neko_phrase_input_transport_phase40.py`（d247…548b），grade 接线原 bytes 存 `benchmarks/raw/evidence/neko_native_grade_patch_phase40.py（只作本地备份，不发布）`（ab708…577d）；然后仅恢复本轮自有接线/producer到已核已发布 exact SHA：producer58bf…07b、gradead82…7be。新 patch module 保留但不接生产。SourceGate 再次实际 PASS，未绕过指纹检查。

测试改为在临时 canonical 上组合隔离 patch，并显式加载 draft producer；隔离适配后同40例 PASS（12.937s）。另补 known-blocker 测试，通过是确认工具仍被阻断，绝非修复通过；与 busy 取消例定向2 PASS（.732s）。独立报告冻结原5 SHA，本段记录隔离后路径和测试变化，不回写审查当时对象。

恢复条件：先设计真实工具 task owner→原 sealed slot 的 conn/scope/Core authority 资格及同 lane continuation join，覆盖 actual study_quiz形态、并行/迟到/新PCM/新连接/取消；不能以同connection或当前seq代替父输入证据，不能让functioncall ID冒认audio ID。未解不在线，局部问题不结束Goal。
