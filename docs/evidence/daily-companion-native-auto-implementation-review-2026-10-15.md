# 阶段40自动音频草稿独立实现审查

2026-10-15。只读指定patcher/upgrader、phrase producer、actual arbiter/transport与精确工具返回callee；仅新增本报告。未修改实现/共享记录/manifest/raw/DB/账本，未部署、启动host/网络/模型/音频或捕获设备。离线执行实际模块/QueueSocket fixture；不冒模型或设备通过。

## 结论：P2工具续接阻断，当前草稿不宜部署

已冻结版本 **40项定向离线独立PASS**，但该组未覆盖“Native先调用Study工具，再返回function_call_output”的真实交互。增加独立只读actual `_tools` 路径重放，确认新的native自动owner与工具结果队列互相等待。已立即通知Main暂停部署。

不能把这项修成允许function-call response ID冒认audio/text ID、接受terminal-only为成功，或无证据清掉native owner。现草稿宜隔离保存，恢复精确已发布接线/producer后转可自主工作；若继续修，须明确工具continuation归属而非宽放guard。

## P2精确因果与离线复现

1. phrase完整audio.append写入后，actual arbiter `_current/_response_owner`是automatic_audio/native_phrase，等待ID-bearing content来确认started。
2. LANLAN_APP capability明确function_call_ids_match_terminal=False；actual notify_response_content拒绝function_call_arguments.done用作response start。实际图出题/解释通常先出现该事件。
3. 草稿在notify_response_terminal前新增严格guard：automatic_audio owner还无response_id或终态ID不匹配即返回False。因此工具请求轮的有IDcompleted终态亦不能释放尚未started的native owner；此拒绝本身是为避免伪造对应，不能盲删。
4. actual `_tools._send_tool_results_openai_realtime`（约1274–1343）把真实function_call_output交既有arbiter.enqueue(source='tool_result', priority5)，然后await ticket.sent。但arbiter当前正在native_phrase `_process`内等待started/done，工具结果只能排队，provider也收不到它以生成后续可识别audio/text。最终由started timeout或外部失败收尾，而不是正常教学续接。

本次内存fixture采用当前test的actual模块/QueueSocket/Core配置，phrase→finish_writer后，调用actual notify_response_content给function call形态，再通过QueueSocket接收有IDparent terminal；最后实际执行：

```python
client._send_tool_results_openai_realtime([
    ToolResult(call_id='actual-call', name='study_quiz',
               output={'question': 'fixture-only'})
])
```

100ms后实际观测（无API/插件模型）：

```text
functioncall_content_rejected=True
native_started=False
native_done=False
owner_source=native_phrase
tool_results_done=False
queue_depth=1
wire_types=['input_audio_buffer.append']
```

使用actual工具返回方法，不是假设它会enqueue。工具结果与原ticket均未成功，等待是有界的，但正常Study教学被阻断；fixture只验证这个阻断，不执行真实study_quiz生成。重放后取消本地工具task并按fixture清理，未回写任何原材料/成绩。

## 其余实现的已核边界

- 新automatic_audio参数默认False，仅source native_phrase、LANLAN_APP、合法正int inputseq、纯非空audio.append列表，禁止ack_expected/pre_commit/response_event；未知profile和bool/0序号拒绝。
- 复用原item-driven安装owner的第一write之前时点，避免同步早content无owner；新模式不发response.create、不伪造conversation item，也不将item_acknowledged=True。
- native_input_sequence_for只对相同实际response ID、current非interrupted automatic owner、started成功返回固定原seq；transport新lifecycle不把later currentseq套给旧response。原普通路径保留。
- phrase sender在每次await前后按原snapshot/epoch/ws与inputseq核验，只记成功写出的样本；整批written==output才安装waiting/watcher。partial多块early terminal失败、不重放；单块send内真实content/terminal可在完整write确认后由watcher结束。
- native input边界由ticket.done成功后、原snapshot/epoch/seq仍当前的watcher触发；失败/statusless/idless/terminal-only/wrongID/local fail-open不当成功。UI hooks仍由原host-turn guard保护，没有迁移旧guard。
- 新正PCM退休旧waiting并cancel旧response_waiter，driver.retire也取消writer/watchdog/waiter；cancel_ticket针对原ticket，busy其它text owner不被错cancel。默认phrase OFF、handoff/replay整段bypass和原native receipts有离线回归。

以上对“无工具、首个实际audio/text response”的边界是正面证据，但不能覆盖P2工具续接。busy队列/取消测试通过也不代表工具结果可以反向依赖正在占lane的native请求。

## 独立测试与调查史

按授权命令使用已有Source venv：

```powershell
.\benchmarks\raw\neko-product-host\.venv\Scripts\python.exe -X utf8 -B scripts/test_neko_native_audio_dispatch.py
```

最终冻结bytes独立 **40 PASS，13.246s**（20新AutomaticAudio＋20 ExistingPhraseRegression）。包含成功/同步早响应、多块early partial、newPCM/originalseq、failed/statusless/terminal-only/idless、partial socket/permission/physical/frontend替换、default OFF/bypass、host-turn UI guard、第二unknown response不关新输入、profile/identity拒绝、local fail-open、busy unrelated owner取消保护。

审查中途Main尚在增补用例，曾看到fail-open fixture与assertLogs fixture问题；Main修正callback/计时和日志屏蔽后，相关2项独立通过，最终全40通过。未把中间fixture错误算成冻结产品失败，也不由最终40PASS掩盖额外实际工具路径P2。

test初始化在自身临时目录对actual arbiter/transport做canonical replay、AST/state/二次幂等；actual host源码未写入。外部DSP/配置/socket/provider seams仍有替身，不是模型/设备验收。

## 最小可行修复边界（后续设计，尚未实现）

若保留automatic native owner，需要一个显式的**同owner工具continuation join**：真实工具task owner必须与原sealed输入/Core authority、物理conn、scope以及仍当前的native slot匹配，才可在该slot内交付其function_call_output；随后仍等后续真正audio/text ID来开始/终结native response。不能把它作为另一个会等待当前slot完成的普通独立enqueue，也不能让无关联UI/SDK/其它工具插队。

当前actual `_tools` 返回接口没有该可信parent-slot参数；function-call ID又不能当终态ID关联。仅有相同connection或“发生在5秒内”不够，不能用当前seq补认父输入。因此这不是安全的一行terminal特判。需先做真实工具task→slot资格捕获/逐await验证和取消边界的最小设计/fixture，再决定是否实现；证据不足时隔离当前草稿是合适的阶段收尾，不停止整个A–F Goal。

必要新增场景至少包含：真实study_quiz形态call→parent terminal→actual工具返回→后续audio/text；并行工具/foreign scope、工具返回时新PCM、失败/迟到工具、old/newconn、无工具普通答案。多ASR/多response仍按已声明首response范围，不能新建宽松的“近期输入”归属。

## 冻结实现指纹（审查时，SHA256）

| 文件 | SHA256 |
|---|---|
| scripts/neko_native_audio_dispatch_patch.py | `c2aaef9d9abde2f7b7620566b08ccb0bc914d62d99a16788919cfb293bf96dd2` |
| scripts/neko_native_grade_patch.py | `ab70802f345f1635e6de3827d021cd70eb925d06ba018f9bb082a165b715577d` |
| scripts/neko_phrase_input_transport.py | `d247be713381aae91a71608441f9a06d3be0b5ccb868a8b667c9d70f44ce548b` |
| scripts/test_neko_native_audio_dispatch.py | `0b3726aebd504b38d4a7ec68271c5a1c912e6520af093f0fe02b1d52216898b0` |
| scripts/test_neko_phrase_input_transport.py | `0be8d99fd113e01b059212247725381ac5a80da710d118fb0154c8ce1243b64a` |

本报告冻结。P2未关闭，不批准这份实现进入在线；宿主/manifest仍由Main按准确旧SHA处理。50原PARTIAL及所有层次边界不变。
