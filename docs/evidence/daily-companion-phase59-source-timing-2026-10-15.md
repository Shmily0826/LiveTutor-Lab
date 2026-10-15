# 阶段59：源码教学分段计时（源码/离线与只读CLI通过）

用户明确继续，Goal接口active。上一实质阶段交接包b9f75ab已发布，为源码与证据上下文进展；未冒称优化或运行验收。先读完整contract/plan/status/blockers及58暂停点后接续。

范围：针对70场工具9.909秒、源码/上下文未拆4.690秒，加入调用隔离的低内容计时。先用本地真实CodeGraph只读查询和离线调用链验证拆耗时，再决定最小优化。暂不实施推测性的模型路由并发，不删语义/历史/授权边界，不改变模型、供应商或配额算法。

原账本bargein-autocheck-20261012已核888/2000、app79/null、tech0；无预算调整。本阶段不麦克风/capture/loopback或声音，不启动Native。现有脏树/.workbuddy/学习数据与Sky源码保持。后续记录必须区分离线、真实CLI、真实模型和设备/真人层。

## 交付与验证

新增标准库ContextVar调用计时，入口结束/失败/取消均复位；日志仅12位关联编号、阶段名、起点/耗时毫秒及终态，不含问题、源码、路径、token或模型内容。覆盖材料快照、source request、索引同步、版本、inventory、query、记录、surface、上下文、路由与解释。未实施并发/缓存/供应商或协议变更。

31个不同相关离线case通过（原29＋新2），新2覆盖重叠调用各自阶段、不泄漏问答内容，及取消继续传播/不上模型/清空调用trace。首次运行4个failure来自AST隔离夹具缺新依赖和新测试误以为正常工具结果必带ok键；已修夹具与断言，保留产品既有响应形状。最后因日志兼容改为预格式化字符串重跑同31，不重复计数。没有物理设备/真人/新真实模型证据。

5个源码文件精确部署，旧部署先核原manifest SHA并独占备份在raw/evidence/phase59-before，未触学习DB。manifest32/32当前，默认部署31/32直接匹配；唯一index.html是既有protected_html文字/capture保护转换，独立重算期望文本完全一致，不当作源码不一致或移除保护。SourceGate PASS，无宿主启动。

## 有界真实CLI测量

复用69store的现有源码授权，执行真实现工具路径的files/node/git查询；显式不执行sync、记录写入、surface HTTP或模型，也不修改学习材料。不是70场完整重现或速度对照验收。

|请求|总计|git版本|文件清单|源码query|
|---|---:|---:|---:|---:|
|weather_service.dart裸名|2270.812ms|106.940ms|1219.214ms|928.572ms|
|返回的完整索引路径|1029.092ms|77.325ms|不需要|942.502ms|

两个请求的29行evidence SHA一致，当前commit7aae20f。说明本次inventory是约1.22秒的明确额外读取，已知完整路径可避免；不是安全的裸名缓存依据，也不能将全部4.69秒归因CLI或宣称端到端提速。首次裸名仍必须验证唯一性，不能因历史缓存漏掉新增同名文件。

raw只读profile SHA256 fbfb081828fb547fffa89665bfcc9756970bdfb11a994f7c10bf68ef72cecf0e，保留本地，不发源码全文/授权文件。它记录tools源码SHA，调用trace模块后续只改日志格式，不改计时阶段。

## 剩余、账本与下一步

完整工具关键路径尚需在实际教师场读取新计时，尤其sync/上下文/DB/surface；本阶段没有声称拿到这些未测数。优先沿现有静音SDK教学量具做一次必要有界真实验证（不Native、不mic），否则转A/C/E/F独立余项。Claude方案继续作为候选而非已验修复，不等其限额。

原账本实核888/2000、app79/null、tech0，未重置/新增外呼。无新live handle、宿主、设备或音频；原Root脏树/index空/contract原SHA/Sky源码保留。Goal active，完整A–F及最终集中真人体验未完成。

阶段59发布确认：14文件commit/push 5a78ec0c12b1f13c7c2fd559b1548970770724d9，远端exact、publisher clean、master仍f1e8f3f5605659f0526e43bc3b85c60ae46c85fb，Root index空。发布仅源码/测试/文档，不含raw、DB、音频、备份或密钥。31为同组不同case，取消断言补强后只重跑该1，不重复计数。原888/79/0，无live。下一60复用原静音SDK callback与owned清理/超时量具读取真实完整计时；先核支持，不重开Native70、不开mic，不等待Claude。完整A–F/Goal active。
