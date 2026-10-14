# 阶段十六Native observer窄审

日期：2026-10-14。已完整承接contract/plan/status/blockers的阶段十五发布记录：e34c2f9、Goal active，Main记录610/58/0，不重置账本；必要输出约4%与禁止所有mic/capture/loopback仍分开。本轮仅只读 `scripts/neko_native_telemetry.py`、`scripts/test_neko_native_telemetry.py`，仅新增本报告。不执行测试、浏览器、服务、API、Native、音频或进程清理，不读取用户DB，不新增Agent。采用ponytail-review的具体可复现缺陷标准，不扩到controller/server或全仓。

## 当前改动与结论

本改动把观察目标固定到显式task debug-port返回的单一已知root pet页面，不再根据audio模块可用性从多个renderer挑选。此前两个chat模板也加载audio模块，因此ready chat不能证明它是固定PCM输入的控制页面。

`NativeTelemetry.attach`（当前源行75–99）只请求 `127.0.0.1:<port>/json/list`，关闭环境proxy；候选必须type page、hostname为localhost/127.0.0.1、port48911且URL path恰为 `/`。root数量0或大于1在任何CDP connect之前抛出identity unresolved。唯一root仍须socketReady=1及audioPlaybackAvailable成立；失败保留这两个诊断字段并抛错，不对 `/chat` 或 `/chat_full` 重试。已建立的CDP socket在probe/INSTALL异常及取消等BaseException路径被close后重新抛出。

这是 **已知任务host48911/root pet的限定支持**。它依赖调用方提供本次Native独占debug-port；URL过滤本身不证明debug-port的进程creation-time ownership，也不是任意Native版本/任意端口或任意个人Chrome的授权。页面readiness不代表server lease准入、合法fixed ticket、provider收到PCM或device播放。未来root布局/URL改变应明确适配或拒绝，不能恢复chat fallback来掩盖未知owner。

本轮限定源码 **SOURCE REVIEW：无新增具体阻断项**。先前root不ready仍选ready chat的错误选择路径已从当前attach移除。

## IPC与cleanup边界

`command/_command_locked/evaluate`（源行101–120）仍使用单observer asyncio lock、递增request id及匹配id后返回，通知不会被当该请求结果。协议error和Runtime exceptionDetails都抛出，attach异常路径关闭该observer的CDP socket。成功返回后沿既有close finally关闭socket；本轮没有新增第二条连接或全局共享observer。

观察INSTALL仍仅挂该页面socket事件、发送元数据计数和播放状态监听，不调用捕获API；它不提升lease owner、不设isRecording、不猜generation、不放宽server。fixed control/PCM仍要求registered id并委托现有appAudioCapture controller；没有重新引入raw appState.socket fallback。INSTALL的页面监听与socket.send包装是既有观察功能，close清timer/CDP并不声称还原页面所有监听；受控task renderer由原owned Native生命周期清理。本报告不据此承诺任意长寿命用户renderer的无痕附着/卸载。

## 证据范围及待补负例

当前已读4个测试源码：不ready pet/ready chat拒绝fallback且仅连接pet一次并close；fixed control仅委托registered source且拒denial；并发CDP id/notification过滤；INSTALL/SNAPSHOT语法和无mic调用。Main报告先复现旧fallback失败，再当前4项通过。本 Agent未运行这些测试，结论分别标为SOURCE REVIEW及 **Main提供的OFFLINE4**，不认领实际Native/runtime/model/device/human。

Main准备补单一ready pet、0/ambiguous/foreign目标和异常关闭socket负例；此处先保持待补，不把已有不ready测试外推为所有分支已执行。服务端sanitized诊断不在当前scope，需另行明确授权后再审。阶段十五实际root证据是Main既有UI记录，不是本轮新增设备验收。

报告冻结。唯一改动为本文件，原controller/server围栏、生产文件、测试、manifest及账本未动。

## 新增负例记录关闭

仅精确只读当前 `test_neko_native_telemetry.py` 新增测试：唯一ready pet与ready chat并列且chat排在前面，连接仍必须选pet；INSTALL抛RuntimeError时原pet socket必须close一次；零root、两个合法root、foreign hostname及wrong host port必须抛identity unresolved且connect未调用。原pet未ready/chat已ready用例仍断言仅连接pet一次、关闭pet且不关闭/连接chat。CDP ids/notifications、registered controller及JS表达式旧3例保持。

Main报告该模块 **OFFLINE6实际通过**，本 Agent仅核测试与断言、没有执行。前段待补的唯一ready pet、0/ambiguous/foreign及INSTALL异常cleanup负例记录现关闭；取消/其他BaseException分支仍只有现有源码catch证据，未把RuntimeError用例冒称取消实测。本次没有新审Source/capture、controller/server或实际Native，不新增runtime/model/device/human结论。报告最终冻结。
