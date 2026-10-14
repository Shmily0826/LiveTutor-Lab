# 阶段十三：较早错题焦点的真实模型验证

**限定通过：受控离线教师窗口夹具 + 真实SDK/SQLite/model。** 这不是新连续真人学习、角色工具选择、Native、声音或human证据。既有19接续结果与18失败不改写，本场证明此前未有model证据的QA焦点路径。Goal继续active。

## 准备与数据保留

只使用本任务已有raw/neko-daily-speech-acceptance-20261014，未打开、复制、恢复或清理原用户daily库。通过mode=ro/query_only只读核对当前30条interaction为19完整原rows，2条QA整表仍原值；同课更早英文错答0分、较晚中文错答10分。主DB/WAL逻辑读取，不凭mtime。current question、evaluation、偏好和课程材料作为保护baseline，不重新出题/评分/制作图或录音。

30首准备因Store.load_config缺fallback参数停止，fixture0、model0，账本不变；修正为实际typed fallback后唯一31执行。复用actual StudyStore.append_interaction，向同课既有prior session追加8条中性concept_explain，明确metadata=test_fixture/source_scope=offline_fixture/learner_progress=false，文字也说明只占窗口、不代表学员学习。不是模型教师回答，不把夹具称自然连续教学。history retention满足39行保留，旧30前缀完整、原QA/题/偏好/材料不变。current历史实际有效空，不需要额外current窗口夹具。

## 一次真实调用与实际提示

public study_summarize_session，只传focus：更早那次英文方向错答、已有判分、下一步、两句、此前归因，不传分数、正确答案/方向或private context。真实SDK POST /runs→终态→export；一model started/completed，墙钟3.707秒，gateway3.062秒，2076 input/209 output tokens。没有native/audio/麦克风/回环/音量操作，没有新app CONNECT。

实际task gateway在发送前追加私有summary messages审计；其唯一变化是现有audit("started")添加messages，routing/runtime/model/预算/deadline/transport未改，canonical产品gateway不修改。source CLI仅在已知canonical gateway和neko-daily-speech-acceptance-* task store启用，unknown source保留拒绝；默认不审计messages，原用户daily不进入该入口。actual仪表记录中没有headers/runtime credentials，raw及学习数据不发布。

实发prompt：previous_answer_records恰2条，score0与10，scope=previous_session_same_course；prior8恰8条中性teacher fixture，current有效空，session_summary_seed={}。目标错答/反馈不在其余窗口，模型的0分和错答证据来自QA锚点；opaque旧QA/question/attempt/session/topic IDs、hidden reference_answer/rubric、图像和整个course_learning_state不在prompt，summary不走vision。没有把理论重建context当实发证据。

## 实际回答与检查

summary两句：明确是更早记录，回顾“所有箭头只从左到右”的英文错答、wrong/0分；正文下一步让学习者对照箭头按起点至终点重述模块顺序。这与该QA已有next_action一致，没有套较晚10分，不称本次刚完成/掌握，不索要已存题/答案，不生成新题或混入后来的源码课。

degraded=false。31新增恰一summarize_session行，其output等返回reply；8夹具保留且明确offline。旧30 rows前缀和全部2 QA完全相等，current题/evaluation/偏好/材料保护字段与baseline相同。所有10项结构/隐私/原数据检查通过后，Main另独立读回答/既有next_action作语义审阅；不是只用all(checks)宣布model质量。

私有prompt SHA256 996cf6cc21d4c4fb00e8a3752de0fca1ba73f1ac845a887871dbf12e9cc681b9。raw31 report、API audit和audit-final均benchmarks/raw/evidence；不commit这些学习内容/DB/API记录。

账本DS594→595/2000（本场+1）、app58/null不变、tech0，同bargein-autocheck-20261012，不重置，请求计数不是金额。31自有host终态已清理，48911/48916空闲。Root的新offline relay与task audit检查分别3/1通过；candidate验证另记录实际结果，原有记忆大批未重跑。B真实fixed input/自然停顿与观察通道局部问题仍在offline-control报告；转项后本场新增C真实model证明，整个Goal不结束。

Root与本场task部署的llm_prompts.py SHA256同为2f0d9a2113032f1c77f3d1d665031d11c6ebf6db116dd149f5297e6efcda2e24，prompt_templates.py同为9905fd448ef78a3826bcefce6f3fa1d94af33234d379070603ffbe92c31ca721。task gateway只加入上述观察记录，不把仪表改动视作产品逻辑改动。

发布候选实际验证：managed codex/daily-learning-companion在07a1fac基线上复制9项精确代码/报告，offline relay 3项、task audit 1项均通过；只用了临时目录/socketpair，未调用外部模型或设备。候选diff-check通过，窄审唯一P2已关闭。此次不重复已通过的旧记忆、语音、UI批次。
