# 已评分当前题重启/idle接续窄复审

2026-10-15。只读Main新canonical __init__.py的startup/启动wrapper/locked/ensure增量，实际test_neko_product_course_memory harness导出及test_neko_graded_restart；仅新增本报告。没有源码、tests、manifest、共享记录或用户DB修改，没有服务/provider/设备/mic/capture/loopback，不动额度。

## 已知真实事故与结论

Main阶段23实际HTTP模型wrong→correct同qid新attempt，2条QA保留原wrong通过，仅2次新DS；换课ACK量具KeyError保持其失败事实。随后实际host重启发现原resume_pending-only启动清掉graded current_question/latest evaluation并把空内容写进course checkpoint，原2条QA尚在。该事故没有变成数据全删，也不能因QA存在就说当前接续正常。

本次修复源码未见具体P1/P2阻断；新增3项独立SOURCE/OFFLINE PASS。**修后的完整宿主重启/实际SDK回读尚未由本Agent验证**。Main此前真实模型两QA证明评分链，不外推这版重启已MODEL/DEVICE通过。

## 源码收口

canonical __init__.py（本次SHA256 `a140babdd0879c4b89c29d7f7a675772fd3db98541f184e056eb38f685fbfb8b`）：

- startup `347–381`沿原Store.load_state读取，不再在启动前清掉当前原题/latest grade；仅去已退休reservation pending/owner，然后调用_start_study_session(..., resume_current_progress=True)。study_session_id新建是生命周期，不改原qid/attempt、题干/私有缓存，也不把原成绩标为本次新完成。
- `_start_study_session:799–802`实际wrapper在原session lock内透传新参数；harness已导出此wrapper而非只调用locked方法，新增检查确实经过其参数。
- `_start_study_session_locked:817–823`只在state.study_course_id与selected_course相同时用已加载live state的四字段覆盖progress：current_question、last_answer_evaluation、last_question_at、last_answer_evaluated_at。它优先于stale retry/course checkpoint；即使四字段中的题为空，这个dict也有四key，所以不会回退到旧checkpoint复活题。
- `829–854`恢复原artifact双ID及已评分状态/cache，清pending/owner reservation；latest evaluation只有仍有完整held题时恢复。没有调用模型、重出题、从反馈文本重建答案或重命名topic。恢复是字典复制，私有原question内容/原origin不被当前saved图重写。
- `900–912`的ensure在session空或30分钟idle后用resume_current_progress=True；原end保存checkpoint、退休session后保留live题/grade再建新session。scope始终是当前course，旧in-flight owner不跨session沿用。
- 显式fresh/换课仍走_restart_study_session，未自动传新resume_current_progress；fresh继续退题，set_course继续按其显式resume_course_progress读取已保存该课checkpoint。新参数不能将current课state借给不同selected_course，条件相等才应用。

## 异步/identity边界

标准外层wrapper、ensure和restart都持_study_session_lock，串行正常换课/start请求；progress/current question读取与安装在原state lock内。新分支没有在启动之前提前复制一个旧graded题来覆盖模型等待期间更新的题，而是在安装时读取当前live四字段；正常grade/retry与state lock继续协调。session/material load前的await不允许调用者借旧Core/Native输入owner：旧输入、旧_expected_question.session_id必须仍被原grade guards拒绝，不能因为原qid恢复就提升旧任务。

课变更/重启会产生新session/material control；artifact source origin仍指向原材料和原session，属于immutable题，不能宣称新图被重新评分。所述场景依赖现有setter锁与合法persisted State，未审修复绕锁直接改state/坏库伪造foreign origin。只要权威State course与selected course不同，当前进度分支不采用；无course归属不能通过泛“看上去像同题”强行恢复。

启动末尾`866–867`仍按既有流程分别save_course_progress及_persist_state，没有本次新增掉电原子保障；这是继承的生命周期写入边界，与retry入口专用atomic两kv不同。完整磁盘故障/进程强杀在两次写之间未验，不应把本次正常Store close/open证明扩大为掉电原子checkpoint。此不是本次新增错题采纳问题。

## 独立执行及证明层

```powershell
& benchmarks/raw/neko-product-host/.venv/Scripts/python.exe -X utf8 -B scripts/test_neko_graded_restart.py
```

3 tests PASS、0.443秒、exit0，fresh临时SQLite，没有服务/模型调用。Main已跑的course8/answer14不重复，按Main原结果继承。

覆盖：

1. 从真实startup AST提取唯一_start_study_session kwargs，确认resume_current_progress=True；通过实际wrapper/locked＋Store close/open，新State wrong0/correct100两subcase的最新attempt/cache/evaluation优先于stale checkpoint；原interaction整行保持，public status evaluated且不露cache。
2. empty runtime session/31分钟idle两subcase恢复grade与时间，换新session并清departed pending/owner，不生成QA。
3. 显式fresh退题，故意stale旧checkpoint后Store重新open/start仍为空，B→A返回也不复活；旧latest evaluation也不伪配空题。

test的graded State/cache是明确的持久化fixture，interaction也是中性输入夹具，**不是实际模型产生的wrong/correct、不是两个QA生成测试**；其用途是复现保存/优先级/状态加载机械缺陷。已有phase23实际模型和同题retry10独立承担评分证据，不混层。该test没有执行整个startup的OCR/agent/SDK初始化；本次源审另核实际startup没有提前清grade，不能仅凭AST kwargs把完整startup运行标PASS。fixture不用原用户DB，未以restore/clear/copy原库制造结果。

新test SHA256 `47d37256cd89d638d80b5ba1a366c1f69edfb54a5d9f662ee6c69e34ae9859a4`。以上为本次版本快照。

## 接下来

Main可在原授权任务store、无新模型调用的正常host重启中核同qid/new corrected aid/latest grade及2条QA仍在，读实际SDK状态/公开题和history/QA hashes；空/fresh分支按已有fixture范围，无需反复重出题。旧真实重启清题事故和ACK量具KeyError均保留，不追认首次结果；只在修后证据到达后单独记闭合。

Native零tool评分与缺ID终结/输出协议仍局部pending，本重启修复不解除它，也不因此结束Goal。唯一本报告写入，完成后冻结供Main整合。
