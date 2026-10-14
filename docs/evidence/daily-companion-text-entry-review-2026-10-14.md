# 阶段十五可见text-only入口窄审

日期：2026-10-14。先完整读取contract/plan/status/blockers当前阶段十四记录：Goal active，ledger Main记录610/2000、app58/null、tech0；最新权限允许必要约4%输出，仍不采物理/虚拟麦克风、不回环、不调音量。本輪不操作账本、不读取用户DB。唯一写入为本报告，没有运行测试、服务、API、浏览器、Native或设备，没有新增Agent。

限定读取 `neko_tutor_start.py`、host新text-only分支、Native text/owned退出相关片段、`neko_output_only_runtime.py`、Daily text/Voice cmd。Main尚在准备实际task-store离线UI和新测试，本报告不认领任何新UI/设备通过。

## P2：退出尚未全部绑定本次owned process身份

`neko_tutor_start.py` finally仍在launcher.poll为None时调用通用host `--stop`。host stop读共享neko-desktop-host.pid、对当前48916发送stop，再按pid taskkill；它没有核这份PID文件/当前端口属于本次launcher的子host。原host child退出/PID复用或新owner替换共享pidfile时，本轮launcher仍存活不能证明它有结束新进程的权利。

Native `shutdown` 同样只从outcome或全局PID_FILE拿数字PID就taskkill。长达四小时的文字场用户先关闭Native，PID后来复用，终于cleanup就可能杀无关进程。launch发现“启动后新出现同名frozen backend”也不能单凭全系统前后PID差证明是本轮descendant；不应杀同时独立启动的同名进程。

最小修法：复用已经验证的owned host停止器/本次Popen后代与creation-time身份。Native outcome/PID记录绑定本次root实例和creation-time，退出/复用拒绝；fallback frozen backend只能清本次已证明的descendant。Browser已有PID+creation-time比对，不应在host/Native退回数字PID。新增负例需证明新owner/PID复用/同时独立同名进程不被停止。本问题已即时交Main，首版待修；不是要求全OS审计。

## P2：voice组合会丢失offline标志

launcher先把 `--offline-egress` append到voice_extra，随后if args.voice将voice_extra整个替换成voice/Core free参数，offline被丢弃。当前任务mixed-audio gate拒绝旧voice路径，所以此次文字场不会触发；但合法 `--voice --offline-egress` 的明示离线语义被破坏，不能声称该组合仍受新offline Sink保护。

最小修法：保留原list并appendvoice参数，或把offline append放在voice分支后；补实际命令构造负例，不能通过取消旧voice权限gate来测试。本问题已消息交Main，首版待修。

## Mode propagation确认

- Daily cmd现在显式--text-only；Voice另入口仍显式--voice及原预算/round。text与voice/fake audio_input在launcher parse后先拒绝，host也拒绝text与voice/output-only或非source组合；不能用speaker授权推导capture授权。
- text_extra传--text-only到source host，launcher子env强制NEKO_TASK_SILENT=1；host显式NEKO_TEXT_ONLY=1、NEKO_OUTPUT_ONLY=0、NEKO_DEV_AUDIO_ALLOW空。无voice分支不会选free realtime route，原text/source gate仍核指纹。文字路径不调用speaker permission是设计，不能据此放行混合audio路径。
- host main/runtime复用原8捕获API拒绝库和单blob fingerprint；text_mode在installer成功后、document.write原应用之前设置readonly __NEKO_TEXT_ONLY__。失败原HTML仍inert，显示拒绝，而非独立script throw后放行app。header确为text-only、HTML no-store和microphone/camera/display-capture拒绝。
- Study plugin-code static入口部署时也用同protected_html封装，先拷当前canonical index再包；不叠包旧guard，不复制用户学习data。该static页不是main-server middleware响应，因此不能假称它天然具有main-server同一套SHA/no-store/Permissions-Policy header，实际served入口需由Main UI检查证明。

## Native/Chrome和缓存边界

Native text分支在写配置/Popen前严格核当前host text-only header、capture库SHA、installer字串和text marker，不调用speaker/mixed permission；非None fake输入及output-only组合拒绝。使用独立稳定 `text-only-userdata`，配置apiBaseUrl明确本机source host；--mute-audio、不加autoplay/fake-device/file/UI-capture flags。profile稳定是为了日常设置接续，不能把“新mode名”当实际清过所有旧缓存的证明。

launcher text把Chrome profile切到store/browser/text-profile，与voice/browser/profile和用户Chrome隔离；命令--mute-audio且关闭sync/background/network component等。main准备后核host text header再打开；browser helper本身不是完整保护入口，text_only=True不单独证明任意URL受bootstrap保护。学习surface是既有受控只读材料，不从本报告扩大到任意网站或OS权限。

main-server页面no-store，Native/Chrome独立profile减小旧未保护页复用风险；Study static缓存/响应、Native实际遵从userdata参数、第二次启动仍加载当前guard，需要Main一次task-store UI场逐入口证明。不能凭预检header或mute参数认领真实前端capture API已装，也不能凭mute就声称任何音频SDK从未初始化。文案隐藏已知mic buttons是便捷层，硬API拒绝才是捕获防线；新React/iframe/worker realm若出现仍须另行核安装。

## 普通路径与验证范围

未选text的Native/product browser继续原audio permission gate；output-only仍走独立speaker许可，不把audio_allowed改true。text正文title/状态明示文字/麦克风关闭；course配置、材料、长期语言存储沿原store，原daily不重置。题/历史接续继承C33限定证据，不因这个入口改动重跑旧paid场。

本报告只有 **SOURCE REVIEW，owned退出与offline组合两类P2待修**。Main接下来必要测试应核text模式冲突、命令传播、guard在app前、安装失败不加载app、served Study入口/current SHA、第二次profile加载、只owned teardown与旧voice Gate。真实task-store UI/用户daily/human未执行，分别保持pending。修复后只精确补关闭确认，不重扫全仓，不用全Goal其他未完成项否定本阶段源码交付。报告冻结。

## 原两类P2修复复核（最新）

Main已修复原问题。本 Agent精确只读当前调用链：launcher在本次Popen后记录pid+kernel creation-time，finally只调用stop_owned_tree(该record)和wait，不读取共享host pidfile或发送全局stop。该helper复用live PID+creation-time比对，调用/T覆盖本次root后代，不依赖psutil。Native outcome及PID文件带created_at；shutdown仅停止同实例，只有saved record的pid/created_at与本次owner一致才unlink，不删新owner记录。frozen检测改成当前已验证root的parent链后代，不再根据全系统同名进程差集直接taskkill。

host_options只在既有list上append text/offline/voice/round/vision，voice不再覆盖offline。原两类 **SOURCE REVIEW CLOSED**。Main报告新text8检查通过，包括真实stranger PID stale/replaced记录不误停/删、非后代同名进程排除与组合参数保留；本 Agent未重跑。真实parent/child launcher检查仍由Main后续执行，不能由本段替代设备/UI。

## 新P2：一个owned停止失败会跳过其他资源退出

精确复核调用边界发现：stop_owned_tree会因taskkill错误/等待后仍存活抛错，而main finally对avatar.shutdown、host stop_owned_tree/launcher.wait没有独立异常隔离。Native停止失败会跳过仍属本次的host/browser/lesson/log关闭；host停止失败也会跳过browser等。原browser分支有局部catch，但它不会被执行。新增更严格停止器不能使其他owned资源在一次失败后全部留下。

最小修法：每个owned资源分别try、收集明确cleanup error，继续清其他owned资源；最后汇报/raise错误，不能把停止失败忽略或谎报全部stopped。使用fake Native shutdown抛错、host stop/wait抛错的定向负例，证明其余owned browser/lesson/log仍尝试关闭，不需要设备或API。该新P2已即时消息交Main，首版待修；仅同原调用边界发现，没有扩大mode/OS审计。

此次仅追加报告，没有执行任何进程/服务/API/浏览器/设备或账本操作。原text mode与guard结论保持，报告再次冻结等待Main精确补证。

## Cleanup P2及CSP增量关闭（最终精确复核）

精确只读 `neko_tutor_start.py` 当前 `cleanup_resources`：surface shutdown/server_close、Native shutdown、host stop/wait、browser ownership记录/停止、lesson terminate各自通过独立attempt执行并汇总错误；一个action抛错不跳过后续action。main finally在该汇总后继续关闭launcher输出，最终stopped按cleanup_errors是否为空计算，非空返回1，不再固定宣称全部停止。原新增cleanup P2 **SOURCE REVIEW CLOSED**，本轮限定调用边界未发现新具体阻断项。

精确只读 `neko_output_only_runtime.py`：text mode收尾不再写inline style，改为对四个已知mic button设置hidden；title suffix先检查再添加，MutationObserver在documentElement的childList/subtree/characterData变化后重做title/已知button投影，避免title自身更新形成循环。capture installer和readonly text flag仍在原HTML加载之前，hidden只是可见性层，不替代8API硬拒绝。该修改解决已知inline CSS CSP触发点；本报告不把它扩大为任意应用、iframe或任意hidden属性变化的保证。

Main报告新text9离线检查通过，包含Native退出抛错时其余host/browser/lesson仍被尝试清理。Main另执行两场静音offline真实text入口及同task profile重启：第二场cleanup_errors为空、端口释放、610/58/0不变；首场曾出现Study inline CSS CSP错误，修复后由global web inspector复查动态title正确且console/page/error为零；两Native renderer实际8API installed、textOnly true、chat input visible、mic false。这些均为 **Main提供的离线/实际UI证据**，本 Agent没有运行或独立复现，也不借此认领模型、声音设备或真人体验通过。

本轮只追加此报告，未启动服务/浏览器/Native/设备，未调用API或操作账本。报告冻结，阶段范围和既有历史发现保留。

最终补充：只读核到host `apply_voice_host_patch` 在各host tree调用pinned capture patch，source启动随后仍执行patch replay再verify_source_audio_gate；当前入口不再仅依赖预先手工复制runtime。未知源拒绝与幂等6项、startup replay/gate实际运行结果由Main提供，本 Agent未执行。cleanup错误时exit1的源码结论保持。原始CSP、连接失败和即时空白截图不被本段追溯改成通过；修后UI证明仍归Main及其阶段记录。未发现此次限定修改的新增具体阻断，报告最终冻结。
