# Study动态就绪与日常入口窄审

2026-10-14。完整读取contract、plan、status、blockers后执行；当前阶段十六已发布`d0c28db65509b673ccea812c4cee8cf244569878`，阶段十五文字入口`e34c2f9`证据继承。只读canonical `static/index.html/main.js`、课程/session必要callee，以及阶段十五task部署的既有request/i18n/status payload小helper；没有启动服务、浏览器、API、测试、模型、设备、捕获、麦克风或回环，也未发声、读用户DB、查/改账本、派Agent。唯一新增本报告，screen_scope_review未动。

## 即时Refreshing的证据判断

阶段十五public报告明确web-inspector只等DOMContentLoaded；该点不等待`bootstrap()`发起的SDK `/runs`创建、轮询与export完成。`main.js:2449–2453`先await i18n，绑定操作后`2691`才await refresh；`refreshStatus:2004–2020`先写Refreshing，await study_status成功后才render状态。看到这个中间文案符合正常加载顺序，**不能由此认定卡住或初始引导回归**。

正常网络/响应体完成的路径上，study_status预算15秒，poll有递增间隔/terminal/error检查；失败由bootstrap catch显示Not ready＋错误，手动刷新由bindButton catch显示Error＋错误，finally恢复按钮。refresh revision会忽略旧并发状态响应，图片metadata read失败不丢图或重新调用模型。以上是SOURCE控制流，不是实测完整UI ready。静态诊断卡默认“Ready for a study session”也不能单凭初始DOM当真实后台就绪；应等一次当前SDK状态和诊断渲染。

本轮确认三个具体日常入口缺口，下述都是源码触发路径，不宣称阶段十五已实际发生。

## P2-1：成功讲解被后续状态刷新失败覆盖

**调用/触发：**用户选择或粘贴图、点击讲解，`study_submit_image`成功返回reply。`main.js:2174–2201`已显示回复、保存previousExplanation，并保留当前图片。随后`2202`附带refreshStatus失败；通常notice `n`为空，此catch重新throw。`bindButton:2404–2406`把页面回复替换为formatPluginError，网络类消息为“图片已保留；点击刷新，恢复连接后再讲解”。

**影响：**真正成功的讲解/历史并未因此删除，但当前可见回复丢失，用户被提示再讲解，可能重复付费生成；刷新失败被误呈现成整个讲解失败。notice非空会吞刷新错误，这个偶然分支不是可靠成功保护。

**最小修法：**把“已成功操作”与“附带状态刷新”分开：成功回复保留，附带刷新失败显示独立“讲解已完成，状态暂未刷新；请刷新恢复连接”提示；保留studyServiceReady=false、当前图/previousExplanation及原课程guard，不能自动重试模型。网络提交本身失败仍沿原catch报错。不要简单吞掉全部错误或把连接失败说成已Ready。

**定向负例：**实际explain方法的submit promise成功，随后status promise reject/503；assert reply仍为成功原文、submit恰一次、图仍在、提示明确只是状态失败、讲解按钮退出busy。另核submit失败仍报失败，不伪造reply；课程变化后的旧结果仍不显示。

## P2-2：UI只有fresh课程操作，缺少返回课程的resume入口

**调用/触发：**`index.html:79–85`课程ID输入与“开始/重新开始Session”按钮绑定`startCourseSession`。`main.js:2091–2113`始终调用`study_start_session`，并清题/答案/反馈/输入。后端`entry_tutor_summary_entries.py:25–35`为显式fresh；新按课checkpoint里fresh会替换当前课产物。UI没有调用`study_set_course`的路径。

**影响：**fresh按钮本身遵循其既定语义，不是后端恢复bug。但用户从该课程入口A→B→A时，不能保留A待答题；这与contract C返回接续的日常UI需求尚未对接。33真实role set_course接续通过不能外推为该按钮也会resume。仅靠告诉用户同ID仍不足以区分fresh与返回。

**最小修法：**提供明确“选择/返回课程”操作复用既有study_set_course；将fresh“重新开始”保留为独立且语义明确的操作，不能偷偷让既有explicit fresh复活题。返回后的公开pending题由下一项status同步，保留source/question/attempt身份，不重新生成，不写另一套DB。

**定向检查：**按钮对应entry和真实返回语义，resume A→B→A只读原题、fresh同A仍退役题；不要重做旧8项底层checkpoint或再付费出一题冒恢复。本轮是缺入口的SOURCE发现，不要求为实现新UI解释额外音频权限。

## P2-3：Study刷新没有同步当前题/session，重载后无法从页面续答

**调用/触发：**canonical `__init__.py:1273–1305`的`_status_payload`仍调用既有`build_status_payload`；阶段十五task实际baseline `service.py:17–73`给状态、课程、评分、last_question_at等，但没有study_session_id/current_question。SDK status entry装饰器列出current_question不能自动补出缺失字段。

前端`currentQuestion`初始null。`setStatusLine:1380–1418`更新课程、图片/文字、模式和状态；`setStudyState:1196–1223`更新评价/习惯，但不恢复题。`setGeneratedQuestion`仅在成功新出题及fresh清空路径调用。`loadQuestionContext`取得的是下一出题选择上下文，不是恢复已有题。因此即使后端restart保留了原pending题，重载Study页的`evaluateAnswer:2243–2244`仍报“请先生成题目”。同页若角色换课后用户刷新，现函数清图和studyInput，却未同步或清理旧currentQuestion/answer/feedback，可能在新课程界面继续展示旧题；后端严格guard应拒绝不匹配评分，不把该展示问题说成已污染DB。

另因plain status不带session，`studySessionId()`常为空，UI提交/控制通知的same-course session比较无法从这份status区分真实session替换；后端材料/session guard仍是主要保护。测试若只注入额外session字段不能证明真实plain status已提供它。

**最小修法：**在当前权威status补真实Study session及`public_current_question_payload`、question_state；不返回私有答案/reference/rubric/cache/owner。前端在当前refresh revision及课程/session匹配后同步公开题；题身份变化/无题时清旧答案与反馈，相同pending题刷新不得清正在输入的答案。若复用已存在study_session(status)工具返回，也须明确与本次课程/session绑定，不能从history旧题重建或调用quiz替代恢复。

**定向检查：**freshDOM收到真实public status→原qid/attempt/题显示、可准备续答；same题普通refresh保留用户draft；外部切B status清A旧题/答案，返回A恢复原公开题；same课fresh session＋none清旧题；未包含hidden keys。这里只需实际status投影＋DOM/stub，而非重复底层grade、model或33全文场。

## 后续最小完整UI验收建议

Main下一次使用独立task store、文字入口、静音/offline；原daily DB/设置不复制、不清空。受控本地界面采用用户指定shared web-inspector工具。本Agent此次未运行它。

1. 从Starting/Refreshing等待**本次**study_status terminal/export及课程/模式/诊断渲染，不以HTTP200或DOMContentLoaded结束。记录响应与可见状态，当前SDK失败应有Not ready/Error和恢复操作。
2. 已有forward图通过真实file入口选一次：压缩/preview可见、读取busy结束、课程归属明确。不要调用窗口capture，不再验证已通过初引导；图片输入可在offlineUI场只检查本地选择，不将其说成已提交/模型讲解通过。
3. 用本地已明确标fixture的SDK响应检查一次完整讲解DOM路径、busy恢复和第二次status故障：必须保留成功reply/图片、独立错误提示、零模型重试。fixture不是真实模型语义证据；若最终验收安排真实讲解，由Main另计一次必要调用，不因此重复旧图片模型场。
4. 复用一个已有隔离pending checkpoint或者Main自建本地fixture，完整检查resume课程与fresh区别、刷新后public题同步。不能打开原用户history，也不能复制C33 DB或再出题凑通过。
5. 在同一有界UI场恢复status成功，确认提示与状态恢复、保留same题draft；检查课程变化后的晚异步结果被忽略。没有Native/provider/声音/设备/human扩展。

源码/DOM stub、真实SDK/SQLite、模型、设备、human分别记录。旧网络503 backend证明、C33实际role恢复继续继承，只验证本轮新可见操作和故障反馈，不循环跑整个旧教学批次。

## 冻结

canonical main SHA `c8a8bb5e4a5dc51b2e3dedd9a18f5723b739baf38ab9014d6701f3e9009ff2ba`，index SHA `b9b83114fb7bc7feafca691f2763a57eff076251b3c4c5a61d9e3d1a1192b92e`。这里只确认源码可复现条件；没有把原Refreshing初态定为bug，也没有新UI/模型PASS。仅本报告新增，源代码/测试/manifest/共享记录/进程/额度/用户数据未改。报告冻结，Main负责必要修复与执行。

## 已授权实施与SOURCE/OFFLINE关闭

Main随后明确授权三个canonical文件及对应窄tests。本子任务已完成增量修改，原上述发现和只读时的证据不抹掉。

- `static/main.js/index.html`：新增独立aria-live刷新notice与`refreshAfterSuccess`。已显示的讲解/出题/评分/总结回复及图片不因附带status失败被覆盖，status失败仍使serviceReady=false，提示手动刷新，不重试模型；恢复刷新后清notice。真正submit失败仍走原错误分支，不伪造成功。旧课程/session/material guard保持。
- 两个课程按钮明确分开：“选择/返回课程（接续原题）”只调用existing study_set_course；“新开Session（退役当前题）”仍调用study_start_session。成功课程操作清旧本地输入/反馈并绑定已接受course/session，再刷新权威状态；不会从旧history造题，不改设置、checkpoint或DB逻辑。刷新失败时显示状态待刷新，不把旧课题继续展示为当前题。
- `payload/study_companion/service.py`：existing status增加真实study_session_id、existing public_current_question_payload投影及pending/evaluated/none；局部held dict用于公开题/状态一致计算。隐藏answer/reference/rubric/accepted answers/solution/private payload/cache/运行reservation，原状态不被改写，没有从history恢复题。
- UI `syncStatusQuestion`按当前refresh revision同步公开题。课程/session/qid/attempt/题文字或选项变化、无题时清旧答案/图片/反馈；相同题刷新保draft和已有grade feedback，pending题可继续用原IDs提交。evaluated同题状态更新不清刚显示的评分反馈。已有旧刷新晚返回不能覆盖新课。

实际执行的窄命令与结果：

```powershell
node --test scripts/test_neko_study_ui_resume.mjs
# 13 PASS, 0 fail; actual UI methods + local DOM/RPC stubs
& 'benchmarks/raw/neko-product-host/.venv/Scripts/python.exe' scripts/test_neko_study_status_question.py
# 3 PASS; actual StudyState/StudyConfig/public helper/status function
node scripts/test_neko_material_control_ui.js
# existing 14 actual UI DOM/stub checks PASS
git diff --check -- patches/neko-study-2026-10-10-product/static/main.js patches/neko-study-2026-10-10-product/static/index.html patches/neko-study-2026-10-10-product/payload/study_companion/service.py
# PASS
```

状态投影3项核qid/attempt和当前session、private keys/cache剔除、0分保留、deep copy不污染原state、none不复活历史题。Node13项核新DOM恢复与原ID续答（评分回复明确为fixture）、same题draft保留、same evaluated保反馈、6种身份变化清旧答案、resume/fresh准确entry与标签、成功image后status网络失败仍保reply/图片/previousExplanation和busy退出且submit恰一次、真实submit失败诚实报错、旧status晚回被忽略。VM capture/Audio/AudioContext/SpeechRecognition入口全部throw，检查无device调用。没有浏览器、本地listener、SDK服务器、provider、录音/播放/回环，也没有创建或读取DB。

修改/新增精确范围：上述3canonical文件；新`scripts/test_neko_study_status_question.py`、`scripts/test_neko_study_ui_resume.mjs`；本报告追加。__init__/models/store/manifest/host/telemetry/四记录/预算及其他报告均未修改；没有commit/push或部署，原脏树保留。只运行受影响窄测试，未重复基础教学、C33或图像模型场。

最终canonical SHA256：main `32f6746b78490d69021317842a2ea3bc5b0a32b7d86446efb0e20d2a81d37c03`；index `cb27a30693e5023dd167781165201712aed79e8662602594f984f2e7e2440928`；service `aba8ec8f1de914daa9d88b9d0f43194fc29a3779d05bcd36cd53d6341a2dcc47`。

三项 **SOURCE/OFFLINE CLOSED**，不是已部署SDK/实际浏览器/model/device/human通过。下一步由Main同步manifest、部署并做一次完整静音UI操作验收；浏览器ready实际时序、真实runs/export新字段、既有课程checkpoint接续与新DOM联通仍需该层验证。原DOMContentLoaded Refreshing判断保持正常初态/证据不足，不冒称它曾是卡住事故。代码与报告现冻结，Main可复制review。

## 后续审查P2：非解释工具的晚结果DOM围栏已补齐

独立screen源审指出：此前generateQuestion/evaluateAnswer/summarizeSession在await callPlugin后会直接写结果；A请求期间切B，晚A成功或异常可能覆盖B DOM。上节13项没有覆盖这三条晚callback，不把当时通过扩为该竞态已安全。Main明确只授权main.js、对应新UI测试及本报告追加，本子任务已按此增量修复。

三条请求复用explainText的同类围栏：初始捕获课程、真实Study session与既有UI `studyMaterialRevision`；返回成功与catch异常都在任何结果状态/题目/反馈/reply写入前核原范围，过期直接return，不重提交、不覆盖新课错误/回复。评分另外固定请求的qid/attempt，返回时要求仍为当前题；A→B→A因为session不同也不能借原qid重新认领。材料范围是既有UI版本，不新造provider utterance ID或长期记忆；后端原材料guard保持。

出题准备阶段也不把旧scope/selection response写回新课：get_practice_scope成功先围栏再调用原setPracticeScopeState；loadQuestionContext新增内部isCurrent选项，迟到成功/错误先拒绝再碰selection DOM。合法当前selection错误仍保留原“显示选择诊断，已有literal text可继续出题”的降级语义，不无故取消ordinary路径或增API调用。

`node --test scripts/test_neko_study_ui_resume.mjs` 最终 **44 PASS**：包含原13、generate/grade/summary三操作×course/session/material×late成功/失败共18、grade qid/attempt各成功/失败4、当前generate/summary成功、scope准备与selection准备的迟到成功/错误各2、当前optional选择失败保literal fallback、三类当前remote错误仍可见/仅调用一次。实际方法＋deferred RPC fixtures断言B/current reply、status、题、答案和feedback保持，过期后调用数不增加；VM capture/output构造器仍throw，没有设备/服务/API。

既有`node scripts/test_neko_material_control_ui.js` **14 PASS**（本轮新增生成准备末尾测试只改test文件，不影响此production指纹）；`git diff --check`过。service/index此轮未动，所以原真实status投影3项仍继承，不重复无变化批次。最终main SHA `38cb30d8622fdf539b2754911b2a8663b4ff9e9d502672561a3434ff434e6185`，UI test SHA `32849ae57dee12d34a6128a0ff02c3988ec40e5cfede6a804e8d8d5e17c4f123`。

此P2 **SOURCE/OFFLINE CLOSED**。新版实际runs/export、完整浏览器操作和部署由Main验证；没有SDK/model/device/human新PASS。仅main.js、新UI test和本报告变化，其余生产文件/host/manifest/四记录/用户DB/预算未改，无commit/push。代码与报告再次冻结。
