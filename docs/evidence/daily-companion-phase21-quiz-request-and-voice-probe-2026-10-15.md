# 阶段21：保留出题要求，修正语音观察程序

真人测试中的“只问方向、二选一、最多一句、不公布答案”无法进入后台：study_quiz只有topic/target_weak。现新增本轮request字段，分别透传当前Study图片、显式主题和自适应弱项；保留原图片/课程/session身份和私有答案边界，不写长期偏好。题型prompt要求不得给方向题追加节点列表或整条路径。没有真实材料且未指定主题时，纯格式要求返回MISSING_TEXT，不收费生成假材料题。

Main实际wrapper→entry→prompt→临时SQLite4项通过，包含三路线/无答案字段及hint净化/偏好不变/旧图拒绝/无图或vision关闭的缺材料拒绝；原quiz材料guard12、memory8通过。独立原3项通过并复核新增第4项及空材料P2关闭。三canonical源码LF/hash与原daily插件代码部署一致，未动学习data/config/history。真实模型是否遵循新request、Native是否主动填此字段仍待，不把本地模型stub算真实模型。

## phrase35有限真实结果

阶段20helper部署修复后，Main仅运行一次必要既有固定WAV/输出专用场；原round、同隔离store与既有Sky图，不重复提交图片。8捕获API保护installed，room mic/capture/loopback均false，volume_changed=false，fake input未开。speaker仅用户4%授权；没有设备回环证据或真人声音评价。

真实Native转写→角色study_explain→Study模型→两句English→24 Native PCM。当前picture identity保持，偏好及cfg.language前后相同，最后source_ended、remainingSeconds=0。原raw35仍turn_timeout、exit1和FAIL_OR_PARTIAL，不能追认整体PASS；仅这些子边界有实际证明。phase34无转写/无回复的失败也保留。

语音观察程序有两个可证量具缺陷：持续pong及定期playback receipts更新native_changed，quiet6s永不满足；另把“偏好没有变化”错误写成“必须显式保存zh-CN”，本场是继承默认中文而非显式语言偏好。修为累计binaryFrames/最新有效事件wall的单调进展（忽略心跳/播放receipt，bounded trace滚出旧事件不算新进展）；偏好需两份有效dict、okTrue、实际cfg语言一致且非空，缺观测不能通过。保留ended、55/35s最小观察、6s quiet、inactive、75s超时及异常停止约束。

Main及独立纯AST7项通过，覆盖心跳/播放周期、late text/audio/ASR/failure、bounded500滚出、偏好缺字段/failedok/有效语言变化。对raw35既有事件只读回放，新判据在输入后59.087秒可结束，偏好判据通过；这是recorded-event replay，未重新跑online观察程序，也不覆盖原报告。避免为修量具再耗一次相同模型测试，下一真正集成场核修后实时等待。

原raw35 SHA256 `4ed1c447e8b7ca43ffb5af71bfc99d57c67a755f0e006cc4c6f1dc202ffa48a9`；raw/派生/回放保存在ignored evidence，不发布音频/学习全文/DB。固定WAV SHA256 `6b6182d69b2a0ea0e12cb8bae72be5edee5629abe65f600c2201e16242eeb93d`。

本场观测：speech end→Native转写11.609s；speech end→首PCM21.775s；首PCM→播放schedule0.512s。Study调用到结果约5.5s，结果到首PCM约5.2s（log秒级与精确观察不同，不冒充同精度）。前一段包含本地等待/上传/服务识别，尚未拆清；schedule不是实际扬声器可听起点。接下来按边界优化，不归咎于所有时延都是模型，也不掩盖真人时Main引导慢。

预算：DS668→675（+7），app62→63（+1），tech0/0；bargein-autocheck-20261012不重置。唯一场exec60014已exit1，cleanup_errors=[]，48911/48916/9234/9235无listener，不按旧PID清理复用进程。policy保持mic/capture/loopback=false，speaker=true。

## 后续仍需完成

本轮已定位Native绕过正式评分：工具在场但角色自由口头回复，current held题仍pending。没有修成持久评分，不能用本阶段出题或语音进展代替。下一步权威显式答题路由需固定ASR owner及qid/attempt/course/session，复用原study_answer和DB防重；正式结果回来前避免自由口头评分，保护普通打断与新输入/换课/换题，不从口头评价倒填记录。详见独立human-grading-routing-review。

材料可见性、graded错答纠正/返课重启、语言术语自然停顿及全部A–F继续；最终集中10–20分钟真人验收待核心自动链过。现有Goal不重建/不complete，局部阻塞继续其他项。阶段20已推ae23b1d；本阶段发布SHA另在status记录。
