# 真人体验前的安全检查点

用户要求收尾当前工作后暂停自动开发，先集中真人测试，再继续Goal。阶段十九已发布`0cb1045147abf163aba8f35ba527c083c986ab19`。阶段二十当前修复尚未commit/push，保留Root原脏工作树及空index，不把未发布源码说成完整声音交付。

已确定voice34具体路由失败：当场22:20:10–30宿主日志反复`No module named 'neko_phrase_input_transport'`；实际launcher cwd中两个phrase模块均无法定位。本地scripts入口将模块放入查找路径，旧manifest只校Root源文件，没有实际部署。

当前修复：新`scripts/neko_runtime_helpers.py`按固定两个文件/manifest指纹部署到两个host根；拒绝未知代码、符号链接/逃逸host或source；exclusive `xb`创建防并发覆盖，只接受同字节并发winner。主host的deploy及source/deployed字节核验、`-E -B`实际cwd child import在任何应用/设备/provider启动前执行。两个helper仅stdlib。

Main 9项临时实际子进程/import/拒绝/竞态/idempotence检查通过；独立审查已闭合8项时的exclusive竞态P2，之后Main又加root containment与第9负例；恢复开发后先核最后增量，再publish。Main已实际调用现有补丁链部署到`benchmarks/raw/neko-product-host`与`candidates/N.E.K.O`，实际SourceGate和launcher cwd子进程导入均PASS，**没有启动服务/应用、联网或音频设备**。独立报告里的“未部署”是其检查时历史状态，不是当前Main结果。

新/改文件仅：`scripts/neko_runtime_helpers.py`、`scripts/test_neko_runtime_helpers.py`、`scripts/neko_desktop_tutor_host.py`和host manifest及本阶段证据/四记录。诊断helper和生产counts-hook未改；根据明确日志先修部署，不为观察而扩大改动。没有voice35或新CONNECT，账本610/2000、app59/null、tech0/0沿用不重置；34原失败不回写。

当前无自有host/Native/browser/online场。用户最新明确授权**本次在场真人测试**使用麦克风和扬声器，取代本次会话的旧mic禁令；不是后续无人开发的永久授权。保持用户约4%扬声器，不调音量、不启loopback，不采未授权camera。测试结束恢复mic/capture禁止的开发边界。测试前/后预算与进程、用户反馈、实际成功/失败需独立记录。

自动Goal按用户要求暂停；后续明确继续后从contract/plan/status/blockers接续，保原A–F范围。真人测试是单独的当前用户请求，不自动恢复后台Goal。未完成：真实模型到识别/回复/声音链、自然停顿/语言术语、更宽graded跨课及集中体验记录；不得据部署/9离线项称provider或human通过。
