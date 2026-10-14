# 阶段48：任务Chrome翻译偏好设计独立审查

本轮仅只读当前`neko_tutor_start.py`相关Chrome命令、profile选择、owned存活检查与现有启动时序；新增本报告，不改源码/测试/配置/47报告/共享记录。未运行浏览器、应用、API、设备或预算操作。新helper及测试尚未冻结，以下为设计边界而非实现通过。

## 当前事实与最小插入点

57已在任务Chrome实际带`--disable-features=MediaRouter,Translate`时仍出现翻译弹窗，46的56单场无弹窗不能外推稳定修复。本阶段只准备本任务profile的translate.enabled偏好，保留feature flag与现有声音/capture围栏，不涉及个人Chrome、系统policy或语言课程偏好。

当前launcher在task store下选择browser/text-profile或browser/profile，chrome_command显式传--user-data-dir。browser_args建立后，现有BROWSER_OWNER_FILE与kernel创建时间核验若发现owned browser仍活则拒绝。建议新准备步骤仅在browser_args存在、该检查通过后执行，并位于所有Chrome Popen之前；无Study/Surface浏览器时不触碰任何profile。不要将helper藏入chrome_command纯命令构造而使单测或preflight提前写配置。

Main提出Chromium官方translate_pref_names.h将kOfferTranslateEnabled映射为translate.enabled；本Agent此次没有访问外部文档，仅据该已提供出处审查本地接线方案，不把键名或单次写入当实际弹窗已解决。

## 必要数据与文件边界

- profile、Default、Preferences及临时文件的最终解析位置均需保持在本项目RAW及所选profile内；拒绝个人profile、路径逃逸、symlink/reparse异常。未存在目录也要在创建前核祖先解析位置，不能先mkdir/write再判断。Preferences若存在应为普通文件，不以目录/坏链接当“缺失”。
- 已有JSON必须是dict；若translate键存在也必须为dict，不接受list/null/字符串并自行重置。失败应让启动明确拒绝，原Preferences逐byte不变；“保存原件”不能通过删除原配置或生成默认空对象实现，也不应打印或输出完整偏好数据。
- 仅变更translate.enabled，保留其他根键及translate内其他键。已有值严格`is False`时原bytes不写，保留原格式与mtime；数字0不能混同JSON false。新profile/缺文件可创建最小合法对象，但不能因此重置原浏览器配置或学习数据。
- 同目录唯一临时文件使用exclusive创建；成功写完整JSON后再replace，异常只清理本次确实创建且仍归属本次的temp。预存在temp、write失败、replace失败不应覆盖未知文件或清理别人的文件。若使用flush/fsync，它只提供写入完成边界，不是并发锁或崩溃后所有存储保证。

## 并发与ownership限制

os.replace使目标文件替换完整，不会自动合并读取之后另一writer的修改。现有owned alive检查不等于持续持有profile排他锁；不能把check→read→replace宣称为并发安全，更不能仅凭相同路径当同一文件身份。尤其“读时缺失、replace前另进程创建Preferences”不能默认为授权覆盖未知winner。

最小工作范围应明确为已关闭、仅任务launcher管理的profile；若实现需要对外部并发修改做安全承诺，必须给可复现的并发负例与真实保护，否则将其留作限制，不能声称任意同时修改均保留。无需为本次偏好建立通用配置系统；也不应为了设一个偏好结束未归属任务的Chrome。

## 最少定向验收

新temp profile的最小Preferences正确；已有其他根/translate键保持；已有严格false原bytes/mtime不动；非dict根/translate、坏JSON、链接/外部路径拒绝且原bytes保持；exclusive temp冲突和写/replace失败不覆盖/误删文件。还需核main时序：live owned先拒、无browser无副作用、helper失败在Chrome Popen之前终止，mute/profile/owner清理原契约不变。测试不得启动真实Chrome或设备。

冻结实现与必要离线后，Main可用唯一任务Chrome实际观察是否仍弹翻译；一次无弹窗只能证明该场，原57失败保留。实际profile写入/生效、模型或声音/human验收分别记录，不重复未变图片/课程/几何基线。本设计审查不预批未知实现；当前无已实施代码可判断的新具体P1/P2，等待Main冻结增量。

## 冻结实现与独立六项离线复审

实读SHA吻合：`neko_tutor_start.py`为 `70712982e36a53256da0de68fa1b21502c1bdeea1601b2c0c56427627e7178d0`；`test_neko_browser_preferences.py`为 `bdf66f6ba87a239b0934be54c140a5c0d646e6d259055356affff0b9e9d817e1`。独立使用既有Source venv `python -X utf8 -B scripts/test_neko_browser_preferences.py`，6项PASS，0.038s；只有RAW内TemporaryDirectory、stdlib文件操作和mock边界，没有服务或设备。

helper先resolve RAW/profile/Preferences/temp并核RAW仍在ROOT、profile严格在RAW内、prefs/temp在profile内，再读文件或mkdir。它提供resolved containment，不能将此描述成所有路径组件均持有句柄、拒绝全部内链或抗并发重定向。实际调用只用本launcher的BROWSER_PROFILE，没有个人Chrome目录发现或系统policy写入。

已存在文件JSON须根dict及translate dict，读取/编码/JSON异常均拒启动且原件保持；仅`enabled is False`时不写。否则保留其余根键/translate子键，只设enabled=false。固定同目录temp用exclusive x创建，不覆盖预存temp；正常写完后os.replace目标，原feature flag/mute/profile命令不变。没有输出偏好内容、token、声音或捕获初始化。

调用点确在browser_args存在且原live owned检查通过之后，位于host/Chrome Popen之前。第六项实际写当前测试进程PID及kernel creation time作为owned记录，执行main并确认prepare未调用、Prefs原bytes保持；host/端口边界为mock，不是实际启动了应用。另五项覆盖fresh最小对象、未知设置保留及第二次精确bytes不变、损坏/错误shape/非UTF8不写、RAW外拒绝与预存temp保留、replace失败时原件不变。

实现明确保留失败temp，不做自动清理或覆盖；因此replace失败后下次准备会因该temp存在拒绝，需人工审阅这份任务内残留后恢复。这是fail-closed恢复限制，不应声称失败后自动重试或自动恢复。没有profile并发锁/修改合并，也没有承诺外部writer或崩溃时的并发/持久化保证；本次按已关闭且由本launcher管理的任务profile契约审查，不据os.replace宣称这些保证。

本次窄审未见新具体P1/P2，可交Main执行唯一58实际任务profile验证；尚未得到偏好在Chrome实际生效、没有翻译popup的新运行证据。Main另报window4/text9通过，本Agent没有重复其未变套件，也未触碰54真实profile或任何用户DB。原57失败仍保留，所有A–F整体未完成；本报告追加后冻结。

## 最终58原件独立只读收尾

原件`daily-companion-browser-preferences58.json` SHA实核 `29eac32101b8979f37c847629b46ee2385315e6df4fa301de94d599064886b3d`。start/test两源SHA仍为前节70712982…与bdf66f6b…，未发生审后漂移。

底层window_observations有两个OS可见窗快照，时间1792015780.1419823与1792015785.8606722，相隔5.718690秒。两次均只有“N.E.K.O · 学习材料”与Study文字模式两个1050×832预期主窗，无Translate辅助窗；启动观测及terminal中的preference_translate_enabled均严格false。actual status非error且ok=true，material为daily-window-fixture54-A、study_store_snapshot/image，原forward PNG SHA `057d5bac5ae440dfa0d3269f5138f1188fa182bc0fce81435676c6a4caa65dcc`相同。五项checks与底层信息一致，支持Main本次同54任务profile修后无翻译弹窗、同课同图的窄运行证据。

exec_session=61267，Enter退出exec_exit=0、cleanup_errors=[]、browser_owned_alive=[]、Native40952不存活，48911/48916/9234/52264均无listener。paid allowed=[]/direct=[]，社区请求被拒，原round保持DS835/app78/tech0，post58_source_gate=PASS，audio/capture/loopback=false。本Agent仅核保存原件与源码hash，没有重新启动/查询服务、浏览器、设备、预算或用户库。

阶段48审查关闭并冻结，未发现新具体P1/P2。58是唯一一场、两次短间隔快照，不足以保证所有Chrome或未来每次启动永无popup；55/57原false不修改。本场没有重新验证真实task Chrome点击重开、全部异步Ready、pointer物理渲染、模型、声音或human体验，不扩为整个A/E或Goal完成。
