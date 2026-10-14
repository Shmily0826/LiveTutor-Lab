# 阶段25 正式评分离线量具与 observer 增量审查

SOURCE / OFFLINE 完成冻结。仅新增 `scripts/neko_native_grade_acceptance.py`、`scripts/test_neko_native_grade_acceptance.py` 和本报告；未改 voice_probe、产品、host、manifest、四记录或账本。本 Agent 没有启动应用/服务/API/浏览器/音频/捕获/回环、调整音量或运行线上。Main 安排实际单场，不能由本报告宣称实际评分声音已通过。

## API

`grade_snapshot(db)` 接受显式已有绝对 task DB 路径。用标准库 SQLite mode=ro/query_only/timeout0/closing 和一个读取事务。仅投影 kv/state 的 course/session/current question 的公开题干及 qid/aid/evaluated、last_answer_evaluation；完整指定 QA 行只用于 SHA256，并返回 `{id,row_sha256,session_id,question,user_answer,eval_result}`；interactions 仅 kind=answer_evaluate 返回 `{id,session_id,input_text,metadata}`。不读普通 interaction、完整 state/history、config/keys，不复制或写 DB；已知 private answer/rubric/cache 等字段递归剥离。每类记录超过10000行诚实拒绝。缺库不创建，错误返回 `{ok:false,error:"grade_snapshot_unavailable"}`，不输出异常/路径/学习数据。

成功快照有 `ok:true` 及约定字段。快照含学习者题干/原回答，仅供 Main 的本任务 private evidence，不应发布或调用于无关用户 DB。

`grade_acceptance(report)` 是无副作用纯判据，返回 `checks/result/old_output_retirement_evidence/physical_output/human`。全 checks 成立时仅 `CANDIDATE_GRADE_FLOW_PASS_REQUIRES_SEMANTIC_REVIEW`，否则 `FAIL_OR_PARTIAL`；physical_output 始终 `UNVERIFIED_NO_LOOPBACK`，human 始终 `PENDING`。不把本地 wirewrite、SDK submitted、provider PCM 或播放 active 当 ACK 或听见。

单次普通 pending-answer 场景要求：初始四 ID 非空且 pending；结束同 course/session/qid/aid、题干不换、evaluated=True；last grade、新 QA、正式 interaction.payload verdict/score 一致；恰新增一 QA、所有旧 QA 全行 hash 保留；恰新增一 answer_evaluate，旧已投影 grade interaction 保留；新 QA 原 answer 和唯一 Native ASR 全文精确一致（不压空白/截取），metadata qid/aid 与 material_context course/session 全匹配。只凭口头回复不能过。

grade_markers 恰 accepted/grade_complete/relay_written 三行，校验各自四身份、result_attempt_id、connection/scope、旧新 token 及实际 profile。accepted/complete 同连接和scope，relay为连接+1及更高scope；三行 profile 与 report 均须实际 `lanlan_app_gemini`，不能把 STRICT 夹具冒充免费真实路由。正式完成必须在输入 speech_end 后、输出观察结束前。Native ASR/取消/PCM/调度依当前 turn window，NaN/缺字段/时间错误拒绝。

输出必须新 token，原 token cancel 接收仍为必需。所有本turn PCM 和非空 Native response text 均在 grade_complete 后；真实新 token playback schedule、最终 inactive/remainingSeconds0/reason=source_ended/correlationId新token/updatedAt 在窗口内。Native 的最终真实 shape 没有 queueLength，本实现不编造该字段。快速 PCM 可以略早于 relay_written logger（sent future回到协程后才记日志），不会因此假失败。

output-only/no mic/capture/loopback/no volume change，以及 installed readonly/flag/captureBlocked/8API 名称集合全部必需。只有一个 turn，且无 timeout/failure/cleanup errors。缺失并不补成成功。

## 旧 queue 退役的两种证据

初版要求 old token 的 native_connection_cancel stopreceipt。Main 查实际播放器后确认：old token 被 hold、fresh renderer 从未收到 old PCM 时，播放器根本没有 old queue，不会发 stopreceipt。强逼会假失败，不能伪造回执。因此最终 check 改为 `old_queue_retired_or_never_received`：

- `NATIVE_STOP_RECEIPT`：原 token 的真实 device speech_playback_state，active=False、reason=native_connection_cancel，且在正式完成之后。
- `FRESH_RENDERER_NEVER_RECEIVED_OLD_PCM`：fresh Native launch receipt 的正整数 pid/windows count、fake_silent_input=False；initial cumulative binaryFrames=0，observer安装/initial snapshot均在本轮input前，initial无活动queue；final累计binaryFrames等于**全部**trace audio_frame数量且正数；所有audio_frame均在本turn window、新token、正式完成之后。trace截断/累计不匹配/initial>0/旧token/窗口外音频均拒绝。原 token cancel 接收仍要求，不因无旧queue放宽。

第二分支只说明该新 renderer 的完整观测中没有收到 old PCM，不叫“已停止旧可听语音”，也不证明PID/设备所有权。fresh launch/限定root observer及进程所有权仍由 Main 既有入口负责。结果单独标明 evidence 分支，避免把没播放过冒充可听取消。

## 离线证明与适配纠正

`python -B scripts/test_neko_native_grade_acceptance.py` 最终 11 PASS，0.294s。真实 small SQLite 与报告 fixtures；覆盖成功、缺测、foreign/空身份、extra QA/删除/旧全行hash变动、重复正式interaction、无/错/重复ASR、无PCM/取消/stop/调度、提前音频/lategrade、marker scope/conn/token/NaN、STRICT错误profile、capture/终态错误、fresh无旧queue及trace/counter缺口、缺库不创建与exclusive lock。正例允许首PCM早于 relay_written，但不允许早于正式 grade_complete。没有模型/设备。

最初 helper 假设 Native.windows 为列表；Main 在运行新场**之前**核现有raw确认真实为整数 count（例如1），最终已改为严格正整数并同步 fixture，未把错误schema强推在线后再追认。Main 自报 actual C32 task snapshot ok/QA2/grade2，本 Agent未读该 DB，不能当独立实测。

最终 SHA256：helper `f7e69619178f673b0bea3bfcea765fa5625e65d32ef3cc6d710d7bd533b6c4a4`；tests `04b0d932bc2ecd5f19ae9d0c23ab50bce2aa7ae465f55bf05a03a412cb9328b4`。

## Main observer / trace / normalizer 窄审

已只读核 --grade-current / --prepare-grade-quiz：只允许output-only、一个固定WAV、已有隔离材料、明确 task fresh provenance；拒绝普通daily store、混合teaching/followup/图替换/手动turn等模式。原输出文件存在就拒绝，不作自动retry；prepare可显式调用一次正式quiz，失败在Native前退出；原 round/DS上限/app记录/tech0沿用，不换供应商，不因失败重置。现场由 Main 独占安排，本 Agent未发请求。

发现一个接线P2并即时反馈：grade_snapshot 错误返回 ok=False，但原 preflight 仅检查另一次 read_question_pin；可能在 QA schema/旧eval JSON损坏、或两快照间换题时，明知baseline不成立仍开启付费Native并必然验收失败。Main已修：Native前 baseline.ok必须True，snapshot四ID/evaluated与完整read_question_pin逐字段相等且pending；否则拒绝、不重读追新题/重出题/重试。当前源已精确复核该条件，SOURCE CLOSED；尚无该追加条件的独立全启动证明。

observer只取before/after快照，输入路径首次 frame pin单次读取是另一独立authority动作，不是每frame读库。after在finally记录；cleanup及timeout判定完成后才 grade_acceptance/report finalized；旧fail/raw不重写为通过。日志仅从当前 log_start 后解析 [study-grade-event] JSON，缺/混profile不猜成功；trace producer记录物理source profile/token/conn/scope与pin/result IDs，不复制题全文或原回答。

`python -B scripts/test_neko_native_grade_probe_plan.py` 独立5 PASS（0.157s）：真实observer AST preflight + mock停止于port前，没有开端口/host/device。此5case不覆盖之后新增snapshot/pin preflight条件，不外推。

normalize_material_audio 增量仅接受原 HELPERS 或精确插入 gradehold 的 HELPERS；旧draft仍须既有hash白名单，否则RuntimeError保留源。独立纯字符串检查 canonical/精确grade-hook保持字节原样，修改gradehook return True→False的unknown被拒。没有写任何运行树；整套30file replay/AST/幂等与SourceGate由Main另记，不借此称当前实际host或provider验收。

本报告及本子任务代码最终冻结。下一步 Main 安排唯一必要真实 fixed-WAV 场、保留失败原证据；候选checks通过仍需核方向/成绩语义，再继续剩余Goal及最终集中真人体验。

## 场36之后的 quiz receipt 适配窄审（不执行）

Main 报告场36已 terminal、未启动 Native，仅正式 quiz 成功并保存 qid/aid；量具误要求 rich `study_quiz` 不存在的 ok 字段，原失败保留，DS+1至678。这是 Main 提供的运行事实，本 Agent 未读其 DB/原raw或账本。

只读复核新 `grade_quiz_prepared`：要求顶层 is_error 严格 False、output.tool 为 study_quiz、degraded 严格 False、题干/qid/aid均非空字符串；ok 不存在正常，只有显式 False 拒绝。没有把 failed/degraded 或其它 tool 放行。坏 shape 会在 Native 前出错，未用猜测 defaults 补成成功。

随后仍先核 baseline.ok/完整 snapshot pin 与 read_question_pin 相等且 pending；若本轮 prepare，还逐项核 baseline qid/aid 等于刚才那次正式 quiz receipt。任一变化都拒绝，不为完成场景重新出题、追新题或把 receipt 当评分通过。未prepare的复用路径不会再次调用 quiz。

新增第6测试从源读到：实际 rich 无ok receipt为正例，空qid/缺aid/degraded/显式okFalse/wrongtool/is_error为负例；本次依 Main 指令没有执行任何测试或启动服务/设备。源码层未发现新具体P1/P2，补丁不改评分/捕获/预算准入。Main唯一场37在本次审查时仍运行且不带prepare-grade-quiz，复用同题；本 Agent不干预、不认领pending结果。等待终态后再按 Main 指定私有报告范围独立读审。本追加后冻结，不改 helper/code/共享文件。

## 场37终态后的 QA question JSON 适配与独立派生重算

Main 报告场37 terminal exit1，正式wrong0/新增一QA/11 NativePCM，原验收只 formal_identity_and_asr=False。独立只读指定任务fixture原报告后确认：finalized=True、无failure/timeout/cleanup errors，原19check仅该一项False；三个 QA.question 都是 JSON 字符串。真实 Store 用 json.dumps 保存完整 held question dict（含题干/qid/aid及private answer/rubric），初版 helper 错将 QA.question 当纯题干比较，且仅对字典递归 _public 无法剥除序列化字符串里的私有字段。原raw保留失败，不追写为PASS。

已按新授权仅修本 helper/tests：snapshot 的 QA.question 若是 JSON，严格解析对象并验证题干/qid/aid均为非空字符串，只输出这三个公开字段；完整原raw行仍先用于 row_sha256，hash公式及旧历史保留检查不变。validator 接受这种公开dict、原raw37的Store JSON字符串、历史plain题干。JSON对象的题干和两ID必须都等于baseline；坏JSON-looking文本、缺/错ID、数组或JSON标量拒绝，不能回退plain绕过。legacy plain仍须题干精确相等以及正式interaction四ID/ASR全部原守卫成立。没有放宽任何marker/cancel/PCM/capture/terminal判据。

正例 fixture 已改为真实 Store 的 json.dumps(held_question) 保存形态，含 private reference/rubric，验证新 snapshot 不含它们；另测原raw字符串和旧plain格式、错题干/qid/aid、缺ID、坏JSON/array/scalar、坏JSON快照诚实ok=False。最终 `python -B scripts/test_neko_native_grade_acceptance.py`：13 PASS（0.334s）。没有启服务/设备/模型或读写任何真实任务DB。

授权只读重算来源：`benchmarks/raw/evidence/daily-companion-20261015-native-grade37.json`，原 SHA256 `c8484c5ed76bfdca348c43c42dbc605c1020bcdc78814ffca66196a4a81e9035`，重算前后 bytes 比较相等。使用修后的纯 grade_acceptance 对原报告输入重算，19check全True，结果仅 `CANDIDATE_GRADE_FLOW_PASS_REQUIRES_SEMANTIC_REVIEW`。只用 x 模式创建新派生文件 `benchmarks/raw/evidence/daily-companion-20261015-native-grade37-rechecked.json`，SHA256 `709a91cad5cb74a4cdaf1ad234b531694baf4bd8393a091011fc8573cc3073d8`；不复制学习题干/私有rubric/完整history，只保留来源hash、原判据、派生判据、必要计数和wrong0。若已存在则拒绝覆写，本场没有重试线上。

独立派生证据层：原报告QA2→3、旧QA hashes保持、唯一正式answer_evaluate四身份/完整原ASR对应、wrong0、11 NativePCM、新token播放终态以及fresh renderer无oldPCM分支成立。该分支是 `FRESH_RENDERER_NEVER_RECEIVED_OLD_PCM`，不是听见旧答案后停止的验收。实际题目/回答的评分语义仍需 Main 人工源码/模型语义审阅；不因全部量具check为True就认领整个Goal或真人体验。physical_output仍 `UNVERIFIED_NO_LOOPBACK`，human仍 `PENDING`。这是同一已结束真实场的派生重算，新增外部调用为0，不是新设备试验。

最终 helper SHA `5c7347086e0b1c5807172e2932f53f25580c0527ac68c60bfe4652d917a71b02`，tests SHA `37ff081fdc68d171e0707a5e5ca52a1bef1a314b065d9f8309837eeca81aef52`。本次仅 helper/tests/本报告及明确授权的派生新文件有写入，原场36/37失败文件、预算、用户数据、host/product/shared文件未改。完成后冻结。
