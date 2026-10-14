# 阶段十八：首次语音就绪与受保护固定输入

承接 eadc692 阶段十七，前一 Goal turn 为 progress：发布17文件，真实本地控制及SDK/SQLite/Browser接续证据已改变下一步，不是无进展等待。完整 contract 保持原SHA；最新权限为必要约4%扬声器，不修改音量，不初始化或使用房间/物理/虚拟mic、任何捕获或回环。既有两Agent中仅screen做窄审，Main安排外部会话与账本。

## 就绪修复与审查

旧量具在输出专用 Native launch 后固定4秒，仅一次 attach；实际先前28notready/29timeout以及phase17cold root证明固定时间不是可靠条件。新增同task/debugport `attach_when_ready`：只有0known root/loading、本地connection-refused或准备阶段timeout等待；ambiguous、foreign web root、安装失败、其他网络/协议错误立即停止。ordinary模式沿原4秒/单attach，没有provider重连或新窗口。

首版 Native11离线过，但独立审查找到P2：同步HTTP阻塞event loop及close无限等待使35秒非硬界限；INSTALL Timeout被当loading重试。现本地HTTP读移to_thread，并传实际剩余期限/不超过5秒底层socket timeout；probe/CDP/INSTALL分别受剩余预算，INSTALL超时转明确RuntimeError停止；失败close独立2秒，超时aborttransport。准备期限35秒与close清理预算独立记录，取消HTTP await不等于线程已经停止，不外推OS全网络或任意恶意HTTP响应界限。

Main Native14离线通过：同端口等待、身份/安装/其他网络不重试、deadline退出、实际blocking mock HTTP不阻塞主loop、INSTALL timeout仅一次且close、hungclose2秒后abort；原socket/ticket/correlation与无mic测试保持。首个5毫秒期限测试误以为Windows timer必精确只poll1，实际poll2仍合时限；改为验证实际elapsed<0.2秒及始终同端口，产品未为测试改变等待行为。

output-only语音量具复用已验证 `cleanup_resources`，记录Popen创建时间；surface/avatar/host清理各自独立，错误写report且退出非0。ordinary清理路径保持。独立精确复审确认上述P2 **SOURCE CLOSED**，Native14为Main执行的OFFLINE证据，实际强制取消负例未执行，不扩大为任意网络硬超时保证。

## 有界真实场准备

账本实际 bargein-autocheck-20261012：DS610/2000、app58/null、tech0/0，不重置、不换provider。准备最多一场voice34，复用已有isolated `neko-daily-silent-vision-20261014-recheck21` 图片材料及existing `daily-picture-constraints-single-utterance-20261014.wav`；当前材料/prefs先经真实SDK核对，不重新提交图/造题，不读取原daily学习历史。output-only capture guard先装后才固定票/会话，固定WAV只内存读取/WS，没有fake input或回环。

该场目的是新版合法固定输入/实际ASR、Study工具、约束输出与时间分布，不重复既有普通human打断批次。phrase/speech gate均为明确opt-in，default OFF保持。观察到拒绝、断连、限流或超时立即停止，不blind retry；局部失败转A/C/D/E/F。网络PCM、Native播放状态与物理扬声器/真人听感分层记录，不把renderer字段当人耳验收。

## voice34实际结果：准入/DSP通过，语音教学失败

`daily-companion-20261014-output-phrase34.json`保留原始结果：actual宿主与Native receipt installed/captureBlocked=true、fake_silent_input=false；known root固定票id1/core/gen2/socket1、实际session_started，无control/lease/delivery reject。本地2098帧、1006953 samples，WAV SHA6b6182d6...。speech结束wall1791969628.52319、固定输入尾静音结束1791969631.54228，输入提交未早停；end_session+原票release正常。

实际本次server log时间窗口采样已另存私有 `daily-phase18-voice34-review.json`：独立去重RNNoise统计共20130ms输入，unavailable_chunks=0，概率peak1，后期静音peak0；最大pipeline处理13.754ms。因此有**实际server DSP处理**证据，而非仅凭本地send宣称后端收到。上行wire仅三条session.update，没有observed append/transcript/Study教学tool；Native接收binary0、reply空、turn_timeout=true。这不是“慢回答但成功”，而是 **FAIL_NO_ASR_OR_REPLY**，当前自然停顿/语言/教学/输出未通过；未产生可验收的回复PCM，设备播放和human均未证明。

该场正常清理exit0只证明量具执行完：旧逻辑没有把turn_timeout转failure，acceptance其实是FAIL_OR_PARTIAL。原raw不重写，现output-only修为将此期限失败明确记录并exit1；不是将新诊断当新模型PASS。实际修正不安排第二场paid重试。

账本从610/58/0到610/59/0，只有本场一CONNECT，没有DeepSeek调用；原round/budgets保留。exec32767已terminal、cleanup_errors=[]、48911/48916无listener。没有capture device、loopback或音量变化。原daily历史不动，现有isolated recheck21图材料由真实SDK核、未重提图/造题。

## 局部失败后的工作

同次DSP持续工作将下一步收窄到DSP之后的active/epoch/lease/current与activation/Native send/phrase边界；没有足够counts/reason前不猜哪项为根因。下一本地工作使用现有真实方法离线量具与明确default-OFF、无内容/密钥的分层计数；不为加证据重新连接provider，不改安全准入或普通打断。已有source review列出候选drop sites，仅SOURCE判断，不据缺日志下因果结论。

并行完成一次10–20min集中体验文档 `docs/daily-companion-human-experience-2026-10-14.md`：准确默认文字启动命令、A/B返课续题、换图纠正、same-store重启、CodeGraph/受控指示与故障恢复；真人体验/原daily最新版实跑仍pending，output-only声音只Main确认后可选，不构造不存在的用户参数或放开mic补救。局部语音失败不结束整个A–F Goal。
