# 日常学习伙伴：长期偏好与概念身份阶段记录

日期：2026-10-14，Pacific/Auckland。此阶段承接指定的图像 checkpoint、teaching-quality accepted、code-grounded tutor、product-memory 四份报告；历史线上验收不重做，旧额度不当作当前额度。

## 已交付

沿用 StudyStore SQLite 的 `kv` 表，键为 `learning_preferences`，没有新数据库或新的历史系统。保存字段限于语言 `zh-CN/zh-TW/en-US`、篇幅 `brief/balanced/detailed`、讲法 `step_by_step/example_first/direct`、严格布尔的 `proactive_quiz`。只有显式 `remember is True` 才写入；临时覆盖返回本次有效选项而不改持久记录。损坏或未知字段不会中断教学，也不进入提示。

未设置时默认为简短、分步、耐心、不追加主动测验。解释、生成题、评分、知识追踪、总结的真实提示构造函数均读取学习 context 中的偏好。当前明确要求以及课程/单次语言优先于全局偏好；明确请求出题仍可出题。模型是否实际遵循这些默认值，尚须真实模型验证。

手动出题如果明确指定当前课程已有主题 ID 或完全一致的名称，保留该主题身份；模型新生成的文字标签存入 `question_topic_label`，不再替换所选身份。评分优先使用已选 ID，再考虑题目/模型的标签。Mastery 与 FSRS 继续使用现有 `课程::主题` 键，因此对同一已选概念的错误和后来纠正会进入同一张卡。未明确选中的自由标签、历史已分散的卡没有模糊合并或改写。

保留现有同课程历史、当前题目、原始错误答案和后续纠正的读取链路；新测试核对重开 SQLite、再开同课程后错误与纠正都进入最终解释提示。没有重新宣称已通过的历史真人教学、图像或语音结果。

## 源码与离线证据

以下命令使用既有宿主隔离 Python。测试只用新建临时 SQLite 和真实产品方法，不启动宿主、浏览器、模型、录音或扬声器。

```powershell
& benchmarks/raw/neko-product-host/.venv/Scripts/python.exe -I -B scripts/test_neko_learning_preferences.py
& benchmarks/raw/neko-product-host/.venv/Scripts/python.exe -I -B scripts/test_neko_product_course_memory.py
```

新测试 5/5 通过；覆盖持久/临时区别、重开及跨课程的全局偏好、无损拒绝错误类型、损坏字段过滤、五类提示实际注入、概念标签漂移后两次 QA 共用一张 FSRS、重启后的 wrong/correct 记录进入提示、手动出题身份。相关既有课程记忆 6/6 通过；覆盖未答题重启、换课清理、同课记忆、课程隔离、历史顺序、总结和当次材料不被旧历史截断。差异空白检查通过。

这属于**源码/离线通过**；**真实模型效果、设备播放、真人长期偏好体验均待验收**。没有把 SQLite 写入或提示字符串当成实际回答遵循的证明。

## 集成与剩余

主 Agent 负责将 `learning_preferences.py` 加入 canonical product overlay；在角色工具中调用 `load_preferences` / `update_preferences`，明确长期意图才 `remember=true`，临时请求通过当次问句/上下文生效。更新读写需沿用插件锁；课程语言优先于全局，明确单次语言优先于二者。角色的默认禁题、篇幅合同需按偏好生成，避免主动测验或 detailed 偏好被硬编码默认覆盖。

需在真实模型上验证保存后的下一轮/重启遵循、一次性要求后回到长期偏好、换课返课的身份与历史。自由标签自动归并及久远历史的相关召回仍有支持边界：当前读取有上限，不能宣称任意旧对话均会恢复。本阶段不迁移旧卡、不清空原历史。

本子任务新增付费调用 **0**，没有调整主账本；没有创建测试宿主或音频进程，临时 SQLite 已由测试清理。共享额度和在线会话由主 Agent 统一记录。下一步为角色注册/部署核对及主 Agent 安排的真实模型验收。

集成审查追加：当前 context 支持仅实例内的 `_study_turn_preferences`，在下一次教学构造时合并并消费，临时字段覆盖 saved 而不落库。提示标注 `learning_preferences_scope=turn`，不将临时要求称为已保存。新增实际 prompt 单次消费回归后 `test_neko_learning_preferences.py` 为 **6/6 通过**；偏好工具的设置与语音 directive 由主 Agent 接入，真实模型遵循仍待验收。
