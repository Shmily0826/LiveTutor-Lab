# 阶段十：英文讲解校验与局部修复

阶段九recheck22/23的英文主体仍夹带7个汉字，均保留FAIL。现在在既有解释链保存前检查中文讲解/图标签，最多一次局部翻译，不重新生成周围的英文事实句、数字或ASCII标识符。复用原agent/gateway及primary runtime/image；既有调用者绑定的模型快照优先，group不匹配继续由gateway拒绝，不切供应商。

只有需要修复时才额外调用。最多12个Han片段、1200个Han字符、8000字符回答，8秒且受原primary deadline约束；无循环或SDK重试。译文必须是数量一致的ASCII字符串，不接受空值、数字、backtick、换行或截断。缓存“未命中”只接受无反极性的cache miss名词短语，复杂条件/双重否定不能可靠校验就拒绝。材料已换、取消、超时或修复失败不会保存成成功解释；结构repair之后还有一次最终语言检查。私有材料复核callback仅放agent_context，不写历史。

明确同源代码/数据原文保持：已知语言fence须与source相同（允许CRLF/LF比较），包括JSON/YAML/XML/HTML等；未知Unicode代码拒绝翻译。已知source fenced代码中的Unicode inline标识符，以及source原样的inline JSON/调用/下标/属性也保留。普通图标签的反引号、text/plain/markdown fence不豁免；未证明的Unicode inline token/表达式（包括模糊的反引号图标签）直接拒绝修复，不发请求，不改名。普通引号中的图标签可翻译。这里只处理English解释链的Han混入；不宣称所有语言、任意Unicode代码、题目/评分/总结均有同等校验。

## 证据分层

| 层 | 实际结果与边界 |
| --- | --- |
| 源码/离线 | 12实际helper/agent/runtime/entry/新SQLite检查，加32受影响材料/课程/语言检查，同组44 PASS。复审收紧same-source text、JSON/未知code及inline数据后，仅相关12再PASS；未无谓重跑整组。反译hit/not miss、图标签冒充代码、bound runtime覆盖、代码数据被译名的失败均有负例并修复。 |
| 真实模型/SDK/DB | recheck24只复用既有Sky暗色PNG和隔离store；一个correction-only请求，不重做已过中文/节点场。两句English正确说明weather cache miss而非hit、百科缓存条件图中未知；没有Han，未错误赞同学习者。DB repair_attempted=true、最终reply等于真实存储；旧interaction/QA不变、same course、当前材料身份与原question保留。该图场限定PASS。 |
| 部署 | 最新28 canonical/daily-plugin-code SHA一致。24实际store在调用时28文件与当时manifest一致；24之后新增JSON/未知语言/inline代码保护只有SOURCE/OFFLINE，不将其写成新模型通过。 |
| 设备/真人 | 无浏览器、Native窗口、声音设备初始化、播放、房间麦克风、虚拟设备或回环；无新增设备或真人证明。未到最终验收，不完成整个Goal。 |

recheck24真实输出开头是“You're right to question it, but … opposite”，随后明确miss/not hit，表示允许质疑而非赞同错误关系。最终两句约55个英文词，仍可进一步缩短。总callback墙钟6.480秒，包含既有语义/vision/局部翻译链，不是首音频延迟，也不能以与23的4.778秒单场差值声称已定位性能瓶颈。

24所验concept SHA是ec4946b61c16055a737fa7b1a95d916af58b1f64dcda16aa148ba43a4def450c；后续代码/数据边界修复没有额外付费。最新concept为32889c6bac3438d78bcd5ce50a677d850ed648ecbcae71dcb2a779817c1289c6；entry为9b3601565e8c554c5be159aa2c6d031bbf3e87b96906a4c5283900c1ff7e29e9；runtime agent为618e3dc5d3def47bcfa644fa280799233fac9b84969c8dde0e85c4ea80c04257。未知inline内容及半截代码/截断回答不翻译；已知source Unicode标识符即使未用反引号也保留。最终边界12项见daily-phase10-boundaries-final12。

raw仅本地：silent-recheck24 JSON/host/console/audit，daily-phase10-final-offline44与literal-data-fix12日志。自有host launcher53964已结束，48911/48916 free。源/单纯离线不冒称模型，backend不冒称设备；旧失败不被追写。

同轮bargein-autocheck-20261012：DS591→594/2000（+3），app56/null不变，tech0/0；请求不是账单金额，不重置。不为额度重复测试。严格静音policy仍false。

独立narration宿主尚缺权威current boot/course/session与最终提交协议，仍默认OFF；精确接点和最小拒绝方案见narration-host-plan。同一Goal继续其他A–F，下一步在现有metadata/队列中补权威确认与claim/drain保护，不另建学习记忆或队列，不借上次tool owner。声音和最终一次10–20分钟真人等新的明确授权。
