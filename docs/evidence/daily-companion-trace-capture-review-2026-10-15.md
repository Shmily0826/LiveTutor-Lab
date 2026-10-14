# study-text未来报告自动保存独立窄审

2026-10-15。只读 `scripts/neko_spoken_turn_analysis.py` 的parse_study_text_records、新probe fresh_log接入和 `test_neko_spoken_turn_analysis.py` 定向增量。只新增本报告；另按授权在原50review末追加no-owner候选机制更正。未改实现、共享记录、raw、DB、账本或实际runtime；未启动服务、网络、模型、Native或设备。

## 初审发现与修复状态

**P2：坏诊断行可能中断probe最终报告。** parser最初只捕JSON ValueError，时间验证调用既有_timestamp。独立纯函数反例：合法JSON的t或mono=`10**400`使math.isfinite抛OverflowError；递归1100层的JSON数组使json.loads抛RecursionError。future probe在finally直接提取，若坏行触发异常，就不能按原意拒绝坏行并继续保留有效记录。

Main已对_timestamp仅加OverflowError→None，保留原数字类型/finite判据，修复超大t/mono；未将异常值改成0或猜测时间。递归JSON隔离已精确报告Main，待最后修复复核。原始初审两类反例和关闭过程在本报告保留，不冒全套测试已覆盖最初缺口。

## 源码范围核查

- parser仅选择固定tag JSON；root必须dict且全部字段属于明确白名单，stage先核str再查允许集合，stage=[]不会触发unhashable错误。reply/text/payload/private字段直接拒绝整行，不是复制后隐藏。
- t/mono必须真实有限数字且排除bool；chars/utf8_bytes/stream计数/bytes为非负int且排除bool，gen/scope允许None或非负int；cid限8位小写hex；sha/stream_sha限64位小写hex；response_id/token仅None或≤160字符串；delivery仅local_socket_write_only；cumulative_available若存在必须bool。
- parser不会根据同时间戳/同hash去重，逐行append保持真实delta顺序；末块sha256与stream_sha256都保留，不冒称末块是完整流。
- 字段合法不等于累计完整：此parser只保存诊断，不推断同provider utterance、完整prefix或ACK；缺cumulative字段、cumulative_available=False不得填补。允许的response_id/token是记录器身份字段，不应在后续报告当教学正文展示。
- probe只从本场log_start byte offset后的fresh_log提取，写report.study_text_trace，未再开外部调用或重读成绩/造题；没有修改grade_acceptance或音频owner。byte slice是本次日志采集范围，parser自身不是跨进程/跨cid授权过滤器；后续分析仍应按实际场景的时间/连接/response分组。
- 自动保存只用于未来场景，未回写50原件；sidecar与旧raw的证据身份保持分开。

## 独立离线验证

初版完整analysis suite **14 PASS，0.008s**，包含stage list、private reply/body、错误type/hash、超长token拒绝及同timestamp双delta有序保留；两异常反例另外独立复现，不由14PASS掩盖。

随后用当前parser对actual global log只读提取并按冻结sidecar既定时间范围选择，**47条结构逐项与50冻结sidecar完全相等**。没有打印正文日志或新建raw派生文件。sidecar SHA=`ee7b49ab9eae3ff9ae5db5f1b19d0ad73cc0b8fdb4acaeda1564eec95b6509f3`，绑定原report SHA=`4b6d1d115aa24e4e1e5d84a397a9f7dbf702f7504405e1ccca3149a80b9b7c41`。该比较证明现有真实诊断可被新parser保真保存，不是新模型结果。

## 50根因调查边界同步

原50review已追加：Main actual QueueSocket/Core fixture在never-announcing idle/no-owner路径未_begin_response_lifecycle，response_input_sequence=None，而waiting仍留；actual watch推进31秒报boundary timeout。它不需要host-turn变化，不能用先前把boundary搬到hostguard前的方案冒认旧response输入。该复现由Main执行，本审查只记录报告层次、没有新跑fixture；50总体FAIL_OR_PARTIAL不变。

当前待办仅坏JSON递归隔离的精确关闭与最终指纹；除此窄范围无新增具体P1/P2。

## P2关闭与最终冻结

Main最终仅将decoder异常处理改为(ValueError, RecursionError)跳过坏行，保留其余严格字段/类型规则。独立只读确认_timestamp仅对数值溢出返回None；新同一pathological_JSON用例串入1100层嵌套JSON、超大t、超大mono，再跟有效record，实际结果仅保留该有效record。

独立完整suite **15 PASS，0.009s**，包括原时钟/跨owner/重复ASR保守分析。**P2按SOURCE/OFFLINE关闭；本窄范围无其他具体P1/P2。** 不扩无依据fuzz或新系统，不调用模型/服务/设备，不修改50原件或补写其study_text_trace。

| 最终文件 | SHA256 |
|---|---|
| scripts/neko_spoken_turn_analysis.py | `a0bb8cd2dc384ce3a49377e2f7b18da63931c1af8177f66f22f0813c03c96837` |
| scripts/neko_daily_voice_probe.py | `59c028330bdc55e8ac8e1b629593e511d9ae1662edb1b5fe7c1e0a1c1066fdfa` |
| scripts/test_neko_spoken_turn_analysis.py | `043086e7ea1ed36ecff41b72d848e0bfe4fcab00d07abdc9d5349b6cc00a1086` |

报告冻结；自动capture的未来真实运行仍待Main，不能拿15离线测试或47旧sidecar比对称为新在线验收。
