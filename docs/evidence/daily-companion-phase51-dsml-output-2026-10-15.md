# 阶段51：内部工具标记输出边界

完整[contract](../daily-companion-contract-2026-10-14.md)优先；全部A–F/Goal active。

阶段51开始：沿实际host ToolLeakFilter加入DSML流式抑制，复用现参数深度和跨chunk尾缓存；不把文本解析为可执行tool。角色可见流仅当最终段无有效文字且过滤了DSML时给诚实失败提示，沿generation取消/槽位所有权；不静默空答、不重试或增加cap。最小可重放patch双host/source指纹固定，先离线断片/参数内假关闭/普通文字/取消/工具轮sentinel检查，随后再决定真实场。原filter/tools/host/manifest独占备份phase51-before，账本847/78/0、无live场/音频/捕获。

阶段51开发冻结：13不同新离线case PASS .142s（首轮测试async join夹具错误已修，不是产品失败），原34过滤case对候选原样PASS，共47不同case；DSML每断点/单字流、parameter内伪close、40k未闭合payload有限尾缓存、普通XML/HTML/提工具名、truncated标记、双host重放/未知source全计划拒改、已有工具轮sentinel/已filter flag/取消generation/调用方slot所有权均覆盖。双host filter SHA13471cc292190928d0a5bf59de98bddff86cac46e835290962141d0bae963a95、offline _tools SHAf832282705c7f9d7e1668eebd96c850a73633006570c6b561a6b6c9c82e90f53已按原base固定重放；host manifest SHA2a36f881b0f873839cd70d570b5bfef6d4d854b7c95ebca517fbb087c6357644，helper脚本pin/SourceGate PASS。只隐藏协议文本，不执行它；无有效最终回答给固定中文诚实提示，不开新provider请求/不加cap。该提示的跨语言适配仍未验证，未知DSML变体不承诺全覆盖。

唯一修后静音60准备：复用已审contrast-only量具，fresh任务store、只拷授权JSON、strict text-only/TASK_SILENT、现有DeepSeek角色textWS/CodeGraph，原round2000全局硬顶/32事件间停止/单场380s，无Native/浏览器/声音/mic/capture/loopback。当前847/78/0、目标store/output/log不存在/三端口空，pre60 Gate PASS；只跑改变后必要三对比，不为耗额度测试。尚未启动，不冒模型通过。

scripts/neko_dsml_output_patch.py SHA3671d2f098c4d090b6f84181b229812c1244a4e6bc0e366ced1c4ef1c87b477b
scripts/test_neko_dsml_output.py SHA49855fbe79e6969b663fe07ff9886ab33d88ab316d44157717dc69922664263d
scripts/neko_desktop_tutor_host.py SHAa4f280772cffa5b42540bcb9debc4d9c0052bf84b49070bfdd1615d746171669

阶段51唯一修后静音真实60已启动exec28554，fresh neko-daily-code-contrast-20261015-60，原847/78/0起。只poll同handle；尚未终态，不冒模型/清理通过。严格text-only/TASK_SILENT与原cap保持，没有Native/浏览器/音频/捕获。

51当前：DSML流式标记过滤与无有效最终回答提示已按固定SHA部署双host，13新+34原过滤共47不同离线case PASS，SourceGate PASS。唯一静音真实60三轮/4源码receipts，直接命中文件、无DSML可见，本场+7请求至DS854/2000、app78/null、tech0/0。教学整体仍PARTIAL：首轮正确区分map行序但>2句；后两轮被旧第二个竖线围栏截断，第三还过强断言值交换过校验。controller exit0/host forced-stop1、owned/三端口全清。下一52修数学/代码竖线被误截的实际根因，保持真正保护；不盲重跑模型/不要求human，全部A–F/Goal active。

阶段51终态：60原raw SHA 6ffd94615ae014ba573fbbc2b95af932779457bfa1ad726e8df194ed83b4d246；独立terminal另件 SHA a1d82ecf92a4e382eb427c29c67c1fc727c05c9e8b5cae61650b12bcb245d891。原semantics=PENDING保留，Main判整体PARTIAL。8→4是59/60两个场的实际源码receipt数、12→7是模型请求增量，不能冒受控性能benchmark；本场三个turn约6.618/4.093/5.098s。前2个receipt直接file node且shown命名客户端/route，第三坐标guard，第四下游weather.js仍仅空header，未认领其内容或成功率；无新cap3日志。该场没有可见DSML但没有实际触发dsml_filtered的证明，DSML触发分支/诚实fallback仍属SOURCE/OFFLINE，不能据一次无泄漏宣称所有provider协议已解决。

实际新失败证据：第2/3轮都停在 |lat，中央host.log 92433/92449（2026-10-15 11:40:46/51）分别明确“检测到第二个 | 字符，截断输出”。现_streaming.py 1475–1482和1693–1700按累计第2个竖线无条件截断，和raw两轮事件终态吻合；DSML filter逐字输入“仅当 |lat| <= 90 且 |lon| <= 180，才过范围校验。”可完整保留，不能把竖线误杀说成DSML修复已解。下一52先查该旧围栏目的/调用与相关测试，交付数学绝对值、代码 ||、正常教学不截且保留必要边界的最小修改，先离线、不重试当前付费场。两句简短和HTTP条件过断言仍需后续，不从本场截断推原模型完整后缀内容。

没有本轮Native/设备播放/真人通过，不改既有59 FAIL/PARTIAL。固定中文失败提示和未闭合/未知DSML的保守抑制都有支持范围限制；无provider重试、工具执行fallback或工具轮数增加。当前无live宿主/自有listener，账本不重置。
