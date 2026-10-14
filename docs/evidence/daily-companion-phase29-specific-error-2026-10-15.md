# 阶段29：具体错因、语义等价和一次语言切换已取得分层证据

继承阶段28已发布代码7118f5e/记录107d76e，上一轮是progress；原Goal active，全A–F未缩。先已读contract/plan/status/blockers，契约原文不改；同round ledger706/2000、app70/null、tech0/0，不重置。本轮静音文字验证，不开avatar/音频/捕获/loopback，不改4%音量；仅Main在线与账本。

场40语义缺陷：材料WEX→NUD→REZ，本题NUD→REZ，答WEX→NUD是另一条边，不是反向。评估4b要求同两端点反序才称反向，其它edge/node/function/step指出具体选择差异，feedback/misconceptions/step_feedback一致，没有证据不编原因。原4a矛盾vs遗漏、expected/current question证据、评分/结构化语言未改。仅prompt七行，无固定图硬编码、输出改写、评分后处理或新记忆系统。独立源码窄审通过，不能当模型效果。

现default daily plugin-code prompt旧SHA与manifest一致，已独占备份并只改代码，manifest同步新SHA；不动SQLite/配置/学习数据。新隔离文字宿主会按原prepare_product_plugin部署相同代码。计划最多一场6个有价值模型请求：相邻边/真反向/正确对照，然后显式course English、一次中文临时解释、重启返课English；复用已有图的事实文本，不新造图或改Sky。预算总增量上限20DS，异常立即停止、保留run身份，不无限重试。语义由Main及独立只读复核，不以keyword自动宣称通过；不重复28 Native链。


## 原场41真实失败（保留）

唯一exec67671已terminal exit1，owned host pid36680退出/清理无error，三端口无listener。原semantics41.json SHA f36545263ab5dd4bb726de0264935b79d676566faf56209f6dfebdefd63f3867；不覆写/追认。场完成三次真实SDK评估及一次English解释，语言切换回调第五个模型请求前返回visual_context_missing后停止，无重试。ledger706→711DS、app70不变、tech0，原round/预算不变。

相邻WEX→NUD wrong0明确另一条边；真正反向REZ→NUD wrong0、misconceptions指出同端点方向相反，均不再混淆，正确参考NUD→REZ。对照正确答“NUD指向REZ”却partial60，反馈承认NUD到REZ仍要求重复“起点”才给满分，真实语义FAIL。course English已保存，英文回复真实两句；临时中文“这一次...箭头”被宽泛这+箭头AND错误识别为current_picture，丢弃给定notes并以visual_context_missing拒绝，没有模型调用，属于源码目标选择FAIL，不是服务离线/限流或课程语言遗忘。重启部分未执行，不能称通过。

真实评估附带knowledge_guidance还把关系图匹配到english_senior_clause_connection（匹配词“连接”“从”）；该泛词主题选择不适合材料，登记C/D后续，不在本次偷偷重标旧QA或重建知识图。

## 根据41新增的两处候选

prompt4c只要求语义等价按内容计分，不因没重复start/end逐字扣掉同样事实；额外推理仍按题目需求。study_explain复用explicit_picture_reference决定current_picture，真正这条/那条/this arrow仍选视觉；“这一次/这次/this time”不再因为任意另一处arrow一并选图。原literal/rejected/明确视觉/oldsummary与图片替换/排队复核保持。

Main language5、新增actual wrapper supplied notes/time modifier/真实visualmissing反例，native material guard25通过（含继承该新增方法一次）。待独立增量审与旧SHAguard同步两default代码/清单后，只复核41两个失败和后续语言重启；原相邻/反向不再付费重跑。原3QA及partial历史保留。


## 场42：语义对照修复，临时语言仍FAIL

唯一exec97000 terminal exit0、两owned host均退出/无cleanup error、原件semantics42.json已finalized但semantic_result仍PENDING_REVIEW，不把exit0等同全PASS。修后same正确文本NUD→REZ actualcorrect100，QA3→4、原3完整rowhash保留；临时文字不再visualmissing，实际进入模型，但回复仍英文。两host重启/返课均保留course English和4QA，新defaultEnglish实际两句。ledger711→716DS、app70/tech0不变。既有41FAIL/partial60保留，不修改原成绩。

源码明确语言原因：_turn_language_request因任何长期/always词return空，原完整“不要把这次中文要求保存成长期偏好”被错误拒绝。新增解析前仅去bounded明确否定save-preference子句，原请求及持久DB不改；真肯定以后/always/mixed及否定语言依旧拒。Main language6PASS；先1 English goingforward残留FAIL，补限定optional范围词尾后过，不吞but之后肯定scope。下一场只复核same完整中文请求→默认英文的连续切换，不重跑28链/41相邻反向/42正确成绩或重启，保留4QA。


## 最终收尾

场43唯一exec17689 terminal exit0、owned host已结束（raw host_exit=1是主动终止的host字段，非主probe退出码），无cleanup error/三端口无listener。原件SHA `d26ba02a523033a0d48d82e2ee1bbbd8a10b22ead50ade9990c3624a0af95f77`。实际相同完整临时中文句获得两句中文，下一请求两句英文；course English及4QA全rowhash前后不变。原42 SHA `26610cdee7ef9002b8ad35bd981e43d06833b2ba340b7d9f0a772f5f761df218` 的correct100、重启/返课保留和temporaryEnglishFAIL都保留，exit0不追认语义全过。

独立发现中文negative-save草案把“不要忘记以后用英文并保存为长期偏好”肯定reminder误删P2；最后仅否定词直接saveverb或把/将宾语结构才删除，三肯定reminder原scopeguard保持。Main/独立language6过、P2关闭source/offline；之前material25独立过，最终未变visual分支不重复。最终avatar源码/default SHA `01a145791e184ccfa9fcf172d37f463b9fcc29853263dabb143ba5b4d0cfe432`，prompt `89dbaaf7540a5cd1dae6e5a1a068ab764c2c398053fa984111852e53be74181a`。43使用先前avatar f6f67...，不能冒称最后新增reminder分支真实通过；无需为这一离线拒绝边界复跑已过模型正路。

specific-error-review已独立只读41/42/43并冻结，核same question/answer含义、所有相关反馈、41两个wrong0区别与原correctpartial、42newcorrect100/old3hash/两hostcourseEnglish+4QA、43中文→英文及4QA/prefs保持。没有写原JSON或伪造派生PASS。41措辞/42语言新FAIL逐个保留，40原FAIL范围也不被后续prompt文字验证追认。

本阶段14总DS（706→720/2000），app70/null/tech0/0不变；非14次评分，未调上限/重置round、未换provider。无音频/Native/设备/回环/物理输出/human验收，当前纯HTTP/SDK真实模型+SQLite文字证据。Scope不外推所有语言/题型/语音自然短答。两default源码oldSHAguard+独占backup、清单全部sourcehash及host SourceGate过，保留原用户数据/Root脏树。原一次inline导入缺scripts路径的检查失败已改成只读带路径检查通过，没有因此另开host。

三current记录已精简，精简前各原bytes独占归档到history-through-phase28-and-phase29-start，SHA见各current文；fullcontract169行完全不改且摘要不能替代原文，四文件接续/后续指令优先/局部阻塞转任务/证据完结条件均保留。下一步C/D指导相关性：41knowledge_guidance错误英语从句，QA实际仍同course::有向关系；从既有match_topics/_query_terms/subject证据离线定位，不改旧QA/不建另一系统，再继续全部A–F日常集成。阶段29精确allowlist发布待核，不动master。
