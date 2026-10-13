# 三教学工具的真实本地 SDK 材料绑定

## 已确认范围

当前完整契约为 `docs/daily-companion-contract-2026-10-14.md`，原 Goal active。阶段六增量未发布；阶段五远端仍 `4a33054231ce1e7487c76b32e6c9237bbf6f2fd0`。

`scripts/neko_material_sdk_probe.py --teaching-chain` 运行实际 patched Core tool handler、真实 ToolRegistry / remote dispatcher、HTTP SDK callback、Study producer、既有 SQLite 数据库。只替换 Core 输出 owner 为内存量具，模型端使用既有本地 HTTP stub；不连接 Native 供应商、不播放音频、不采麦克风。

本场步骤为新隔离 store 内换课 A → topic 出题 → 评分 held 题 → 学习历史总结 → 换课 B → 查询材料控制回执。角色接收方由可信 Core 注入，不依靠模型指定角色。

结果 `PASS_TEACHING_CORE_SDK_LOCAL_STUB_ONLY`：

- quiz / answer / summary 三条真实回调均有私有材料绑定，Core 均绑定当前量具 owner；quiz 使用 question 字段、其余使用 reply。
- 私有 binding 在送回模型前均剥离，原始模型 arguments 不被修改。
- 出题生成真实 question_id / attempt_id；SQLite 中仅一条评分 interaction 和一条 QA record，均对应这对 ID、同一 session；总结记录也属于原 session。
- 换课通知的精确目标为 `MaterialSDKTestRole`，SDK 接受 blind 控制。`submitted` 不证明设备停止播放。
- 三次模型请求全部到 loopback stub；共享 `bargein-autocheck-20261012` 账本不变：DeepSeek 537/2000、Lanlan.app 53/null、tech 0/0。

## 首次量具失败与修正

`teaching3` 三工具的五项 Core checks 和控制提交都通过，但量具要求 avatar 评分回复返回 question_id / attempt_id。现有评分回复只展示反馈、verdict、score 等字段，因此 `grade_matches_quiz=false`，原结果保留 `FAIL_OR_PARTIAL`，没有修改原证据。

只读查看本场 SQLite 证明评分 metadata 与 QA question 已保存正确 ID。量具随后改为只读核对真实提交记录，不为增加字段而修改角色产品协议。新独立 store 的 `teaching4` 通过。没有清空、覆盖或复用用户数据。

## 证据与限制

本地原始证据：

- `benchmarks/raw/evidence/daily-companion-20261014-teaching-core-sdk3.json`
- `benchmarks/raw/evidence/daily-companion-20261014-teaching-core-sdk4.json`
- 相应 `.host.log`，两个独立 `neko-failure-material-sdk-20261014-teaching3/4` store。

最终结果保留所有调用、真实 ID、按工具 Core checks、账本前后和 child PID；finally 清理本任务 host、stub 与 HTTP client。原始 DB/学习记录不发布。

本场成功响应是预置协议内容，100 分不是模型教学质量证明。当前证明到 SDK / producer / DB 和量具 owner；新 quiz / grade / summary 的真实模型、Native / 实际设备、真人体验仍待。replacement14 的 explain 设备证据不扩张到这三条线路。独立叙述 queue 和长静默恢复仍另外推进。

## 源码审查后四个修复

独立审查 `daily-companion-teaching-binding-review-2026-10-14.md` 保留最初四项真实方法复现；Main 后续修复为：

- 普通 held 题评分显式屏蔽新 saved image / OCR，维持原题依据。
- 同 session 新题替换后，旧评分历史/tracker可保留，但旧反馈不返回/广播，也不污染新题实时 verdict / seed。
- ensure 后当前 session 必须等于请求 session，空 session 不接纳外来 ID。
- 过期可信 Core Study invocation 明确拒绝、不调用 dispatcher；缺省 invocation 仅以空可信 ctx 执行，不透传模型伪造角色。

这些异常负例目前是源码/离线证明：grade10、host31、Native integration5、course6 等；本场 SDK 是正常串行三工具链，不能把正常链通过当异常负例已设备验收。
