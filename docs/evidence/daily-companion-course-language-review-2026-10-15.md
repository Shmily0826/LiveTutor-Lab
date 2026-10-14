# 阶段32：课程语言实际入口独立审查

按 Main 指定范围只读 canonical `__init__.py` / `study_avatar_tools.py` 的本轮增量、共享 course-memory fixture、新 course-language runtime 测试；随后补审 `neko_course_language_probe.py`。只写本报告，未修改实现、manifest、共享记录或部署。没有服务、provider、Native、浏览器、设备、mic/capture/loopback、账本操作或用户 DB 访问。离线测试使用独立临时 SQLite；实际 lifecycle、entry、context、prompt builders，模型和角色语言 pin 网络为替身。

## 原问题与本轮实现

44/45 的已记录失败是 persisted course English 而 direct SDK grade 实际中文。原 effective language 仅 avatar 路径应用；本轮把现有 `_study_effective_language()` 放在 `_start_study_session_locked` 的锁内、`selected_course` 写入当前 state 后，后续直接 entry 建 context 前，因此 startup/resume/idle/session 初始化可使用同一规则。未在语言修复中新增任何偏好存储或把临时请求升级为永久设置。

末级回退从当前 mutable cfg 改成首次缓存的 `_study_config_default_language`，避免 A 的有效 English 被当作无偏好 B 的“配置默认”。课程映射 > 明确 global preferences > legacy teaching_language > 原配置默认，保留现有优先级。首次缓存逻辑本来已有，本轮主要改实际使用的 fallback。

临时 explanation 仍用现有 explanation lock 序列化其 cfg override，并在 finally 回退；本轮新增课程已换时重新应用新课 effective language，防止旧请求把 B 的语言写回 A 的旧值。材料/session guard 仍拒旧课结果，没有通过采用新材料来掩盖旧请求。

## 独立执行

```powershell
.\benchmarks\raw\neko-product-host\.venv\Scripts\python.exe -X utf8 -B scripts/test_neko_course_language_runtime.py
.\benchmarks\raw\neko-product-host\.venv\Scripts\python.exe -X utf8 -B scripts/test_neko_product_course_memory.py
.\benchmarks\raw\neko-product-host\.venv\Scripts\python.exe -X utf8 -B scripts/test_neko_explanation_language.py
.\benchmarks\raw\neko-product-host\.venv\Scripts\python.exe -X utf8 -B scripts/test_neko_learning_preferences.py
```

本轮独立 **7/7** runtime（1.080秒）、**8/8** course memory（0.954秒）、**6/6** temporary-language（0.528秒）、**6/6** preferences（0.779秒）通过。共享 fixture 已从固定 lambda 改成 AST 提取真实 effective 方法，正确设置 relative-import package namespace，不再用“总是zh-CN”替身绕过新调用。

覆盖 startup/resume、direct grade 未先调用 avatar、五操作实际 prompt language、A en→B zh-TW→无偏好原默认 zh-CN→A、global/legacy priority、idle、临时语言后 direct grade、临时期间换 B 退役旧回复并保留 B 配置。这是 SOURCE/OFFLINE；不代表模型输出或所有并发已通过。

## P2：同课程新持久语言被临时 finally 覆盖

新增 finally 只比较 course_id，未保护同课程期间明确改变的持久语言。独立实际 entry/Store/临时 async fixture 复现：

1. A 已保存 en-US，启动有效 cfg=en-US；发一次临时中文 explanation，替身模型等待 Event。
2. 同课实际 `study_language_tool(language='zh-CN', scope='course')` 成功；持久 A 映射与 cfg 都变为 zh-CN。仅 `pin_character_language` 使用本地 AsyncMock，未执行网络。
3. 释放旧 explanation；course_id 仍 A，所以 finally 盲设 previous=en-US，未重新读取持久选择。
4. 同 session 下一次 direct grade 的真实 context.language=en-US，尽管持久 A=zh-CN。

建议最小修法：finally 恢复当前 effective 持久选择，或校验捕获的偏好版本/快照；不能只比较 course_id。临时请求本身仍不保存偏好。已报告 Main，发现先保留；修复关闭在后续追加。另一次尝试用 zh-TW tool 输入因现有 normalization 未支持而未修改偏好，不是该 P2 的复现；最终复现用明确支持的 zh-CN，choice.ok=True。

## 新单场 probe 窄审

`neko_course_language_probe.py` 限固定 owned C41/45 store、7 QA、空 current_question、当前课保存 en-US，原题/参考及既有 binding；不创建 pending、不先调用 avatar/language/set_course prime。唯一实际 SDK grade 在 ready 后调用，110秒 timeout，无盲重试；`--source --text-only` 和 `NEKO_TASK_SILENT=1` 同时保留。来源/期望部署指纹与29文件 manifest、唯一 protected static HTML 例外、SourceGate 均在启动前核；同 round 预算只读检查不重置，output x-mode claim，owned cleanup error 影响退出码。

判据核 old QA/mastery/interactions 完整前缀、formal +1、mastery +1、topic不变、FSRS identity集合不增、course及语言映射保持、前后无 pending。**没有用这些结构判据声称回复确为 English**；模型语言和反馈语义须实际终态另行核验。量具本轮没有新增具体 P1/P2，未执行它。cfg caching 与某些其他直接操作的全并发隔离不属于本轮已证明范围。

## 初稿指纹

| 文件 | SHA256 |
|---|---|
| __init__.py | 15daa339ddfab7dbce2d90627528a9803ab715ac88bb5bf6c40300c2474e1add |
| study_avatar_tools.py | 4523838fc6bf24c043edc3a64454cde37073d0d126d70fbbc96f577874799747 |
| test_neko_course_language_runtime.py | 3bcf1e8f42b168f5850369a60bcbc2ac0ce1b9adb994bdfe8a9a3ab890801f73 |
| test_neko_product_course_memory.py | d69a29973059c8939c69893d1494ef8f49cfe6258c13c62be232a842992fe067 |

不因本轮局部通过宣称 B 全面语言/语音验收，设备、人体验与整个 A–F Goal 仍按契约继续。

## 最终修复复核与冻结

Main 将 requested explanation 的 finally 改成先恢复 previous，再**无条件**应用当前 effective 持久选择；不只比较 course_id。独立读核新增第8项：实际 `study_language_tool` 在临时模型等待时保存同课 zh-CN，仅角色 pin 网络是替身；结束后 cfg 和下一次 direct grade 的实际 context 均 zh-CN。先前 P2 在 SOURCE/OFFLINE 层关闭，原发现保留。

Main 随后提出“实际 `_persist_state` 会 save_config，可能把课程语言当配置默认持久化”的假设，沿精确 callee 检查后被既有保护否定。本审查也只读确认：`store.py:548 save_config` 在写入前 pop language，`:540 load_config` 合并时过滤 language；因此**没有这个已存在缺陷，也没有新增生产 Store 修复或复制配置逻辑**。实际 `_persist_state` 仍是现有 save_config + save_state 两次调用。

共享 fixture 删掉原 save_state-only stub，AST names 加实际 `_persist_state` 并通过同一 bind loop 安装，避免测试绕过真实配置保存。新增第9项使用真实 save/close/reopen/load_config，配置仍 zh-CN，startup 应用课 A English，再切无偏好课回配置 Chinese，再返 A English；实际临时 SQLite 没有借用用户 DB。

最终独立按上列四命令执行：**9/9 runtime（1.369秒）+8/8 course memory（1.073秒）+6/6 explanation language（0.521秒）+6/6 preferences（0.731秒）全部通过**。这是最终实际 persist fixture 的结果，不能和初稿7项混称同一批。相应常规材料/语音、provider、设备测试未在本审查重复。未发现其他本范围内需要阻断的具体 P1/P2。

最终指纹：

| 文件 | SHA256 |
|---|---|
| __init__.py | 15daa339ddfab7dbce2d90627528a9803ab715ac88bb5bf6c40300c2474e1add |
| study_avatar_tools.py | 45e6bed56a136d067f832ceb9952aa941331be7507b81eb093df6e8280743f50 |
| test_neko_course_language_runtime.py | 021f20b86f8088fa37d87983a59fd8198b66775acd6d4ce6b4507b5a9f553b12 |
| test_neko_product_course_memory.py | 365733ac41b6be2b8728d411a4650787a85a87f8e27738a4e9e52bc93d6b19c7 |
| neko_course_language_probe.py | 76e8a546cf8dc20f20a301fc1d926148bc6ea4d0c9d73f268c9f1fe29d2cc286 |

产品仍仅 session effective 调用、默认 fallback 与临时 finally 两文件的最小增量；没有修库、保存临时偏好、或把所有并发解释/评分共享 cfg 隔离问题冒称已解决。单场 probe 自前次审查未变，没有新增 P1/P2；实际 English 输出语义仍须 Main 有界终态核验。报告冻结，部署/模型/发布由 Main 管理。

### 唯一末补 startup 基线缓存

最终只读补核 `startup`：先从 `self.config.dump` 重新 `build_config`，再实际 `store.load_config`，紧接着同步设置 `_study_config_default_language = str(self._cfg.language or '')`，在首次课程 effective 应用之前完成。故同一 plugin 对象再次 startup 时不会保留前次 cache，普通 session/换课本身不会重置配置基线。这里没有用上一课 mutable cfg 作为新原始配置；现有 Store 也继续过滤存储中的 language。

该唯一后补只涉及 startup 一行，最终 `__init__.py` SHA **`11d5b41556425793d1af4b9b19f7475d316907ae2d031172f0d9a10a6d100a44`**，替代前表该文件 hash。其余文件 bytes 不变。最终9/8/6/6独立批次已通过，但夹具不执行完整 plugin startup（只绑定指定 lifecycle 方法），因此这行只记 SOURCE 顺序核查，不冒同对象 startup 实际运行；不为此重复无关离线批次或启动应用。无新增具体 P1/P2，终审冻结。

## 实际单场46原件复核

仅只读 Main 已终结的 `benchmarks/raw/evidence/daily-companion-20261015-language46.json`，独立 SHA256 **`05d1de88e8b92f9b20583dafdd942b9de8954638b50580c7adb4930691785bc9`**，与 Main 提供值一致。没有新 provider/host、live DB 访问或写入、ledger 变更、原件改写或派生脚本文件。

从 before/after 原始行重算全部8判据，独立结果均 True：

- QA **7→8**、mastery **7→8**，新增一条 mastery 与同一绑定 topic 对应；原7 QA/7 mastery 的完整 row 字段保持。
- 所有 interactions **12→13**；另按 `kind=='answer_evaluate'` 独立统计，**正式 grade 是7→8**，不是12→13。原12 interactions 完整保持，新增正式记录的 session/input 与新 QA 相符，QA verdict/score/feedback 与本次返回一致。
- FSRS **4→4**，topic identity 集合不变；除本次被评分 topic 的卡可能正常更新外，其余卡完整 row 保留。没有新增或合并复习身份。
- 新 QA 的完整 learning_topic_binding 与原上一题 binding 相同（相同 key/topic/question scope），题干/参考答案同原题，公开 selected_topic_id 继续指向该题身份。course 与保存的 en-US 映射不变，前后 current_question 都 `{}`，没有 synthetic pending 或 avatar/set_course/language prime。

本场真实返回自然语言字段均已逐字段读核：reply/summary/feedback、misconceptions、step_feedback、reference_answer、missing_points、next_action、related_topics 使用 English；空 covered_points/diagnosis_questions 不当作额外语言证据。payload 内对应字段与顶层一致。原输入仍是中文 `WEX 指向 NUD。`，不能把原文保留误判为生成语言失败。

实际评分 **wrong0**。English feedback 说明给的是到达 NUD 的 WEX→NUD，而题目要求离开 NUD 的 NUD→REZ；misconceptions 和逐步说明同样区分 incoming/outgoing edge，参考答案 Start NUD, end REZ。没有把相邻两条边错误称为同端点反序。本次语义与 English 输出窄链成立，不外推所有题型/所有并发。

原件 finalized=True，没有 failure 或 cleanup_error；host_exit=1 保留为 Main 主动 terminate 的子进程结果，不改称 exit0。Main 已另核 owned PID 不存在、任务端口无 listener；本审查没有独立进程操作。原件 ledger 为 DS **723→724**、Lanlan.app **70→70**，未见 tech 新支出；audio/avatar/microphone/capture/loopback 全 False。新 probe 源码只有一次直接 SDK grade，已明确禁止先调用 avatar/course/language 进行 priming；不是 Native 或设备场。

因此阶段32可追加 **实际静音 SDK/模型/SQLite：启动后直接 grade 正确使用已保存课程 English，原记录与同题身份保持**。整体 B 语音、共享 cfg 全并发隔离、物理输出、真人体验仍未由本场验收，不把本场 PASS 扩大为整个 Goal 完成。报告冻结。
