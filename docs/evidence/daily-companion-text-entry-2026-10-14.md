# 阶段十五：可见日常文字入口

承接605deff/原contract，不重建Goal、账本或用户历史。新增源码尚待本阶段提交。最新许可仅允许必要约4%扬声器，仍无mic/capture/loopback许可；本阶段实际全程静音、offline-egress、无外部模型请求或设备采集。

## 交付

Daily cmd默认text-only；Voice cmd独立保留旧权限gate。host安装受指纹核验的早期捕获保护，原HTML在8API保护安装前保持inert，text flag readonly。Study静态入口只在task部署封装，canonical不改；主服务器另有no-store/SHA/Permissions-Policy，不冒称Study拥有相同headers。Native预核当前保护、稳定专用text userdata、mute；Chrome专用text-profile/mute，无fake capture flags；纯文字启动不导入ASR。未知设置保留，损坏宿主/Native配置拒绝覆盖。启动链重放pinned bootstrap/helper并再核source gate，不能依赖开发者先手工复制helper。

退出只按本次root PID+creation-time身份清后代，不使用共享host全局stop。Native不按全系统新出现同名backend推定owner，仅当前后代；不删除替换后的owner文件。各资源独立关闭并汇总错误，任何失败都使stopped=false/失败退出，不让Native失败跳过host/browser。voice与offline组合保持明示offline。窄审原两类P2及异常隔离/CSP源修复已关闭，精确复核未发现新具体阻断；独立review只认源码，实际运行证据归Main。

## 实际证据与失败

- SOURCE/OFFLINE：text9、原launcher11、output-only6通过，真实parent/child tree关闭与stranger stale identity存活；异常avatar cleanup仍尝试其他资源。canonical/损坏配置保留用temp store，非原用户数据。source gate先因新runtime指纹不符拒绝，精确核两个树与canonical bytes后更新仅对应manifest项，再通过；没有取消gate。
- ACTUAL HOST/NATIVE/UI：同fresh task store `neko-daily-text-entry-20261014` 两次有界实际主入口，第二次沿用同text profile；原生日志可见窗口、同一宿主attach。现有Native E2E transport只连接本次明确9231端口，本机48911 task渲染器，未查询用户Chrome。`/chat_full`真实composer可见；pet及chat两个renderer的textOnly/captureBlocked true、8API installer installed、mic控件不可见，真实截图Main已检查。不是输入发问/模型或avatar动画完整证明。
- Global web-inspector实际Study页面HTTP200并显示图片/课程入口。首场inline CSS被CSP拒绝，保留失败；改为hidden属性和MutationObserver适配动态控件/title，第二场title明确文字模式、console/page/failed requests零、无横向整页溢出。该工具DOMContentLoaded时还显示Refreshing，不能冒称完整后台state已刷新或操作通过。chat网页首个即时截图空白同样只记加载早期，Native等待composer提供后续可用界面证据。
- 第一次Native观察器调用早于启动，WinError10061，未取得证据；宿主/Native实际就绪后观察成功。检查器现有界等待35s且保存FAIL范围，不做无限重试。未增加paid场。
- 两场退出均stopped true，第二场cleanup_errors=[]；48911/48916/9231无listener，所有本场自有host/Native/browser已停止。没有用户daily刷新、麦克风、音频播放/采集/回环/音量操作。账本仍bargein-autocheck-20261012，DeepSeek610/2000、app58/null、tech0/0。

本地原始证据：`benchmarks/raw/evidence/daily-text-entry-tools-20261014.json`、`daily-text-entry-native-20261014.json/.png`、task launcher.log及本场host/native日志。均不公开Git；公开报告不含学习DB/history/keys/录音。

发布候选复核：13文件allowlist、AST/密钥模式/contract原hash/Root index检查。candidate source复用既有隔离runtime依赖，首检缺ignored APP/base Git夹具且旧launcher测试只查找lesson.terminate源码文字而失败；补准确runtime路径，旧测试改为实际创建并关闭测试子进程。候选text9+launcher11+output-only6共26通过。不是把缺夹具或旧源码字串失败写成产品运行故障，也没有取消测试/gate。

## 剩余与下一步

本阶段是SOURCE/OFFLINE+实际限定入口/UI，model/实际声音/human未新增通过。提交检查后的必要文件到codex分支；不merge/force/master。继续B固定输入server lease/renderer准入离线定位和当前语言/数字口語，再安排必要输出专用场；普通mic、人类听感和最终10–20min集中体验仍pending。Study动态就绪与较完整日常文字学习整合待下一必要场。局部阻塞继续他项，Goal仍active，以实际证据完成。
