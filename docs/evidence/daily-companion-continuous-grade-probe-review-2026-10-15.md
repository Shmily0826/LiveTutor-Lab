# 阶段34：三WAV连续评分量具独立审查

本轮只读 `neko_daily_voice_probe.py` 的 grade-chain 增量、`neko_native_grade_acceptance.py` 的 grade_chain_acceptance、对应 probe-plan/acceptance 两测试；只写本报告。没有改这些脚本或共享记录，没有 host/service/provider/Native/设备/mic/capture/loopback、用户DB、账本或部署操作。阶段33发布 ae248a14 与 Main 旧SHA部署/SourceGate 是 Main 的已报告前提，不由本审查重新执行。

## 初稿已核边界

- grade-chain 必须 output-only、三WAV teaching-chain、已有隔离图片；与 grade-current、prepare-grade-quiz、correction等混合路径拒绝。已有 store 名/provenance.fresh、项目raw containment、文件存在及声卡权限守卫在端口/host前执行，原 Daily store 拒绝。它不赋予 mic/capture/loopback 权限。
- host ready 后只读 grade_snapshot 与 `read_question_pin(include_empty=True)` 核健康空题/course/session；没有清理 current_question 或编造 pending。首轮之后读取实际Store pending四身份，再进入下一WAV；无有效新题就停止，不用模型口头题替代正式题。
- 输出仅经本任务 output-only verified Native fixed-input controller；不会因新增 grade-chain 初始化回环。每帧失败/revocation停止输入，超时/cleanup错误会令量具失败。原 permission/ticket/socket守卫未放松。
- 答题轮用其专属 snapshot/window 调用原 `grade_acceptance`，完整复用现有普通成绩检查（19原检查加supported_grade_intent），没有改成“听到回复=评分”。第三轮对比题目、QA、正式grade_interactions和last evaluation，要求不额外评分/换题。
- 候选结果仍要求独立语义审核，physical_output始终UNVERIFIED_NO_LOOPBACK、human=PENDING；wire写入/排程不当 provider ACK 或实际可听。

## 独立初稿离线执行

```powershell
.\benchmarks\raw\neko-product-host\.venv\Scripts\python.exe -X utf8 -B scripts/test_neko_native_grade_probe_plan.py
.\benchmarks\raw\neko-product-host\.venv\Scripts\python.exe -X utf8 -B scripts/test_neko_native_grade_acceptance.py
```

实际 **9/9 preflight PASS（0.264秒）**；**24/24 acceptance PASS（0.637秒）**。preflight执行实际AST main直到模拟端口哨兵，未开端口；acceptance为纯检查器/临时SQLite fixtures，不是音频/模型场。通过不能消除下列未覆盖反例。

## P2：首/第三轮未以真实回执证明完成

`three_completed_native_turns` 初稿仅检查 turn.native_pcm_frames>0、native_reply非空、无timeout和时间顺序，没有检查首/第三轮自身 Native snapshot、ASR、实际turn end或inactive/source-ended终态。现有 ContinuousGradeEvidenceTests 初始正例本身没有 first/third native_snapshot，仍全部checks True；把第三轮 native_pcm_frames 设成布尔True也通过。

已用该 fixture 直接纯函数复算确认，未构造服务或改测试。建议对首/第三轮也从独立turn-window的Native trace核实际ASR、正bytes PCM和回复、对应token的实际system turn end + source-ended/inactive终态；不要仅以派生计数/文本或system事件来自任意旧轮判断完成。该修正不应改变 physical/human未知边界。

## P2：失败/未写入delivery仍能“同连接两输入”通过

`same_connection_first_two_inputs` 初稿只用 started_wall 和 connection_generation。把 fixture 两条 phrase_deliveries 全改成 `result='failed', written_samples=0, output_samples=48000`，全部连续checks仍True。这把开始尝试当成实际输入提交。

建议保留每轮恰一条和相同connection，另外要求严格int connection/sequence、完整positive output==written、明确成功result与finite完成时间，且落在相应输入/观察范围；序号要证明新实际输入而不是重复logger。对failed/partial/zero/bool/不完整/重复的负例 failclosed。已向 Main 报告，本轮未修改实现。

## 需要精确保留的旧队列适配边界

答题 view 保留整场 native_initial 与累计 trace。首轮 quiz 已有旧token PCM，所以原“fresh renderer never received old PCM”替代路径不能用于这个答题轮；它应有真实旧token stop，或另有严格证明“旧token此前已经完整排空、之后无旧PCM”的实际回执。不能通过裁掉首轮trace/重置binary计数伪造fresh，也不能捏造stop receipt。本审查没有越范围读player或宣称一定会失败，此处交 Main 核既有真实player语义后决定；原严格单次评分判据应继续复用。

首轮 wire 的 study_quiz arguments.done 是provider调用请求，和新Store pending共同支持出题链定位；后续终态仍需审核实际tool/result/题目内容与学习材料，不能只看request就说整个教学成功。第三追问内容与参考方向也需人工语义读审，结构check只负责不添正式成绩。

当前结论：9/24离线通过，但两具体P2仍待Main收紧再运行必要真实场；不是全局阻塞或Goal完成。后续修复/复测与最终指纹追加，不覆盖初稿发现。

## 两处P2修复复核与最终冻结

Main 已收紧 `_completed_native_turn`，每轮使用自己的 native_snapshot 与输入窗口：要求恰一非空ASR且在speech end后、实际正bytes PCM、同terminaltoken、非空Native文字、实际system turn end、该token播放排程，以及source_ended/inactive/remainingSeconds=0和updatedAt范围。布尔派生计数已不能替代这些回执；首/第三轮缺receipt、active/wrongtoken等新增负例拒绝。

同连接两输入现在还要求每轮恰一条 `written_waiting_provider_boundary`、已知arrival估计timebase、严格正int generation、positive source/output/written counts且source>=output==written，以及本轮 sealed<=started<=first_write<=completed 时间链。failed/partial/bool generation/缺字段均拒绝。实际logger当前没有input_sequence字段，**不为测试捏造seq或provider utterance ID**；这些仅证明本地完整写入和同generation，不能称provider已ACK。答题仍完整复用原grade_acceptance，不凭phase counts重新实现弱版正式成绩检查。

本审查独立重跑最终同两命令：**9/9 preflight PASS（0.284秒）+25/25 acceptance PASS（0.638秒）**，包含新增负例。两处P2在SOURCE/OFFLINE层关闭，未发现本限定范围内其他具体P1/P2阻断。初稿反例与9/24旧批次仍保留。

## 新fresh picture准备范围

Main 说明旧 C32 已evaluated，旧 C41虽健康空题但原QA缺少qid/aid导致保守snapshot拒绝；**没有为适配量具改写旧历史**。新 `--grade-chain --prepare-picture --verify-picture-state` 只允许不存在的专用 `neko-daily-speech-acceptance-*` store；原普通grade-current/provenance门禁不放宽。权限、混合mode、WAV文件、目录containment和任务端口核验先执行，随后 mkdir(exist_ok=False)和provenance.open('x')独占创建；已有目录不接管。

准备阶段复用原 `diagram-input-forward.png`，其他模式原Sky图选择不变；只建立该隔离课的中文/brief/no proactive偏好，提交图片时明确先确认主要关系、不出题。Native前仍实际核健康empty描述与只读snapshot相符；首题必须来自第一轮角色study_quiz，不能由准备步骤制造pending。新测试只执行到模拟端口哨兵，并确认此时fresh目录尚未创建；本审查没有真的准备库、生成WAV、启动宿主/Native或联网。

原旧队列适配提醒继续保留为诚实的实测边界：答题前已播放quiz，若实际player不对空旧队列再发cancel-stop，严格验收可以FAIL/PARTIAL；不能为了通过裁trace、重置binary计数或冒充physical stop。这个尚未实测的适配点不是本轮新确认缺陷，也没有被本审查擅自放宽。必要真实场可由Main按授权和现有guard有界执行，其终态/教学语义仍须独立读审。

最终SHA256与Main提供值逐一一致：

| 文件 | SHA256 |
|---|---|
| neko_daily_voice_probe.py | 16cc4bbc406516e49e2f8591ac0118108ee48b4a8de3742ab41fbb7463f07dbd |
| neko_native_grade_acceptance.py | 7608015d33cc67048991156e42697426e2e895592a6f0dd906f94b5187e77be1 |
| test_neko_native_grade_probe_plan.py | 7b1e0f27bf6f061f0942f3cd318d978342b17f2f5fcb6ed170bc5b2acf846b99 |
| test_neko_native_grade_acceptance.py | a27dba1c7dfd8ee23fbde76bd2147ed43649a40559887b2171368b54a9f05d2b |

最终结论是量具SOURCE/OFFLINE可进入Main的必要有界实测；不是连续学习、实际音频/物理输出或human已通过。无原raw/DB/ledger修改，未重复旧37–46场，也不把SDK45/46冒充Native证明。报告冻结。

## 实际场47：原失败与前置路由证据

Main 请求追踪时，本审查首次读到原 `daily-companion-20261015-continuous47.json` 已有3轮且finalized=True；未启动/停止/重试该场。原件独立 SHA256 **`4e83c318b0f06cff06abca24b59266db5cf23259205cc2db06ec9e82660d4824`**。Main 随后确认 exec42404 exit1、cleanup=[]、无listener；本审查没有进程操作。

底层只读观察：

- Native前 Store healthy empty、`chain_empty_pin._question_empty=True`。第一轮 provider 实际study_quiz 后保存有效 pending qid/aid，attempt_evaluated=False。第一轮 Native文字确为“从WEX出发指向哪个节点”，未产生正式 grade。
- 第二轮 ASR完整“我 的 答 案 是 WEX 指 向 NUD 。”，同pending题保持；provider发起study_answer，但没有本地grade markers。角色只确认“你的答案是WEX指向NUD，对吗”，QA/formal仍0，不能称已评分。
- 第三轮是要求解释箭头尖端且不要重新评分/出题的非答案追问；题/attempt仍原pending，QA/formal仍0。
- 三次本地phrase delivery都记录同connection1、positive完整written；**所有三轮NativePCM均0**。raw wire有3条provider response.audio.delta，不能把provider已到音频当Native收PCM/播放。实际chain只有healthy_empty_start、role_quiz、quiz_no_grade、followup_no_grade保持为True；same_connection_first_two_inputs因无accepted grade marker为False，answer_grade_flow和three_completed_native_turns为False。
- 原件无failure/timeout、cleanup_errors=[]，量具仍按验收失败退出。ledger原件为DS **724→746**、app **70→71**；tech无新支出，本审查未改账本。physical_output仍UNVERIFIED_NO_LOOPBACK，human=PENDING。

Main 指出更前置的路由失败，本审查也独立读到本场 timing_log：07:27:44/07:29:41 的 binding admission 为 trusted/current/free=True、**tts=True**、captured=False。受审 Core `_read_study_question_pin` 和 `_start_study_grade_claim` 都在use_tts=True时直接拒绝，所以DB健康empty不等于transport首次捕获到了healthyempty；实际槽可能先是readerNone的invalid槽。新provider study_answer guard会拒无localclaim的评分；被禁的外部TTS不能补Native播放。

Main 后续定位 fresh store 初次启动前 chars.json 尚不存在，`apply_free_voice_route` 提前返回，runtime生成默认mainland voice令use_tts=True；这是Main的source调查/拟修范围，本审查未独立重跑fresh启动，也没有把warm-store第二次修好当当前通过。**不能把本场未grade唯一归因于下面的clear问题**。

## 独立后续缺口：静音clear会毒化已正常退休的healthy-empty槽

另有与tts前置条件不同的具体SOURCE/OFFLINE冲突：原wire第二输入开始1792002507.589543后约0.056秒发送input_audio_buffer.clear（1792002507.645），处在WAV开头1秒全零前缀，早于实际speech。实际runtime `_transport.py:1904` 本地静音条件会调用clear_audio_buffer；`_audio.py:230–240` 在phrase不再保护时无条件把现有pin.invalid=True后发送clear。

本审查按Main授权，用AST提取**实际runtime `_audio.clear_audio_buffer`、`_transport._native_phrase_protects_input`**，接已有NativeGradeRoute的healthy-empty fixture和真实NativePhraseUplink.note_boundary，做定向离线复现。未import音频模块初始化、未provider；只有route-reset/resampler不相关callee为空seam，send使用原fixture Fake wire。

结果：

| 状态 | clear之前 | await实际clear之后及下一positive capture |
|---|---|---|
| healthy_empty | True | 仍同一槽 |
| invalid | False | **True** |
| provider waiting | None | None |
| phrase protect | False | — |
| empty rearm eligible | True | **False** |
| next speech新pin reader调用 | — | **0次** |

Fake wire确实写入input_audio_buffer.clear，model double调用0。因rearm要求not invalid，这个本来正常、可为下一新输入退休的空题槽会永久回到poison，现有empty positive测试直接从boundary跳到positive，没有包含前缀quiet帧触发实际clear这一callee。

这证明一个独立的生命周期缺口，**不证明47真正首槽就是healthyempty，也不排除其更前置tts=True已使capture失败**。修法必须区分“无待发PCM且此前已sealed/ASR/boundary明确完成的健康空题”与replay/overlap/authority loss等clear，不能一律免除clear毒化或在旧ASR重读新题；具体实现由Main另行独占。原47 FAIL不追认通过，也不为该假设立即付费重跑。

本轮原件/源码/定向fixture读审到此冻结。Main继续fresh路由修复和必要离线验证；全Goal依然推进，实际连续grade/NativePCM/播放尚未交付。
