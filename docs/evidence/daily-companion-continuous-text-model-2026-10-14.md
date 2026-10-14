# 按课原题接续：真实角色文字与SQLite限定验收

阶段十四，完整contract继续约束active Goal。**原待答题跨课返回及宿主重启接续：限定PASS_REAL_SDK_ROLE_TEXT_SQLITE；默认语言PARTIAL。** 没有Native/声音/捕获/回环/真人证明。

## 原失败与有依据的接续

continuous32从新建neko-daily-continuous-text-20261014-32开始，原用户daily/旧C31库未打开、复制或恢复。复用既有forward/reverse PNG，不新制材料。SDK提交A图，实际文字角色status+quiz产生恰一question_generate并等待；随后SDK切B并提交B图，B无A当前题。

量具错误地从state读取大图hash，得到空bytes hash而断言失败；真实图片保存在按课submitted_image kv/data URI。32原FAIL_OR_PARTIAL、空hash和terminal不改写，不能据它宣称产品丢图或返课/重启已过。修量具后只读正确kv解data URI，reverse原PNG SHA逐字匹配。

33通过受限--resume-from，先核32 finalized的具体中断位置、same store/provenance/source、3旧rows/0QA、B正确图、A原checkpoint。只继续未执行的返A和重启，不重复出题或提交图片，不恢复/删除旧数据库。32与33是一次准备后的两段有证据接续，不声称一次未中断长语音会话。

## 实际工具与回答

返课角色实际study_session(action=set_course,requested_course=A)并再status，receipt含原public question及pending；宿主停止后同store重新启动，新的Study session，角色再次实际status读到原题。两次完整回复都逐字复述原题并等待学习者，没有透露私有答案、新题或评分。结论依据实际工具返回前public JSONL、文字WS终态、SQLite和Main独立回复审阅，不是靠旧聊天“记得”。

原question_id/attempt_id/public题payload保持相同，新Study session_id变化合法。旧三条interactions全部hash保持，恰一个question_generate；answer_evaluate、summarize_session和QA均零。A与B原PNG仍按课保存，返回及重启当前A为forward。公共工具receipt无answer/reference/rubric/solution/cache/reservation内部字段；私有reference依旧在本地原题，角色没有输出它。

原题文本SHA256为3a80c6913645484e6dafb153f75edeaf05c6378f365ec9990c346c416826ae4b，public payload SHA256为f682c506abc50d98a998658a1a0f2423de1dee413fb7c32c747566cde1eeb54d。raw32/33、私有session audit及final review仅本地，不发布学习DB/完整对话/运行配置。

## 真实限制、源码和部署

返课回复前出现一句“I'll check the session state first.”，随后中文复述；重启回复全中文。故默认语言/简短风格不称全面通过。Main随后给现有managed tutor guidance补“工具静默调用、无计划前缀、答复随课程语言”，保留既有Study Companion mode所有权前缀。这项修法当前只有源码/prefix检查；不为一句前缀重复该付费场，下一必要集成或集中真人体验检查效果。

按课checkpoint/显式fresh退役、公开题投影与grading owner/ABA修复详见course-progress及review。Root course8/answer13/language4/task audit2通过；真人与设备、突然掉电时跨kv原子性、所有课并发和graded返课真实模型仍未验。此场未评分，不能把answer guard离线负例冒称真实grading并发通过。

两段共DeepSeek595→610/2000（32+9、33+6），Lanlan.app58/null不变，tech0/0，同bargein-autocheck-20261012不重置。计数不是金额。source env NEKO_TASK_SILENT=1，无voice/Native/meter/麦克风/虚拟捕获/回环/音量操作。32/33均已finalized，三个自有launcher均终止，48911/48916无listener。没有关闭其他用户进程。

此阶段产品部署为该独立task store当前6个payload实际SHA与canonical相等（avatar仅加入已知观察instrumentation）；原daily未启动刷新，不能说已在用户日常窗口实测。reviewed codex发布记录另写，Goal不因本阶段结束而complete。

发布候选当前在56c2a07基线上，18项必要文件；candidate实际course8/answer13/language4/task audit2均通过。一个未改动static/main.js检出为Git CRLF转换差异，归一化后与原HEAD及Root逐字相同；仅恢复候选canonical LF bytes以核manifest，没有新增语义修改或扩大staged范围。不重复设备、旧C31或已通过底层批次。

最后source-only评分边界在本模型场之后：reserve移到ensure active session后、context同锁核身份再创建，空会话自动续题不会清掉本次owner。Root answer新增该场后14通过，其他已过测试无变化；本场没有grade，不将此改动冒称MODEL并发/评分验收。候选最终answer结果另记录实测，source manifest hash同步。

候选最终answer14实际通过，精确窄审移动顺序未见新阻断；course8/language4/audit2既有候选证据继续适用。只复跑有新评分改动的这14项，其余未重复。最终发布按18项exact allowlist及source/index/hash/manifest/AST核验，raw/prompt/DB/userdata排除。
