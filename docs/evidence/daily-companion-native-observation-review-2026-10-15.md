# 阶段37 Native累计观测与late cancel独立审查

2026-10-15。只读本阶段 `neko_native_telemetry.py`、`neko_daily_voice_probe.py`、`neko_native_grade_acceptance.py` 及对应tests。仅新增本报告，无实现/共享记录/raw/部署/账本修改，未启动服务、API、模型、浏览器、Native或声音/捕获设备。定向测试仅用其假协议、Node VM及自身临时SQLite fixture，未读写用户或实际任务学习数据库。

## 发现：P2，observer末段异常可被吞掉（待Main修复）

`observe_native`中 `native_history.capture(await observer.snapshot())` 失败会结束observer task，但未设置failed/ended，也未记录report.failure。主循环仅在等待响应的while（约549–551行）检查task.result；正常break后另有3秒sleep、截图和preferences/status/material等await，期间observer仍在运行。若此时发生ring gap、计数不符、身份重载或容量上限错误，后面只检查failed事件，finally又用 `gather(..., return_exceptions=True)`吞掉该task错误。

可复现后果：报告仍保留上一份valid/sequence_complete的native_final，observation_end_wall却继续向后；末段gap之后的PCM/text可能缺证，而report.failure仍None。正常已结束轮的grade检查可能继续通过。此为观测链P2，并非产品音频owner漏洞，不应通过放宽原guard修。

独立只读离线重放actual `observe_native` AST及actual NativeTraceHistory：假observer第一次返回sequence400完整窗口，下一次返回sequence1000仅最后500条；在模拟末段grace等待后收取task异常。实际输出：

```text
actual_observer_task_error RuntimeError Native observer ring lost events between polls
failed_flag False
retained_sequence 400
report_failure None
```

该重放未执行完整probe/应用，不联网。最小修法：observer异常同步记录diagnostic并设置failed/ended后重抛；冻结turn与最终收尾再核task健康/必要最后一次capture，正常主动取消单独处理，不能只在响应while内检查。补“最后3秒grace/最后收尾await发生gap”actual AST异步负例。已即时报告Main；本段保留初始发现，后续复审另追加，不改历史。

## 累计History本身的审查

- JS observer_sequence为本renderer本次INSTALL的单调事件序号，使用自有eventSequence生成，不能当ASR utterance ID或server authority。每条事件含sequence；device playback投影新增remainingSeconds/updatedAt，未修改播放器。
- NativeTraceHistory默认上限12000；安装时间改变、sequence类型/回退/越界、batch>500、序号不连续、重叠旧event被修改、首次已淘汰前缀、两次poll间gap都抛错。先验证候选added/all_events及累计binaryFrames/binaryBytes与全部audio_frame精确一致，最后才写self.installed_at/events，避免半提交。
- 成功结果复制event字典，调用者修改返回的标量event不会改内部已留存的event。历史前缀一直保留，source旧token PCM不被重新当fresh；单纯ring换窗口不重置binary计数。
- installedAt绑定是本地observer安装身份，不是OS进程ownership或provider generation。输入计数沿原snapshot保留，本次一致性验证针对全部binary接收帧/bytes；不宣称每一input计数亦被独立回推验证。
- probe initial、等待session_started、持续observe均使用同一NativeTraceHistory实例；每轮统计用累计帧数差，而非每轮清计数。History失败不应被改成清空重建继续。

## Late cancel例外范围

`_native_terminal`保留原final source_ended路径；新增只在final reason=speech_cancel时查完整累计事件：sequence_complete literalTrue、first1/last/eventSequence/len相等、逐条序号1..N、累计binary计数与全部帧一致；要求同新token真实device source_ended、activeFalse、有限数值remainingSeconds=0及updatedAt有效，且在本轮最后PCM之后、最终cancel之前。还要求最后PCM与receipt间实际audio_done或system turn end；receipt后不得再有PCM/audio_chunk、非空模型文本或active播放事件。

该路径证明已观察到正常结束后才出现空队列cancel，**不将cancel本身当正常结束**；它不取消旧token、重放声音、修改owner或改变评分内容。legacy未带collection仅能沿原final source_ended路径，不能借新例外通过。返回仍是candidate、physical_output无loopback未知、human PENDING。

done身份的支持范围：当前事件字段/逻辑允许窗口内audio_done或system turn end；普通system消息未必带可用token，不能将这项文字写成已核provider ACK或完整speech owner证明。其他qid/attempt/正式entry/旧输出退休/新token帧与schedule判据仍继承。

## 独立定向离线执行

采用已有Source venv的 `python.exe -X utf8 -B`：

| suite | 独立结果 |
|---|---|
| test_neko_native_telemetry.py | 18 PASS，2.910s |
| test_neko_native_grade_acceptance.py | 27 PASS，0.704s |
| test_neko_native_grade_probe_plan.py | 9 PASS，0.261s |

包括actual INSTALL/SNAPSHOT在Node VM滚动400+350事件保持完整750、gap/reload/旧event篡改/计数漂移/overflow/首次丢前缀拒绝；latecancel缺collection、计数/序号不一致、缺0/布尔0、foreign token、缺done/过早receipt、active/后续PCM/text拒绝。18/27/9通过不覆盖上面P2末段task错误传播。

## 初审指纹

| 文件 | SHA256 |
|---|---|
| neko_native_telemetry.py | `3d87fe07ee45b3ccebb8ca4f63e4b4a9b148e9a17664afba10535f25603e598f` |
| neko_daily_voice_probe.py | `b167d9cbfdd1a28f085b4d4b8eeb6818346dfc7b35defb6130e29e2cf0d8d3a5` |
| neko_native_grade_acceptance.py | `f6b921e4bc855602c286daaca6caf3fbdcab90f16832dc4b95c2966aaf33f079` |
| test_neko_native_telemetry.py | `645cef6693aba5258c0e118ac1bddccad458510b0d38c2581a2ef03e06720075` |
| test_neko_native_grade_acceptance.py | `6ed8614320f7bc3c0f8553a5797be4a504d6ccf9d18e9972814260f09d9114dc` |

当前结论：History/latecancel核心新增逻辑未发现其他具体阻断；probe末段异常传播P2待修后复核。原49 raw与PARTIAL不改，短答案根因另报告仍UNKNOWN，量具修复不追认49整体PASS。

## P2精确复核关闭（追加）

Main随后最小修复已只读核对：

- actual nested `observe_native` 捕获Exception，先同步记录native_observation_error并设置failed/ended，再raise；普通CancelledError不被该Exception分支误标为观测失败。
- `checked_native_snapshot` 在snapshot await前后均检查observer task；失败task重抛原异常、意外取消或无异常早停都拒绝。中间fresh capture仍用同一History，gap/counter失败不重置或提交半份结果。
- 每轮3秒grace后先checked fresh capture再形成reply/turn snapshot；最后截图与preferences/status/material await后再次checked fresh capture，因此原报告描述的两个漏检窗口均关闭。
- 最后健康检查到主动task.cancel之间无新await；主动cancel/gather后置None，再发送end_session，区分正常结束时停止observer与提前丢失观测。外层finally的幂等cleanup继续保留。

独立运行更新后的 `test_neko_native_grade_probe_plan.py`：**13 PASS，0.570s**，新增四项使用actual nested observer/checked AST：400→1000真实History gap在trailing grace同步failed/ended并拒freeze；observer仍pending而最后fresh本身有gap拒绝；snapshot await期间observer失败在后置check传播；正常主动取消不误记failure，但取消task若用于新freeze仍拒绝。没有宿主、网络、音频或实际学习库动作。

此前独立18 telemetry/27 acceptance的四文件指纹未变，未重复无关基线；Main另报告18/27/13均通过。**该P2按SOURCE/OFFLINE关闭，本窄范围无新增具体P1/P2。** 不外推真实持续观测已经执行，更不修改49原raw/PARTIAL或短反馈根因UNKNOWN。

最终冻结指纹：probe `2f38d62d9fc548789ae2e8e95b2ebbf6f8b5f0a6244d272126f298352c7c0290`；probe-plan test `59b542c71e3bb4e09baa504df33e1545255246c117f7b2888eee2a86e398242f`。其余四文件沿上表未变。本报告冻结，仅追加此关闭记录。
