# 阶段38：无正文的反馈边界诊断

## 最终交付：源码/离线与部署通过，线上待验

Main 7新诊断＋38原grade route＋5原spoken trace，共50 SOURCE/OFFLINE PASS；独立7再次PASS（.245s），未发现具体新增P1/P2，[审查报告](daily-companion-feedback-trace-review-2026-10-15.md)已冻结。只记录无正文的长度与UTF8 digest，诊断为best effort；若logger失败或identity不全，缺关键链仍UNKNOWN，不把缺日志当provider没发。

已按下表8个各自oldSHA逐项复核并exclusive `.phase38-before`备份，再canonical apply/AST/二次幂等；Source与candidate原Core turn差异保留，未整文件同步。manifest原bytes独占备份在任务raw内；同步4个Source指纹、native_grade_patch helper，新增_wire_trace.py和新patcher fingerprint，当前SourceGate全部源码/实际cwd helper导入PASS，草稿期间的拒启动状态已消除。既有opt-in创建条件在实际_client.py:277–279，未启WIRE_TRACE的client仍None。

新patch helper SHA `e6bd8accfb23a9d1cc78afa21018f2e3f3cd47412d4865c87992df6dfd15480c`，grade patch helper `ad82cf1102d37e57da4aeeeea033cc5ea03f75eb250d2f7a8c2d07bdd3f3b7be`，新test `34163718f1bbe6f8d2af4ff3604b7363edc3e271cdee513ff2e4a4678d95498e`，manifest `40c8f65425f0ed61a9a64318316b540043e2990b14f63e23b3fda0dcc3f3da71`。

本阶段没有启动host、模型、Native、浏览器或任何音频/捕获设备，没有新增请求；原round当前实核DS785/2000、app74/null、tech0/0，无live场。原49/PARTIAL、22→7根因UNKNOWN保留。下一阶段39只安排一次有新增完整观测与反馈边界的必要固定WAV场；必要speaker沿已设4%，禁止所有mic/capture/loopback、不调音量。新场要先读四记录与本报告/审查、核SourceGate/账本/空端口，不复用旧输出文件或造ASR/题/ACK。

Main先本地开发，当前待独立review/部署，尚无模型或设备调用。复用原RealtimeWireTrace的默认关闭/既有WIRE_TRACE实例，不新建runtime helper或数据存储。

实际provider每条audio transcript delta在原first-delta节流前记录chars/UTF8 bytes/SHA256；done全文另记，不与delta相加。按实际generation+response_id及stage/scope/token累计最多64流，只保留digest状态/计数，不留正文；缺identity、容量不足或异常不冒完整prefix。诊断异常吞掉，不改变guard/输出。

其他边界：正式grade_complete的bare reply；send_event已成功await transport.send的实际序列化payload，bare reply与完整envelope分别hash、明确local_socket_write_only不是provider ACK；5个既有Omni callback调用前；Core callback entry、真实sync queue写入后、成功WS await后，后两项context在该方法首次await前冻结，不随session替换误记新owner。Core entry上下文来自当时Core session，不是另行证明provider utterance authority；缺response ID不强拼累计。Native沿阶段37完整事件本地比较，不新增正文日志。

Main7新fixture PASS（.254s）：4实际Source文件temp canonical replay/AST/幂等；actual22字符relay表达式与payloadprefix完全匹配；actualsend成功/失败及await内gen2→3保持旧writegen；actualOmni buffer flush与Core entry/queue/WS含takeover拒绝及await内session替换；actualgrade marker；多delta有序累积、无ID、64上限、logger异常。原grade route38 PASS（6.618s，实际SDK/SQLite在fixture、假模型/网络），原spoken trace5 PASS（.035s）。共50 SOURCE/OFFLINE，仅该scope，无房间mic/capture/loopback/扬声器。未重跑37未改基线。

两host部署前实核与temp canonical结果（candidate Core turn与Source旧差异各自保留，不整文件同步）：

| host | file | before SHA256 | planned after SHA256 |
|---|---|---|---|
| `benchmarks\raw\neko-product-host` | `main_logic/omni_realtime_client/_wire_trace.py` | `714502f39f0368132556664a92734e41ac02521d0035e0ce04ae4a6952ea2140` | `9b30a9dfe4c314b223590f36020b09e6071da8f8a9451a4fd081a51aebb191c5` |
| `benchmarks\raw\neko-product-host` | `main_logic/omni_realtime_client/_transport.py` | `634ec3f9a681bf0a4fc1e63a554fcae6a87ca3b5dafd7e914ec234a36ffed853` | `78df4190470f8d6ec43ae94c2995fa1eef9b3e30a59b3673418b32c6ddacdd65` |
| `benchmarks\raw\neko-product-host` | `main_logic/core/turn.py` | `4513a0a76f94e39097a2fce7e0be5b66aaf3d59baecbc8e4e907f2e221b93f1e` | `f0d6b1940265a7cdd93f890df85c62e2ada0707a4b527d6b6563a24c10f22e3a` |
| `benchmarks\raw\neko-product-host` | `main_logic/core/tool_calling.py` | `fd5160b4d8c7836c9d1167c346163ef6aeed3076d9fa0326843c522c1f3cab86` | `f4c0eaed424284215a47c34dc0dc3b8d4a47828daa04d80994ad05fa5911f56b` |
| `candidates\N.E.K.O` | `main_logic/omni_realtime_client/_wire_trace.py` | `714502f39f0368132556664a92734e41ac02521d0035e0ce04ae4a6952ea2140` | `9b30a9dfe4c314b223590f36020b09e6071da8f8a9451a4fd081a51aebb191c5` |
| `candidates\N.E.K.O` | `main_logic/omni_realtime_client/_transport.py` | `634ec3f9a681bf0a4fc1e63a554fcae6a87ca3b5dafd7e914ec234a36ffed853` | `78df4190470f8d6ec43ae94c2995fa1eef9b3e30a59b3673418b32c6ddacdd65` |
| `candidates\N.E.K.O` | `main_logic/core/turn.py` | `6ed9e294c612a396a49a69a29ae94818190cf40fad143eadaad56817c735a8fe` | `77b04b7761218b52100aaa217f164895678b9648b8d52c4452711d10b3ac5c3d` |
| `candidates\N.E.K.O` | `main_logic/core/tool_calling.py` | `fd5160b4d8c7836c9d1167c346163ef6aeed3076d9fa0326843c522c1f3cab86` | `f4c0eaed424284215a47c34dc0dc3b8d4a47828daa04d80994ad05fa5911f56b` |

当前manifest仍旧，因native_grade_patch helper草稿hash变化，SourceGate应拒绝启动；不得称已部署。独立review后再核上述oldSHA、exclusive phase38-before备份、canonical精确apply，补manifest含_wire_trace.py与新patch helper指纹，SourceGate全通过才可启动。

原49 raw/PARTIAL不改；22→7字符根因仍UNKNOWN。账本原round DS785/2000、app74/null、tech0/0，无live进程。下一仅为新可区分证据的一次必要场，随后依据实际边界修，不能为额度重复跑；A–F剩余全保留，日常AUTO仍OFF。


阶段38发布/安全节点核验：10精确allowlist commit/push 60f4c1fb8c7c3fb5b0a868538b9faff0f50a5d83，remote同SHA/publisher clean/master未变，Root index空；SourceGate PASS。无raw/DB/录音/备份/密钥发布；contract原169行SHA不变。未新增在线/设备，ledger785/74/0；48911/48916/9234无listener。Goal当前接口再核active，未暂停/重建/标完成。下一39必要诊断场后按结果继续，局部问题不结束全A–F。
