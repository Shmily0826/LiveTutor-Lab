# 阶段八真实后端检查：源码纠正通过，总结接续失败

现有 Goal active，完整contract与四接续边界保持。quality18 exec46812终态：实际source host/SDK/Study/SQLite，两次后端调用，不开Native窗口/音频/麦克风。结构checks仅证明调用完成、同课程、原interactions/QA未改，不代表教学质量通过。

## 已确认结果

`study_summarize_session`要求两句话复盘上一轮题、错答、正确方向和下一步。实际模型说本次缺可核对旧题/错答，要求学习者补全；旧图题和wrong/10记录仍真实保存在同课程。这个接续检查 **FAIL**。它没有假称本次已完成解释，但“诚实不知道”不能替代取用已经存在的学习记录。

源码原因已核：每次host初始化新session；summary入口只取新session历史。`_build_learning_context`已经从既有Store按course过滤取`previous_course_history`最多8条，但`_summarize_context`没有转发这些证据。主线正在复用这份已查询的历史，独立标为前一会话；不把旧行填入当前session，不改SQL/数据库/历史，不增加记忆系统。

`study_explain_text`使用刚经CodeGraph读取的Sky Scout真实weather_service.dart第14–19行，询问假设互换latitude/longitude取值会否缺lat/lon字段。真实答复恰好两句：键固定，互换只是数值对调，字段不会消失/变undefined。这个 **真实模型后端源码纠正 PASS**，并区分当前源码与假设改动。知识语义路由返回`invalid_response`，实际解释走general fallback且非degraded；不称语义路由或角色自动调用CodeGraph通过。

Source：只读Sky Scout HEAD `7aae20f87033f404943f8a72ac7e6b38cc65e9a7`；weather_service.dart SHA256 `022bc38fc77e6adf38a87f8255f7f5c17be348bf6e7048b89fcf9b5bbbef6458`。CodeGraph只返回一个相关文件，模型只收到第14–19行；没有改源码、索引或重建架构图。Main获取源码并经正常Study入口送入，不能把它当作Native角色自主工具选择的新增证明。

本场DeepSeek+3，app/tech均+0；终态580/2000、56/null、0/0，同轮不重置。launcher18312已结束，48911/48916无listener。原始JSON/hostlog/DB只本地。设备和真人均未做；语义通过范围仅后端该问题。

下一步：修同课程之前互动的独立投影及来源标签，以一次summary-only真实检查验证已存错答可用，避免重复已通过源码回答或三工具设备路线。自然停顿整phrase实验并行先离线，默认OFF；局部失败不结束整个Goal。

## quality19 限定补证

既有course过滤的previous_course_history以独立prior来源投影后，Main仅做一项summary-only真实检查。exec74953终态，明确“上一轮”源码讨论与“更早一轮”图题；两句spoken summary使用已存错答、REZ→NUD→WEX和具体复述下一步，没有再要求补题。原interactions/QA均未改。该有限重启接续 **真实模型后端 PASS**，quality18失败原样保留。

本场只+1 DS，终态581/2000、56/null、tech0/0，无新CONNECT/Native/设备/human，launcher48216已清理、端口free。它不覆盖八行窗口外的更旧题；新grade-anchor正做离线增量，不能将19结果扩张到新anchor或所有长期相关性。旧反馈仍低估左右相反的解释；总结也复盘了最近源码课，单一题目的更强聚焦仍有改进空间。
