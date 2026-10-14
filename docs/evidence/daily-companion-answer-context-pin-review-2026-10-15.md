# 正式评分expected identity屏障与Native路由边界

2026-10-15。Goal按用户明确指令继续active。范围为canonical study_answer_tool新私有_expected_question、新test_neko_answer_context_pin及原answer-material suite；进一步只读必要Native/Core协议方法。仅新增本报告，没有源码/shared records/manifest/账本修改，没有应用、provider、SDK服务、设备、mic/capture/loopback。原真人口头评分未落库缺陷仍未关闭。

## 身份屏障审查：未见具体阻断

读到canonical avatar SHA256 `11b684469b1fe7f9f8f2753042debd50fe86a26eb0536db48756f19e9deb1344`；新test SHA256 `b0d54a94ed2ce90c6c2f55ef307a3a1800d83ea8b649f4ac425953ad517e7e56`。这些只是本次SOURCE快照，未部署/模型证明。

study_avatar_tools.py `1102`增加可选私有_expected_question，public llm_tool schema `1095–1098`仍只有answer。新字段不会引导角色编造内部ID，也没有替换正常legacy缺参调用。

`1111–1124`在现有state lock内读取held，并按四字段question_id、attempt_id、course_id和**当前**session_id精确比较；key集合必须相同，每个值必须非空str，extra/missing/非dict/错误值均拒绝。未将原question的source session冒充当前session，适用于跨课返回/重启后的已恢复held题。model/正式评分入口发生在检查之后，没有锁跨模型IO。

匹配后仍给原study_evaluate_answer传真实held双ID与原_material_context（1130–1135）；不把_expected_question发模型或存为一套新记忆。entry原锁内context检查、QUESTION_MISMATCH、attempt reservation/cache、model后/finalizer/return校验继承；wrapper最后仍核题目identity再绑定输出。因此snapshot后题替换不能借新held改写原ASR答案归属。已提交原题历史可以保留，晚反馈不得更新/返回给新题；这与原14项guard范围一致，不删历史作失败恢复。

原answer按原字符串传递，不为了匹配中文intent删空格、重命名标识符或提炼成一个方向词；本轮长度/原因指令也保留在原answer。这个保留检查不等于评分模型实际遵守两句要求。

**证明措辞需收窄：**私有pin检查位于_snapshot→_ensure_active_study_session之后。若原session空/过期，无效pin仍可能触发正常session/state lifecycle SQL，再拒绝正式评分。因此可证的是“拒绝后不调用评分模型、不reserve/提交这次评分、不采纳新题”；不能笼统声明任何初始状态都零DB写。新3项在已active session中断言model/history/held不变，没有覆盖DB total_changes。此为范围说明，未发现错误评分阻断；合法生命周期写入不是伪造学习成绩。

未来宿主fallback应保留独立的pin副本，不把共享status dict在await期间原地重写为最新题；当前接口验证的是进入锁时所给对象，不能证明外部调用者从不变更该对象。原native模型工具不要求pin的兼容边界有意保留，所以这项不是完整Native答题必调保障。

## 本Agent独立离线结果

```powershell
& benchmarks/raw/neko-product-host/.venv/Scripts/python.exe -X utf8 -B scripts/test_neko_answer_context_pin.py
& benchmarks/raw/neko-product-host/.venv/Scripts/python.exe -X utf8 -B scripts/test_neko_answer_material_guard.py
```

新3 tests PASS（0.332秒）；原14 tests PASS（1.334秒），均exit0。两个进程仅临时SQLite、实际wrapper/entry/context/finalizer/Store、本地async model，互不共享测试库；没有原daily DB操作和外部调用。

新3项：精确pin评分且原答案完整到模型、原题ID/attempt进入实际interaction、重复调用只一次模型/记录；8种错误/不完整pin拒绝、不调用模型、不改变held和评分history；snapshot后进入wrapper锁前替题拒绝、不采纳新attempt。第三项是fixture在snapshot返回前替换题，不是完整原生ASR并发/真实锁拥塞量具，不把方法名外推成设备race证明。

原14项继续覆盖immutable held题不借新图/OCR、图片-only更换不误退题、错ID不reserve、空session/failure、course/model/commit之后变化、晚新题反馈、staging/final cleanup、旧task不释放新session reservation。模型、event push、图片验证及UI缓存有fixture double；没有SDK serialized private参数或Native工具协议验收。独立测试证明SOURCE/OFFLINE，不证明真人评分缺陷已修。

## Native强制工具协议：现有证据不能直接采用

实际host `main_logic/omni_realtime_client/_transport.py:779–799`的free session只提交tools、输入/输出格式、语言和VAD配置；`_tools.py:1118–1123`的free更新也仅提交tools。当前源码没有强制命名tool_choice的实现或代理接受回执证明。GPT/Grok的auto字段不能作为free支持同字段或强制选择的证据。不通过猜provider参数或增加CONNECT来绕过这个未知。

`_tools.py:1277–1294`明确free的function_call_output需要服务器实际发出的call_id，`1308–1321`把结果绑定这个ID。宿主若主动执行study_answer但本轮provider没有FunctionCall，不能合成call_id后复用_raw tool batch发送；“本地registry允许任意call_id”不意味着远端存在那次call。原真人缺陷正是没有观察到Study ToolCall，不能仅转换已有study_explain来覆盖。

原speech gate/late-ASR owner方法可以保护**已有**工具，不能把任意ASR文字自动当工具事件。MANUAL、VAD、PCM入口本轮无须改动；不以新身份屏障外推自然停顿已解决。

## 有限首版宿主fallback：最小安全路线

以下为已有接口及必要缺口，未实施，不能称Native修复PASS。

1. 在真实accepted ASR事件上，仅匹配明确回答当前held题并要求判断的意图。匹配副本处理本场真实中文字间空白，原answer完整保留。普通“图片对不对”、解释旧答案/引用他人答案或题意不明不得自动评分。使用当前输入捕获的connection/provider session/scope/角色，不借display websocket或旧tool owner。
2. 通过现有可信Study状态入口读取当前course/session/public qid/attempt及pending，再固定独立四字段pin；已有study_session(action='status')能返回这些，不读隐藏答案/rubric。getter不可用/no pending时诚实拒绝或澄清。随后透过现有Core _on_tool_call→trusted registry执行一次study_answer，传私有pin和原answer。Core真实invoking_session与plugin metadata校验、角色_ctx覆盖必须保留；不能由模型传来的_ctx或_expected_question自述取得宿主权限。
3. 独立getter和执行之间每个await后复核原输入owner；pin保证“当前变新题”不能采纳新题，但不替代connection/scope退役检查。注册在已有owned-task/cancel机制，不能开另一个长期队列。原attempt reservation/cache作为重复模型调用和fallback的正式成绩去重基础；同轮提前自由Native verdict需要先抑制，不能一边说wrong一边后台评分后给相反结果。
4. 主动评分结果先以真实status/公开text证明成绩已保存；不能为让角色读结果伪造function_call_output。若同场仍需Native发声，应使用合法plain-text注入＋response.create，内容只含真实grade的公开feedback/verdict及转述约束，不能带隐藏参考答案/私有binding。
5. 现有 `_responses.py:1419–1469`的inject_text_and_request_response确实有plain input_text、response.create、返回arbiter ticket及精确completion/rejection回调，可复用其传输机制。但WS分支`1767–1775`为proactive enqueue，没有原grading tool owner的event_sender；仅caller进入时检查会让晚grade排队后跑到真新输入。**不可原样调用这条proactive helper当安全fallback。** 需最小给最终item/create发送各附原owner guard，并在新输入/连接替换/任务取消时取消其精确ticket，提交前再核四字段状态。可复用原tool_result enqueue的event_sender模式（_tools1326–1355），传入的是合法文本事件而非伪工具结果；不新增队列/DB。
6. 原 `cancel_response(wait=False,send_guard=...)`（_responses2944–2971）支持发送前guard；wait=True分支直接cancel_current，不能无条件用于此旧ASR任务。必须取消本轮已捕获owner对应自由输出，不能等待后取消下一轮。provider可能在ASR完成前已播放自由回答：首版须明确这个残余时序，不能倒称用户没听过旧判断。不得重放PCM、伪onset或无限reconnect。

普通prime_context不适合替代上述owner relay：它可能创建新user turn/触发响应，且Gemini分支有不同skip语义；不能用静默context更新名义抢占本轮。所有最终发送须在当前材料/题目owner下发生，SQL已提交后scope变更应保留原记录并放弃晚播，而不是回滚历史。

## 下一步最有信息量验证

Main可以先仅离线实际Core/registry与新pin构建“明确答题ASR→真实状态读→同一原题评分→status一致”的一次路径，覆盖中文字间空格、no pending、status后换题、真新输入/连接替换、模型同轮迟到调用和provider未发call_id。发送量具必须断言只有合法plain message，不出现虚构function_call_output；同owner队列后变更需零晚send。已有身份和14项guard不用无依据反复重跑。

此后Main独占安排必要受控输入/真实provider证明，独立核工具Trigger、SQLite原attempt、回读一致和角色公开反馈；普通打断继承保护。真人未重新授权前不要求朗读、不初始化mic/capture/loopback。至此本项身份屏障SOURCE/OFFLINE闭合；Native必调/无提前口头评分/真实设备播放仍未实现或验收。本报告完成后冻结。
