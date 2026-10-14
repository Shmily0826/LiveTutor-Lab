# correction_of同题更正与SDK私有pin复审

2026-10-15。只读Main新增canonical study_answer_tool的correction_of、私有_expected_question及两项指定test/直接复用的SDK量具。原Goal active；未使用任何音频、mic/capture/loopback，没有应用/provider/HTTP服务或额度操作。唯一新增本报告，不改已冻结retry entry、avatar、tests、manifest或共享记录。

## 结论

本项未发现具体P1/P2阻断。correction_of只接受当前原qid/attempt；先经原四字段pin及course/session guard，再复用study_retry_question创建同题新attempt；重试后重新锁内核当前course/session与新attempt才进入原正式grade。新schema与真实SDK本地参数准备证明闭合，不代表Native自动路由/模型选择工具、真实模型评分或设备/真人已过。原真人零Study call口头判断缺陷仍需Main对应Native入口修复。

本次avatar SHA256 `d5e62ed86c1d06def5f46ed95accbb7cb7395786b7c4cecd1a4b1bd0aeb13d76`；correction test `22e5ae25af5793669cb31d105d0bb4ee89a0ad07cbada60823ed1691be7e37c0`；context pin test `605956c077926114a1063ace9a8971734b5eea08e1ad3ae81f233b5be7b703aa`。后续Main改动需另按新指纹，不外推。

## 路径与身份

canonical study_avatar_tools.py：

- `1088–1109`把可选correction_of加入public LLM schema，含仅两个必填非空字符串question_id/attempt_id且拒extra fields；描述要求显式修正此前wrong/partial才使用，普通answer仍省略。私有_expected_question不进该schema。
- `1117–1135`沿原snapshot、lock、完整四身份pin检查，拒绝旧课程/会话/题；不因这次是纠正而先放宽。origin course检查仍保留。
- `1139–1145`精确比较correction_of和当前held两个ID；不允许省一个、错一个或把最新别题当旧题。不接受纯“同题”模型自述代替ID。
- `1146`调用原显式retry，传当前course/session与原双ID；retry的已评wrong/partial、cache、reservation及原子两kv保存规则继承。普通未评/正确题不建立第二grade；retry Err不落入评分。
- `1147–1157`验retry回执为真实retried、新attempt非空且不同、原qid和previous attempt对应，然后锁内复核当前材料scope和held新双ID。换课/换会话或新题插入后不能采用那道新题；旧retry已持久化不通过失败恢复覆盖回去。
- `1160–1181`传原答案、新held IDs和原course/session context给既有grade，最后identity/material binding仍核当前。更新的是新attempt，不重放旧评分；已提交原history/QA不删除。图片-only换图按immutable held grading既有语义处理，不附无关新图像/OCR。

这段没有await期间state lock跨模型/网络，也没有新增长期偏好/新记忆表。_expected_question仍是当前调用开始的四身份；correction成功后新attempt由可信retry结果和live第二次检查得到，并非把外部pin偷偷改成任意最新题。真实ASR owner/connection/scope必须仍由Main Core路由和工具生命周期保证，不能拿这段课程/题目校验替代Native owner。

未知/保存失败/并发旧ID的retry返回不会调用grade；成功retry但其后scope变更时可能留下未评分的新attempt。这是显式控制已提交的正常结果，不是假成绩；caller应status回读后继续普通答该pending题，不能盲重放原correction_of。部分错误在真实SDK Ok/Err包裹中由_envelope转为ok=false+error文本，错误码不一定像fixture字典保留；本报告不把固定code断言扩大到所有真实Err序列化。

## 独立执行

```powershell
& benchmarks/raw/neko-product-host/.venv/Scripts/python.exe -X utf8 -B scripts/test_neko_native_answer_correction.py
& benchmarks/raw/neko-product-host/.venv/Scripts/python.exe -X utf8 -B scripts/test_neko_answer_context_pin.py
```

3 tests PASS（0.481秒）＋4 tests PASS（0.651秒），exit0。仅fresh临时SQLite/本地async model，无服务/用户库；第一次SDK模块准备有0.157秒async debug耗时提示，不是provider延迟或失败。

correction3：实际wrapper→retry entry→grade/finalizer/Store，原错答QA保留、同qid新attempt正确成绩形成第二QA；旧reference重放拒绝；错题ID/缺attempt/非retryable缓存不建新grade；同reference/pin并发只一次实际模型评分。其already_correct负例修改的是本地cache，另一个已冻结retry10里有实际correct grade后拒绝；不把此负例当真实模型正确判分。局部correct/wrong payload来自本地async model，只证明记录与路由逻辑。

pin前三项继承精确匹配/8种错误/锁前换题拒绝。新增第四项确实经真实NekoPluginBase LLM tool动态注册、collect_entries、SdkContext、prepare_entry_kwargs、实际callback函数与实际host result serialization片段；JSON roundtrip的私有_expected_question保留。错pin在评分前拒，真pin形成一次实际interaction/held evaluated，且public schema不含私有字段。

第四项的proof边界必须明确：

- 是实际Python callback/SDK/serializer本地执行，非启动SDK HTTP server、非remoteDispatch网络、非Core可信角色注入或provider FunctionCall。
- PluginContext只编译其真实dataclass字段/recipient方法，避开legacy provider/config初始化；plugin host Trigger和State是本地stub，permission availability/timeout由helper固定返回。因此不证明插件授权/manager身份/实际voice lease。
- 新SDK case验证普通study_answer的pin序列化，不验证correction_of经过真实provider schema后被选择，也未直接注册/调用public study_retry_question SDK entry。correction3运行真实业务方法，但通过existing fixture的Ok/Err形状及direct call。
- retry后的课程/题替换由当前源码双检查及既有entry guards保护；新correction3没有单独复现这段await间切换。本次未见源码缺口，但不能称这一个新race已有独立设备测试。

## Main集成与剩余

指定增量SOURCE/OFFLINE/LOCAL SDK PARAMETERS已通过，当前无需扩大旧全套或Paid测试。Main后续Native入口应固定真实original owner及四pin、在明确纠正时给correction_of原ID、遇retry/grade失败诚实返回未评分。真实模型必须选择正确入口、使用新attempt并回读真实QA/evaluation才关闭口头判错未落库问题；本报告不替代该验收，也不解除音频/mic禁止。

本文件完成后冻结。其他源码、历史、账本、应用进程和设备均未修改。
