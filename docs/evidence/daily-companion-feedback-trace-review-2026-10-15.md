# 阶段38反馈边界诊断独立审查

2026-10-15。只读 `scripts/neko_study_text_trace_patch.py`、`scripts/test_neko_study_text_trace.py` 及 `neko_native_grade_patch.py` 末尾text_trace_targets接入，定向读取其实际WireTrace/send/Core callee。仅新增本报告，无生产/runtime/manifest/共享记录/raw/DB/账本修改，无服务、API、模型或音频/捕获设备动作。

## 结论

本窄范围**未发现具体新增P1/P2**。诊断记录正文长度与UTF8 SHA256，复用既有opt-in RealtimeWireTrace；不改owner、guard、queue、SDK评分或音频路由。独立新6项离线通过。可以由Main继续精确hash/SourceGate与部署工作；当前草稿不是已部署证据，也没有解决或定位场49短反馈根因。

## 证据边界核查

- WireTrace仅在现有NEKO_REALTIME_WIRE_TRACE启用的client上存在，未另建全局logger/队列。新entrypoint内部try/except Exception吞掉诊断失败；正文只瞬时编码/hash，日志无reply、delta、instruction、tool args或PCM/base64字段。标识只沿既有cid/gen/response_id/scope/token scalar投影，长度/hash是诊断，不是授权凭据。
- provider_delta/provider_done记录插在record_recv的event_type读取之后、原first-delta去重/节流判断之前，因此每个实际delta可单独记录，不被原结构wire只保留首delta的行为遗漏。累计key含stage/gen/response_id/scope/token；必须正int generation且非空有界response_id，最多64个key。缺身份/容量满明确cumulative_available=False，不清掉旧累计或假称新前缀完整。
- 累计hash按实际delta顺序update，不能按相同时间戳去重。Core/Omni可能有scope/token分段；跨key不可擅自拼成完整provider流。64容量是整client记录器生命周期上限，耗尽后per-delta仍可用，但不能宣称全流累计仍完整。
- relay取证位于actual `await transport.send(payload)` 成功之后，使用发送前已冻结的trace_generation和真实serialized payload；bare reply从精确authoritative前缀JSON投影，另记整个wire envelope的bytes/hash。两者不混比，不对send失败记write receipt；标签明确local_socket_write_only，不能冒充provider ACK。
- 五处Omni on_output_transcript callback前插入同样计数/hash，不替换callback入参或顺序；覆盖buffer flush、done buffer、done transcript及streaming buffer/delta位置。callback来源metadata取当时client状态，不是伪造provider utterance ID。
- Core入口在takeover/grade hold等guard前记录core_entry；send_lanlan_response清洗后实际queue.put后记core_queue，成功WS await后记core_ws。source与identity在本次调用首次await前捕获并经closure使用，不在await后把旧消息诊断误标到新session。没有取消原guard或为了日志重试发送。
- grade_complete沿现有result记录grade_reply；只取已经返回的reply，未多调模型/工具，也未改变正式成绩。

诊断自身logger异常时记录可能缺行；累计器可能已经观察到该delta，不能把日志缺行当provider未发送。分析必须检查stream_chunks/累计数与边界证据，缺关键段仍UNKNOWN。此为best effort观察，不是强制完整审计或故障修复。

## 独立定向离线验证

执行已有Source venv：

```powershell
.\benchmarks\raw\neko-product-host\.venv\Scripts\python.exe -X utf8 -B scripts/test_neko_study_text_trace.py
```

**6 PASS，0.234s。** 该test初始化在自身临时目录复制现有四个actual host源码，使用actual canonical patcher首次回放、state=patched、AST解析、二次bytes不变；未写实际host。检查包括：

- 实际WireTrace连续3个provider delta在旧节流前逐条有记录，22字符累计hash匹配done，全句与7字符前缀均不出现在日志JSON正文。
- 缺response identity不造累计，65新key仅存64，logger抛错不传播。
- actual relay文本表达式生成的bare reply和serialized envelope哈希各自准确且不同。
- actual transport.send_event用假socket写成功时记录原generation=2，即便await期间client generation变3；失败socket保持原异常且不新增write receipt。
- actual Omni buffered flush把完整22字符交callback，hash不截断。
- actual Core handle_output_transcript/send_lanlan_response输出完整文本，queue/WS hash一致；takeover只记入口不发布；WS await期间session替换后仍记录原gen/token。

四个actual源码方法的外部socket/owner/config等是定向fixture seams，不是provider、真实runtime会话或设备验收。此处独立跑到的是Main补齐后的6项，不沿用最初4项数。

## Canonical/replay与未执行项

native_grade_patch末尾先保留既有UPGRADES/TRACE/TAIL/DAILY转换，再把targets与已组合replay交text_trace_targets。新patcher对targets及已有replay的new端应用同样增量，避免未来回放又插回旧诊断前版本。已用四个actual host文件临时验证首次/AST/幂等，不声称全候选树、未知历史变体或实际部署已通过。本轮没改既有normalizer/生产文件。

Main说明SourceGate当前因helper草稿hash与manifest不同应拒启动；本审查没有启动或绕过该门禁。后续先按旧SHA部署/更新清单及SourceGate，再由Main决定是否值得一次必要场。原49 raw与PARTIAL、22→7字符责任边界UNKNOWN保持，不凭新增日志或纯重放追认PASS。

## 最终审查指纹（SHA256）

| 文件 | SHA256 |
|---|---|
| scripts/neko_study_text_trace_patch.py | `e6bd8accfb23a9d1cc78afa21018f2e3f3cd47412d4865c87992df6dfd15480c` |
| scripts/test_neko_study_text_trace.py | `1056e321b932c9f31d7248beb6ae46109f5d224be96db6eda80b107899ba4391` |
| scripts/neko_native_grade_patch.py | `ad82cf1102d37e57da4aeeeea033cc5ea03f75eb250d2f7a8c2d07bdd3f3b7be` |

本报告冻结。未生成新音频、未发请求、未操作进程或额度。

## 最后新增grade marker用例复核

Main补actual `_record_study_grade_event` AST测试后，独立重跑当前完整定向suite：**7 PASS，0.245s**。accepted阶段不生成grade_reply，grade_complete才记录已返回reply的正确hash，private_rubric测试哨兵未进入新诊断JSON。source patcher和grade接入指纹仍同上，test最终SHA改为 `34163718f1bbe6f8d2af4ff3604b7363edc3e271cdee513ff2e4a4678d95498e`。

再次核Corecontext在text_clean前冻结，入口另独立快照；send与WS await后仍用原identity，不采新session字段。未发现新增具体P1/P2。Main另报告route38、spoken trace5及两host四文件tempcanonical/AST/幂等通过；本次没有重跑该两组，也未把两host的turn文件强行视为相同。部署必须各自旧SHA核验、保留既有差异；本报告不认领实际部署或在线结果。最终再次冻结。
