# 阶段九交付：图片重查来源与默认关闭的自然停顿接入

从功能分支codex/daily-learning-companion的080d69a继续，阶段成果可发布，不合并主分支。独立叙述宿主保护和声音验收仍待，整个A–F Goal未完成。

图片纠正可明确选择current_picture或literal_text；auto只接续同角色、boot、课程/会话/材料身份且最新已保存解释。丢弃旧summary后再解析单次语言。明确拒图优先，来源参数不能覆盖学习者选择；SQL/语言锁排队后复核原binding和最新记录。对象不清明确询问，不付费、不写假学习记录。

自然停顿已接真实Core/Omni授权、LOCAL_ACCEPTED和成功wire计数，默认OFF。20秒/640000原字节、1.2秒quiet、0.3秒前滚、单writer与8秒发送上限；保留非零微弱音频，只压全零内部停顿。UUID只标wire请求，不伪造provider utterance。handoff整段旁路；输入时间仍arrival估计。模式变化有未发preroll也fail-close，无待发则retire旧等待；日志异常不阻碍writer清理。

静音guard在常用Native/UI/voice/回环入口启动前拒绝，PortAudio延迟到guard后。NEKO_TASK_SILENT=1或本地ignored policy audio_allowed=false生效，无效policy拒绝。无policy的普通环境保持原行为；不声称Windows全局禁音或Native文字avatar已不初始化音频。

| 层 | 当前证据 |
| --- | --- |
| 源码/离线 | 最终60项PASS：20 actual Core/Omni/socket、12受影响旧handoff、4静音入口、24材料来源/SQLite/竞态。最终扩展that/latest/submitted/shown/Study/中文最新拒图与空text后，相关3方法再PASS。fresh Git LF四host目标完整bytes/AST/幂等/unknown拒绝3PASS。语言/summary14PASS、普通浏览器命令构造1PASS。 |
| 部署 | 固定daily插件26源/部署指纹匹配；两实际host transport与fresh LF一致042af91f557431e981ce588565f1dc827bb466109a8155c6c2179fdd83f7b3c8；helper79cff29ca529ebc2e2e421288f48f0a384ed6d88399707d24711223ecfa324bb；gate通过，无关TTS保留。 |
| 真实文字/图片模型 | 21读对「天气未命中 / 百科 HTTPS」但推广百科条件，PARTIAL；22中文区分直接事实/未知，实际auto重查、旧text忽略、历史保留；22错误赞同hit提议，23纠正miss而非hit、没有虚假赞同。22/23仍夹7汉字，严格纯英文FAIL。最新锁/拒图是后续SOURCE/OFFLINE，不外推模型通过。 |
| 设备/真人 | 本阶段无设备初始化/播放/录音/回环/Native窗口；无新增ASR、自然停顿provider、设备、人耳证明。继承普通真人验收，不重做。 |

60项合并运行334.248秒，其中一次fixture记录311.594秒异常装载/阻塞；原因未定位，可能有输出流背压（推断），不是模型或语音延迟证据。后续离线输出写raw日志再读结果，避免控制台影响观察，不反复跑这批已过组。

两位既有Agent仅只读审查，5项边界和一处拒图限定词残余均由Main修并补实际负例，限定复审无剩余具体发布阻断。迁移曾生成两份已知admission block，fresh LF发现失败；写入前严格normalize后两树一致，未知/残余重复在write前拒绝。失败保留，断言不放宽。

仅发布必要canonical插件/manifest、host patch/helper/启动guard、测试、单次新图片probe及证据/use。排除密钥、学习DB、raw、录音、隔离store、本地task policy和.workbuddy；完整contract/plan/status/blockers留项目内接续。原脏树和空index保留。

同轮bargein-autocheck-20261012：591/2000、app56/无固定累计上限、tech0/0；三个必要新后端场+10 DS、0 CONNECT，不重置、不为额度测试。相关证据见silent-resume、silent-picture-quality、phrase-input-implementation、phrase-host-contract及历史审查报告。

继续独立narration host权威current/claim/drain/media保护等静音可做项。严格英文需有界校验/修复策略，停止仅重复prompt的付费尝试。声音设备和最终一次10–20分钟真人待另行授权，未人工项不冒称通过。
