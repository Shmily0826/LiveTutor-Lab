# 阶段十三：无外部请求控制诊断与局部转向

沿用bargein-autocheck-20261012，当前DS594/2000、app58/null、tech0/0。Main实现 --offline-egress：本场relay在_spend前拒绝所有外部CONNECT/absolute HTTP，返回NEKO_EGRESS_OFFLINE；不更改共享预算/计数，不把服务额度设零后重置。actual socketpair协议2 PASS：CONNECT和HTTP没有spend/tunnel/forward调用、原ledger bytes完全不变；普通路径原accounting保留。该开关范围是这个relay，不声称系统全网络断开。

新控制诊断脚本只尝试guarded Native和固定来源控制，明文禁止自身发送start_session/PCM；--api-budget0、offline relay、同一2000/app unlimited/tech0 ledger。需要必要speaker权限但不调用麦克风/虚拟输入或回环，不调系统音量；本场没有任何模型音频输出。Source CLI和task窗口仍在本项目隔离范围，不加载原用户daily历史。

28用全新task control-only store，Native窗口launch后没有ready playback socket，停止并清理；capture renderer receipt未取得，不能借别场宣称此新store通过。29改为既有recheck21隔离store并对同一已启动Native observer readiness做有界poll，发生TimeoutError（观察通道超时）；最后停止并清理。两个raw report都finalized且ledger_bytes_unchanged=true，DS594/app58/tech0完全没增。未重新播放整WAV，没有用paid CONNECT诊断，没有改写27明确control reject。

28/29没有捕获到新的lease事实，所以仍不能唯一归因27 invalid_or_stale_control。两个已结束process的raw证据保留；不能把一次DevTools观察超时当provider自然停顿修复或系统麦克风安全证明。既有25–27 guard proof仍只覆盖其具体Native场。

脚本只对本任务分配debug port观察自己的Native，不查询既有Chrome/tab、不安装Playwright；全局web-inspector只执行help查询，没有打开外部网站或认证。后续需要具体观察通道恢复方案或actual frontend-ASR离线联通，不能直接猜大generation、忽略控制拒绝或用fake捕获回退。

Main现在按contract局部转向C真实总结焦点：只复用旧task-store错题/旧rows，确认当前metadata后，追加有标记的中性teacher-window离线夹具，再一次model summary；原QA/question/history不清空、不改写、不拷贝原用户DB。该夹具用于检验较早QA被prior8挤出后的引用，不冒充真实连续教学/human证明。最终10–20分钟真人集中体验仍pending，麦克风等明确准备好了。

后续C31已真实完成，详见summary-anchor-model报告；当前同一账本为DS595/2000、app58/null、tech0/0，增加的1次仅来自该summary，不归28/29诊断。

窄审发现offline constructor在缺失、坏JSON或不同round时可能先persist而重置计数。Main已改为offline无法resume立即拒绝，在persist/socket创建之前退出；追加三个负例逐bytes核原文件或原缺失状态保持。Root actual relay现在3项通过（2项原协议/普通路径加1项三种异常账本），review已确认SOURCE REVIEW CLOSED。正常非offline路径不扩改，shared ledger没有被这些临时测试写入。
