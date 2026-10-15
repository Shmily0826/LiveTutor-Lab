# W-B：评分早退诊断与可说出口的失败

## 已证实与尚未证实

- 原日常库只读一致性快照确认：旧课程保留完整题目与答案、question_id/attempt_id，题目来源课程与当前课程相同；原库 QA/错题/掌握度均为 0。不能据此断言“旧课程污染”就是原因。
- 在副本上运行真实 grading entry/Store/Tracker 配合离线模型，可以评分并追加。遗留课程和跨会话保留题目本身并不必然失败。
- 旧 wrapper 在真实 SDK `Err` 上丢失错误码；若评分 entry 早退、retry 被拒或返回空 feedback，则可能原样返回一个**没有 reply 的 dict**。空反馈甚至保留 `ok=True`。这与真人日志的“同秒返回、reply=False、没有评分”相容，已用先红测试复现。
- **昨晚具体命中了哪条早退路径仍未知。** 原日志没有评分工具的参数/拒绝码；源码与副本不能恢复那两次真实入参。不能把下面的可复现输入假说写成历史根因。
- 后续普通 Native 产品场（未启用实验性 auto-grade）已真实复现：先正常出题，第一次错答与随后纠正均触发 `study_answer`，并立即返回 **ATTEMPT_NOT_RETRYABLE**，QA 仍为原有的 2 条。该码来自 exact question/attempt 校验之后的 retry entry；结合当前题 `attempt_evaluated=False`，可确定这场 Native 给首次未评分答案也带了匹配的 `correction_of`。这是真实产品路径上的已证实缺陷，与昨晚模式吻合；昨晚是否同一入参仍属推断。

## 修改（仅 payload）

1. `_envelope` 保留真实 SDK 错误码。
2. 评分 wrapper 的上下文不匹配、更正不匹配、retry 不可用、entry 错误和空反馈均返回 `ok=False/status=unavailable/reply/relay`；不给失败结果附上虚构分数或有效材料绑定。
3. 按原因说明当前题目/课程、重复作答、不能更正或服务无确认结果；日志只记拒绝码。若异步提交后才发现上下文变化，不谎称数据库一定没有记分，而是要求核对学习记录。
4. 保留题目/尝试身份、课程隔离、重复评分和事务保护，不把无效更正参数自动当成普通答案。
5. 对**精确匹配当前题目和尝试、明确 `attempt_evaluated=False`、且没有评分占用**的 correction pin，按该待评分尝试的首次作答提交，不创建 retry。已评分题仍走原更正流程；未知状态、外来 ID、busy 尝试不放行。同步工具说明，避免模型误把第一答当成必须先 retry。

## 验证

| 层级 | 结果 |
|---|---|
| 新增离线测试 | 7 项通过：真实 SDK Err 保留 code、空反馈、无效更正/失败 retry、异课题目、遗留课程图片出题→重启→答错→纠正完整链、Native 首答误带匹配 pin、busy 尝试不能被绕过。首答误带 pin 的测试在修复前真实复现 ATTEMPT_NOT_RETRYABLE，修复后以原 attempt 评分一次，不调用 retry。 |
| 原有相关离线 | 评分保护 14、纠正尝试 10，独立进程通过。 |
| 完整回归 | 105 模块独立进程，98 通过；7 个历史失败的具体失败测试名与原因和基线相同，无新增失败。 |
| 真实文字模型 SDK | 新课程/新 store，提交固定测试图后出题；答错 0 分，再用该题自身参考答案纠正，判对 100 分。QA=2、wrong_questions=1、mastery_snapshots=2；同一 question_id、新 attempt_id；原错答行 SHA 未变，全部 7 项记录检查通过。 |
| 实际 SDK 失败返回 | 在上述任务 store 上重启、外呼完全拒绝：空 `correction_of={}` 立即返回 QUESTION_CONTEXT_CHANGED；对已评分题普通重答立即返回 ATTEMPT_ALREADY_EVALUATED。两者都有 reply/status，无分数，原 2 条 QA 和计数不变，账本消耗 0。前者能复现“立刻返回而不评分”的一种机制，但没有证据证明昨晚发送过这个参数。 |
| 普通 Native 产品路径（修复前） | 固定 WAV 出题正常；错答与纠正均被错误路由到不可用的 retry，角色说出本轮新增失败提示。QA/错题/掌握度没有增加，证明“提示可说出口”和“成绩落库”是不同验收项。 |
| 普通 Native 产品路径（首次作答修复后） | 唯一一次复核成功：语音出题→错答 0 分→纠正 100 分，均有 Native 回复/音频；新增加 2 条 QA、1 条错题、2 条掌握度。原 fixture 的 2 条 QA SHA 未变，新错答 0 分行保留；新两条属于同一 question_id、不同 attempt_id。没有启用实验性自动评分。7 项 Native 落库检查全部通过。 |

真实 SDK 场账本 DeepSeek 1223→1228（+5），Lanlan.app 保持 108；离线 SDK 拒绝场消耗 0。原始证据在 raw/evidence 的 `codex-wb-real-sdk-20261016.json`、`codex-wb-refusal-sdk-20261016.json`，不提交学习库/原始参数记录。

普通 Native 修复前场证据 `codex-wb-native-product-chain-20261016.json`，账本 1228/108→1248/109。修复后场 `codex-wb-native-product-fixed-20261016.json` 与 `codex-wb-native-database-proof-20261016.json`。音频返回与数据库闭环已证明；可听性与真人仍待用户。

## 部署与剩余项

改动前备份 W-A 已部署 avatar 和 manifest，新 SHA 已同步 manifest 与部署副本；SourceGate PASS。原日常库 SHA 与开工快照相同，原宿主日志仍为 114708 行、结束于 00:22:47；原 launcher/probe 脚本 SHA 未变。没有修改宿主、旧学习记录或旧日志。

待 Opus 复核：若仍复发，利用本轮新增的 content-free 拒绝码定位。需要精确工具参数时，只记录参数键、是否提供 correction_of、题目/尝试身份是否匹配等脱敏信息；是否在宿主增加关联遥测应另行审查。本轮不凭推测放松身份校验。
