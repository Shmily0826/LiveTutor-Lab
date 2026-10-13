# 总结入口课程 / 会话一致性：阶段六

2026-10-14。先完整承接contract、plan、status、blockers；沿用长期Goal，不重建或标完成。仅修改canonical `payload/study_companion/entry_tutor_summary_entries.py`，新增 `scripts/test_neko_summary_material_guard.py` 与本报告。共享context finalizer、Store、wrapper、consumer、event bus、manifest、账本及其他Agent文件未修改。

## 已交付

原总结入口先ensure/read旧session历史，再由context builder重读当前state的course；换课发生在这些await之间时，可能将旧历史与新课程enrichment交给模型。现在：

- 首次await前捕获course/session，不包含图片hash；支持wrapper传可选私有 `_material_context`，仅接受这两个字符串字段，陈旧/错误/混入图hash的context诚实返回course_context_changed。
- ensure后只有原session为空且course未变时可初始化；非空session被重启、到期或换掉，即使仍是同课程也拒绝。解析后的session必须与真实current session一致。
- history读取后、context builder后、模型后、shared finalizer后、叙述返回后均锁内核对同一context；tutor_context的course/session不匹配时不送模型。不拿新的course enrichment给旧总结。
- 初次读取的真实history同时用于模型参数、context.history与session_history。总结按已有学习记录工作，禁用视觉输入并清模型context中的当前OCR/vision snapshot，不依赖同课随后换掉的图片。
- extra_context携带 `_material_context`，复用原finalizer的短SQL锁和live seed守卫；没有新表/新记忆系统。换课发生在SQL开始之前，不写总结；旧context仍有效时已经提交的旧总结保留在旧session，随后换课不污染新seed、recent events或public reply，不清任何历史。
- 叙述入口获得payload副本，附原 `_material_context` 与 `_session_summary_seed` 快照；这两个私有字段不加入summary public返回。叙述前后的入口检查不冒称异步queue的最终准入保证。

## 定向验证

用宿主隔离venv执行：

```powershell
& benchmarks/raw/neko-product-host/.venv/Scripts/python.exe -X utf8 -B -m unittest discover -s scripts -p test_neko_summary_material_guard.py -v
```

**14项通过，1.081秒。** 使用实际summary entry、原context builder/Store/Tracker/finalizer和全新临时SQLite；只替代模型输出、叙述边界与精确await暂停点。没有导入/启动desktop host、模型、音频、房间麦克风或窗口。

| 检查 | 结果 |
| --- | --- |
| 正常原course/session总结、DB来源metadata、原history保持 | PASS |
| stale/非法私有context在ensure/model前拒绝 | PASS |
| ensure期间非空session换代，同course或异course均拒绝 | PASS |
| 原空session同course可创建；异course不能初始化后绑定旧请求 | PASS |
| 实际SQLite history read期间换课 | PASS，未进模型 |
| 原context builder snapshot后、实际DB enrichment期间换课 | PASS，查询仍限定旧course，旧请求拒绝 |
| builder返回错配course/context | PASS，未进模型 |
| 模型等待时换课 | PASS，无summary row/新course seed污染/叙述 |
| 同course仅换图片 | PASS，history总结有效，图/OCR未作为模型材料 |
| shared finalizer短SQL开始前换课 | PASS，不提交summary |
| SQL已开始时换课等待原_lock | PASS，旧summary提交保留；新course seed/事件/叙述/返回阻断 |
| 已提交后、返回前换课 | PASS，旧row保留，不叙述/不返回旧总结 |
| 叙述await期间换课 | PASS，传原快照、最终public返回拒绝；不声称queue已撤回 |

首次运行13项通过，唯一量具错误是取rows[-1]假设最新总结（Store实际排序不同），KeyError发生在断言而非产品。已按kind精确选summary row，第二次14项全过；不把该量具修正说成产品回归。

主线负责补旧course-memory AST fixture的globals，并报告原6项通过；本Agent未修改或重复运行该批。新测试没有将假模型输出认领成真实模型质量证据。

## 叙述集成剩余边界

现stock `_emit_session_summarized_event`在获取_lock后读取live session_summary_seed，排队后的消费者也需检查context；仅入口pre-check不能阻止等待期间换课。因不在独占范围，本Agent未改该helper、Store或consumer。

给主线的具体接口：叙述payload包含 `_material_context={course_id,session_id}` 与 `_session_summary_seed`。producer应在实际调度前核同一context并使用原seed，consumer在真正入模/播放前再核；course/session不匹配丢弃，不把图片hash作为history summary的失效条件。必须防producer等待之后拿新course的topic/count补旧summary。入口已做前后检查并提供原快照，晚queue取消效果仍属主线后续范围。

本阶段未部署、未在线、未SDK整合运行、未设备播放或真人体验。主线最新537/53/0及已发布4a33054是交接快照，本Agent未重查/调整账本，新增外部调用0。所有定向测试已结束、临时SQLite已关闭清理；没有任务host/native/audio进程。

交付冻结：只上述三个独占文件；下一步由主线整合wrapper subset、叙述producer/consumer及部署，按受影响路径补证，不重复旧教学/图片验收。Goal仍active。
