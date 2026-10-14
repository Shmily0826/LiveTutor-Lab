# 阶段33：日常正式评分准入只读调查

接续当前 contract/plan/status/blockers（阶段32发布 f42386db，完整 A–F Goal active）。本轮只读指定 Native grade/intent/route tests、daily start/host、实际两个 Daily cmd 引用，补读既有 probe 的开关赋值及原场40；只写本报告。没有生产/测试/manifest/共享记录修改，没有应用、服务、provider、音频设备、mic/capture/loopback、用户 DB、Sky 或账本操作。下列临时 SQLite 检查均为已有离线 fixture，模型与外层 transport 是 double，不是 Native/provider实测。

## 为什么日常入口未启用本地正式评分链

- `Start-Daily-Tutor.cmd` 调用 `neko_tutor_start.py --text-only --study-ui --learning-surface`，稳定 store 为 `neko-daily-companion`。默认文字入口不会进入首语音帧/ASR pin 机制；不能因本地 AUTO_GRADE 关闭就说 Study UI/SDK 无法评分。
- `Start-Daily-Tutor-Voice.cmd` 传 `--voice --voice-host www.lanlan.app --voice-connects unlimited`，start 的 host_command 固定 `--source`，host_options 传 voice/free、预算、Study vision，**没有 AUTO_GRADE CLI/赋值**，也没有给 launcher 新的 output-only 参数。它当前仍含 mic 操作引导，不能在本任务禁止 mic/capture 的权限下直接用来验新语音场。
- start.launch_env 与 host.env 均复制父环境，未显式清除 AUTO_GRADE，因此手动父环境设 `NEKO_STUDY_AUTO_GRADE=1` 可以继承；准确说是“日常入口没有受控启用”，不是“只有 probe 才可能启用”。唯一仓库内明确设此变量的现有运行入口是 voice_probe 的 grade_current 分支；同处 phrase/speech gate 仍独立 opt-in。
- grade patch 自身标注 opt-in。只有 AUTO_GRADE=1 才给实际 session 安装 get_study_question_pin / get_study_input_authority / ASR 路由回调，并自动允许 phrase input；不是全局替换普通 callback。Core pin 还要求当前 active session、无 takeover、非 TTS、free proxy。host role guidance 已让模型自行调用 study_quiz/study_answer/study_summary；本地 AUTO_GRADE 关闭并不禁止模型自行调这些工具，而是缺少确定性的本地答案 claim/正式成绩转述链。

## 已有身份链应保留

首个实际 positive DSP frame 在首 await 前捕获原题只读四身份 pin、evaluated bool、Core activation/socket、provider ws、connection/token/scope；不是从 ASR 后的新题反向补 pin。实际协议 speech_started 或 no-VAD completed 只有一次明确 scope +1 许可。claim 必须保留原 owner/current frames 和物理连接，Core 之后通过 study_session.status 再核同四字段与 pending/evaluated，调用已有 study_answer；correction 使用原 attempt 指定重试且返回新 attempt。

正式结果经现有一次 controlled reconnect / arbiter relay，旧 token cancel、完整新 owner 校验、禁止 PCM replay、工具 join/去重。材料换课/新 question 或新输入不能被迟到旧 reply 覆盖。不能用手动提升 owner、观察序号冒充 provider utterance ID、吞下任意第二 ASR、重复旧 PCM 来拓宽准入。现有纯请求 tail 只有 first-origin sealed local delivery 的可信归属证明、同 driver/delivery/epoch/frames/四身份、3秒/一次、没有新 pin，才保留原 scope；这不宣称同 provider utterance。

## 启用前的三个具体缺口

### P2：正常无题轮和有害 poison 混为连接终身无效

`_capture_study_grade_pin` 目前把 pin 缺失或 authority 缺失都设 invalid；replay 只留下 `{connection, invalid}`；超过1.2秒的输入歧义以及重复/foreign scope 也会毒化。`_take_study_grade_asr` 只清非 invalid 槽，注释明确 poison 保留到物理连接替换。因此：先语音“给我一题”时尚无 pending → reader None → invalid；工具随后正常生成题 → 同连接下一次新回答仍无法取得 pin。

独立使用现有 `NativeGradeRoute.asyncSetUp` 的实际 helpers/Core/tempSQLite 复现：首次 reader None 后 `pin=None, saved_invalid=True`；恢复原 reader 可读真实当前题，推进实际 fixture scope/frame 后第二次 positive capture，仍 `pin=None, invalid=True, connection=1`。这证明 helper 状态阻断，不代表已经跑过实际模型“给题→回答”。已有测试 unknown-pin 能诚实无评分，但没有覆盖后来正常恢复。

最小处理方向应是明确 reason 和旧输入退休证据，而不是统一清 poison：

1. 区分正常尚无可评分题和 replay、authority loss、overlap、foreign/repeated scope。`read_question_pin()==None` 本身也可能是 DB/路径/字段不合法，**不能单独当“正常无题”证明**。
2. 复用实际本地 sealed delivery / first waiting / driver+delivery identity+epoch+input_sequence、当前 Core authority。只有已明确退休的原无题输入，随后真实新 positive PCM 才能为新输入捕获新题；不能在旧 ASR 上重读最新 DB、更不能以 response.done 单独授权。
3. 捕获 hook 发生在 phrase collector accept 前，若依赖“新 collector 段”，须按这个真实调用顺序接入。replay/不明 authority/歧义仍 failclosed，不能借 waiting=None 重新获得 first-origin 资格。

若本轮尚无法证明这条退休边界，日常启用必须明确限制为“已有可信 pending 后开始的新 Native 会话”，并把连续要题后同连接答题作为下一必须补的项目，不能据此缩减整个 Goal。

### P2：撤回/未确定/不要提交未优先拒绝

实际纯 helper（`allow_declared_answer=True`）结果：

| 原话 | 当前结果 |
|---|---|
| 我的答案是B。 / 我选B。 / 当前题，我选B。 | None |
| My answer is B. / I choose B. | None |
| My answer to the current question is B. | None |
| 当前题，我的答案是B。 | answer |
| My answer to the current question is B. Please grade it. | answer |
| 当前题，我的答案是B。撤回刚才的答案。 | **answer** |
| 当前题，我的答案是B，我还没确定。 | **answer** |
| 当前题，我的答案是B，不要提交。 | **answer** |
| 当前题，我选B，请评分。撤回刚才的答案。 | **answer** |
| My answer to the current question is B. Please grade it. Do not submit it. | **answer** |
| 为什么刚才那个答案错了？ / 当前题，我的答案是B，不要评分。 | None |

最小先加中英 withdraw/uncertain/no-submit 的拒绝优先级，再在**已可信绑定且仍 pending**的同一 pin 下支持有限完整首人称“我的答案是…”/“我选…”/“My answer is…”/“I choose…”声明。普通 `answer_intent` 默认仍严格，不给 missing/evaluated pin 这一宽声明资格，原 transcript 完整交正式 entry，不截答案或模型猜 target。

测试应包含中英追问、否定/撤回、引用别人/引用代码、假设、改课程/要新题、未知尾句和语法提问，不能只扩大几个 positive regex。已提交原 grade 不删除；下一真实输入能抑制旧转述不等于可抹去已落 SQL 的正式成绩。现有 `test_new_speech_during_grade_keeps_commit_but_suppresses_late_relay` 正是此边界，撤回后状态必须诚实。

### P2：拒绝本地 claim 不等于阻止 provider 误调用正式评分

当前 `_on_tool_call` 仅在已有 current claim/controlled relay 时 join 同一 study_answer 或拒不相关教学调用。无 claim 时仍放行 provider 的 study_answer。实际离线 Core→SDK→entry→tempSQLite 反例：在 AUTO_GRADE=1、held pending 有效、无 local claim 时，注入 provider ToolCall `study_answer(answer='为什么这个答案错了？')`，得到 `is_error=False`，model double 被调用1次，新增1 QA。

这不证明实际模型必然如此调用；它证明当前“追问 None → 不误 grade”测试仅检查 `_start_study_grade_claim`，没有覆盖 provider tool branch，因而不能作日常零误评分证明。建议仅在 AUTO_GRADE 受控 Native 语音路由中，要求 provider study_answer join 对应的可信 current input claim/owner；没有明确答案意图的这轮最多 status/解释或要求明确回答，不提交正式 grade。已有 UI/SDK direct entry 不应被这个 Native 约束全局禁掉，工具 dedup/relay 继续复用原链。

## 场40证明范围

本轮只读原 `daily-companion-20261015-native-short40.json`，SHA **`356f05bd564a629a9b0c96ade307f6629d1afe7a8e1c4a82acaef380875c84ab`**。它明确先 grade_quiz_preparation，再新 Native 固定WAV，opt_in=True/phrase=True；既有20 grade checks 和 accepted→complete→relay 的 connection1→2 是该已备题窄链。原 ASR 是中文带空格“当前题，我的答案是WEX指向NUD”，纯尾请求被受限消费。

该证据没有覆盖无题起步/临时问答后生成题/同连接下一题/自然短选择声明/English 自然答案。其 Native PCM 与播放调度不是物理听见，原件仍 physical_output=UNVERIFIED_NO_LOOPBACK、human=PENDING；反馈把相邻边说“反了”的原语义 PARTIAL 继续保留。SDK45/46 只补同题身份和直接文字 English，不能移作这些 Native 缺口已通过。

## 最小下一交付顺序

1. 保持 daily 默认安全文字入口及 AUTO_GRADE OFF；先修正常无题轮的可信退休/新输入 pin，并补“无题→真实工具生成→同连接答题→追问→纠正/下一题”实际离线链。replay/authority/旧scope/newPCM 替换负例仍必须拒绝。
2. 同阶段做拒绝优先级和可信 pending 的有限自然声明；补 provider study_answer bypass 负例。修改复用现有 Core claim、Store题、工具owner和SDK，不增加第二套 routing/记忆/队列。
3. 再添加明确受控启动开关，贯穿 start→host env，并报告支持范围；text-only 不把 AUTO 当作音频授权。当前禁 mic/capture，任何必要真实验证仍由 Main 用已有 fixed WAV/output-only与guard、单场预算/超时/owned cleanup，不能为了开日常按钮放宽权限。
4. 最小新模型场应真正从无 pending 开始请求题，再答一次自然短句，并核唯一正式 grade/旧行保持/新 Native token 排程/拒绝追问误 grade；不要再用预备题加单答案冒充整段连续学习。尚未实现的 English/纠正/物理可听分开登记，自动验证成熟后再集中human。

本轮没有重跑既有28 route全套或无关SDK/语言/设备基线；只执行针对上述两 helper/Core反例和纯意图矩阵的本地检查，所有临时夹具已关闭。当前没有可据此直接盲启日常 AUTO_GRADE 的证据；三个具体局部问题已发 Main，自主工作可继续，非全局阻塞或 Goal 完成。

## 调查源指纹

| 文件 | SHA256 |
|---|---|
| neko_native_grade_patch.py | 54d9b7e1b8cf49afeae01b4231288751261e1c37dcd48c3236e69d06ff1f12e4 |
| neko_study_answer_intent.py | 9d1fa1135c49cf4185683fa4efbe850e76ab2678f00b0e5434752e70410f4a71 |
| test_neko_native_grade_route.py | 4a192b0551a44ba99b3fe727a7e123788940959cd80241740b75f2069c949dcb |
| neko_tutor_start.py | fe03fe4541e61f5270b2d34e8b67adbf06f0f00a60d705a7de0a77a8fc671cb4 |
| neko_desktop_tutor_host.py | 614a60710b0076f37b047d1135e48b529339459b574bbbc93f8d69e9fe78bc87 |
| Start-Daily-Tutor.cmd | e6029f0da609cb50be20c02f4a6c03f344027bc4490e83806f7bc478cd422bd0 |
| Start-Daily-Tutor-Voice.cmd | 6c45c5c3d561fb9036e4bb9b633d569adc65078623b44cc26da34b4eb4f78a4b |

指纹记录 Main 实施前/调查期间读到的该版本；后续实现由 Main 独占，不把调查结论写成修复已交付。报告冻结。

## 阶段33四脚本实现复审（SOURCE/OFFLINE）

后续按 Main 授权只读复审两个 helper/patch 和对应两 tests；不改实现。独立实际运行：

```powershell
.\benchmarks\raw\neko-product-host\.venv\Scripts\python.exe -X utf8 -B scripts/test_neko_native_grade_route.py
.\benchmarks\raw\neko-product-host\.venv\Scripts\python.exe -X utf8 -B scripts/test_neko_study_answer_intent.py
```

结果 **Native route 36/36 PASS（6.195秒）**；intent **19项中18 PASS、1 Windows symlink 权限1314跳过（0.361秒）**。没有把 skip 算作平台 symlink 路径实际通过。路由夹具的 canonical patcher 在临时文件回放实际旧 runtime 源，随后 AST 提取真实 Core/transport 方法，接实际 SDK/临时SQLite/arbiter；模型、outer transport/socket、某些 route seams 是 double。empty 场景把原 fixture question 保存后重新安装，**不是实际 provider 生成新题的整链**，手工设置 last_delivery 也不是实际音频提交证明。

### 健康空题的退休与新输入捕获

新 `read_question_pin(include_empty=True)` 默认API不变，仅完整 course/session、确证 current_question 为真实空 object 时返回私有 `_question_empty` 描述；缺失、None、部分旧题、字符串 `'{}'`、DB错误都不当健康空题。最终查询使用 SQL CASE/json_type + NOT EXISTS(json_each) 投影空对象布尔，**不 SELECT 完整 current_question JSON/private答案**；既有 readonly/timeout0/path/file identity 保护保留。

空题槽不再直接 invalid，但 question 仍 None，不能拿它评分。只有实际协议 scoped 一次的原 ASR 首次取得了完整 sealed local delivery，且同 driver/delivery object/epoch、provider/ws/token/scope/Core authority，随后 provider boundary 令 waiting=None，下一 speech literal True、非 replay 前置捕获才可重新读新题。旧 replay/overlap/foreign scope/失败读取仍保留 poison。新槽带 previous_empty_phrase；其 ASR 又要求不同的真实 sealed delivery、同 driver/epoch和递增 input_sequence，单独 positive frame或旧/early ASR不能取得新题。

实际受审 runtime `_transport.stream_audio:1680` 的 pin capture 位于 phrase-driver/admission之前，也在 `_note_voice_handoff_input_open:1728` 递增之前。因此新测试先 capture 再 increment 的次序与该路径相符，本审查没有把“先增序号”假设当作缺陷。这里是 local collector归属约束，不能升级成 provider utterance ID；真实连续场仍待 Main。

### Provider 误评分拦截范围

新 `_on_tool_call` guard 在 AUTOON、当前 free-proxy invoking_session 的 study_answer 上要求 matching local claim/input owner，已有 current claim/controlled relay join/去重先执行。独立负例已覆盖 provider 把追问/no-submit包装成 study_answer，正式 model/QA均不增加；原 claim/relay positive 保留。

准确保留范围是**直接 Study 答题 entry/SDK**。这不等于 Avatar 文本或网页UI E2E：active Native session 中 typed answer 无本地 ASR claim，同样会拒 provider grade。尚需真正 text ingress authority 或明确让学习者使用 Study 答题入口；不能把 `self.h.study_answer_tool` 单方法测试说成页面自然评分已通过。默认 OFF 仍保留，没有因本轮源码就盲启日常。

### 新声明与剩余P2

自然中文“我的答案是…/我选B”和 English “My answer is…/I choose B”只在 allow_declared_answer **literal True** 时开启，Core资格来自可信 pending pin；默认False/数字1不扩大，裸B/泛泛 I think 不自动评分。原 transcript 不截断，之前列出的 withdraw/uncertain/no-submit 确切反例已获优先拒绝覆盖。

但独立补测发现仍有明确非提交否定被判 answer，已发 Main：

- “我的答案是B，但这不是我的最终答案。”
- “我的答案是B，只是举个例子，不要当成作答。”
- “我选B，这只是示例，不是我的答案。”
- “My answer is B, but this is not my final answer.”
- “I choose B as an example, not my answer.”
- “My answer is B; I have not submitted it yet.”

上述均在 allow_declared_answer=True 下返回 answer。最小需要明确的“非本人/非最终答案、示例非作答、尚未提交”拒绝优先级，保留positive覆盖，不以无限扩普通口语范围来修。该剩余P2待 Main 修复后追加关闭；当前36/18通过不覆盖它。

### 普通日常输入的speech bool：只读链路结论

按 Main 追加授权，只读精确 runtime callee，未开 mic：

| 位置 | 当前源码事实 |
|---|---|
| static/app/app-audio-capture.js:1965–1987 | 普通录音在isRecording且socket OPEN时发NEKO magic+sample rate+PCM16 binary；没有前端speech_active字段。 |
| main_routers/websocket_router.py:102及129–136、1348 | binary decode生成audio stream_data；经原voice lease/route守卫后进入stream_mgr.stream_data。 |
| main_logic/core/streaming.py:237–243 | audio进入既有_enqueue_audio_stream_data，未信任前端VAD布尔。 |
| main_logic/core/asr_runtime.py:3599、3861、3947附近 | worker调用_process_microphone_stream_data；实际pipeline.process得到processed_frame及概率/evidence，再经route/activation队列到unfiltered。 |
| 同asr_runtime.py:4706–4732、4791、4805/4814 | Omni路线调用_voice_session_activation_has_speech：有权威概率则>=0.5，否则RMS fallback；所有return为bool，随后显式传speech_active。 |

因此**不能仅因前端没有bool就断言当前Core普通Omni一定走legacy None**。该已追到的SOURCE路径会计算并传bool，但受实际route/activation/noise contract等守卫，真实日常设备场未执行。仍有 legacy/direct client调用在 speech_active=None 时早退pin capture，后续DSP speech fallback用replay=True毒化；本次没有删除或放宽此 failclosed，也不把40fixed输入的明确bool外推真人麦克风可用。其他入口未全面扫描；下一步依据真实调用边界定向验证，而不是假设所有daily都兼容或都不兼容。

## 最终声明拒绝修复与收口

Main 最小补上明确“非我的/非最终答案、尚未提交、不要当成作答、只是例子”及对应 English not my final answer / have not submitted / as an example 的前置拒绝。独立读核新增 `test_explicit_non_submission_and_non_final_declarations_are_refused`，覆盖上述六条加“尚未提交”共七个明确反例，在默认和 trusted pending 两模式均拒绝；原 positive 未扩大。

独立重跑 intent 全组，**20项中19 PASS、1 Windows symlink权限1314跳过，0.363秒**。Native route/migration 36项已独立通过，最后只改纯 classifier 的 REFUSE 与对应单测，未改 Core/transport 方法，不重复未改整组。先前 remaining P2 在 SOURCE/OFFLINE 层关闭；本轮三类发现均已有对应本地保护/测试，没有其他本审查范围内具体 P1/P2 阻断。

迁移范围也已核：`DAILY_UPGRADES` 叠加既有 UPGRADES→TRACE→TAIL，回放字符串会依次带上后一层变化；tests 的 `replay()` 用真实 canonical patcher 对临时旧 runtime 文件 apply、确认statepatched、再AST提方法，未手工重复旧升级 bundle。36项含既有 exact-known-helper 去重/unknown拒绝/幂等三个迁移检查，**不等于本轮已独立回放全部30个部署文件**；Main 后续完整oldSHA部署/manifest gate另管，本审查没写实际 runtime。

最终读到四文件 SHA256：

| 文件 | SHA256 |
|---|---|
| neko_native_grade_patch.py | d9b511352910333e29d71f5010cc53c65dcd4ac6449585e58f3047e38e475ada |
| neko_study_answer_intent.py | 829c2da3cc181b7f99505e09d5b600a346d87fabe2d594ff83639f953a01c7a2 |
| test_neko_native_grade_route.py | 6402ff3dd00455fb4d50c1d95f7bcaae14067d64b1ff20b97e229199c5e5b559 |
| test_neko_study_answer_intent.py | 2e2b8f06f187e06c029c152a05f261a73277eb19b12101deb10873fc36908faf |

交付边界不变：健康空题恢复和自然答案准入仅 SOURCE/OFFLINE，不是模型出题→语音答案的实际连续链；新本地 delivery 不冒 provider utterance ID。当前Core普通Omni源码会计算bool，不代表所有legacy/direct输入都支持。直接Study entry/SDK保留不等于Avatar text/UI自然评分；free Native active typed/provider无claim仍会拒绝，待明确text ingress归属或Study入口。daily默认/权限未由本审查启用，真实模型、Native/设备、人体验待Main有界推进；SDK45/46不能移作新语音证明。报告冻结。
