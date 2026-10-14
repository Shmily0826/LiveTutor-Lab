# 阶段41：学习图片在现有预算内保留无损 PNG

完整 [contract](../daily-companion-contract-2026-10-14.md) 保持，Goal active，A–F 不缩减。阶段40自动响应草稿因实际工具续接P2已隔离、运行接线精确恢复且SourceGate PASS；本轮推进独立的图片入口，不新开语音模型场。

## 改动

此前 `compressImageForStudy` 会把 PNG 架构图一律转成 JPEG，再按0.82/0.56/0.3压缩。在现有缩放与白底绘制后，现在仅对 PNG 先编码为 PNG；不超过原1,000,000字符上限才保留，否则仍用原JPEG三档。JPEG输入仍走原路径；原最大边长设置、不放大、文件20MB限制、取消/换图换课守卫与既有Study vision提交入口不改。没有增加配置、模型、依赖或新图片材料。

这避免的是PNG图中文字/细线再受有损编码；**不是提升图像分辨率、OCR或密集小字模型验收通过**。仍按既有canvas白底绘制/缩放，因此逐像素对齐的是该渲染结果，不冒称原PNG元数据、透明度或文件bytes保持。

## 证据分层

- SOURCE/OFFLINE：Node VM抽取实际encoder函数，7例通过。canvas输出为明确替身，核PNG优先、超上限回原JPEG、JPEG原两档、全超限拒绝、取消、尺寸cap、不合法零尺寸；不将替身作为实际编码证明。
- 真实本地浏览器：复用既有3张图和 `test_neko_daily_image_ui.py`，由指定 shared web-inspector CLI 运行。桌面flow13、race7、手机flow13检查通过：PNG预览、精确提交、替换、粘贴、坏/大文件、换课、异步旧图/回复拒绝均保留。SDK/模型为fixture，不冒真实Study后端或模型教学。
- 新encoding浏览器3检查通过：真实图解码、同设置canvas白底/缩放的所有RGBA像素与输出PNG解码逐项相等；尺寸按原cap且不放大；exact PNG经既有study_submit_image参数送至fixture。console/page/failedRequests均为空，无整页横向溢出。原3张图hash由runner前后核相同。
- 未新增真实模型/设备可听/真人证据，密集小字识别仍待验；无mic、capture、loopback、声音或系统音量改动。仅loopback HTTP fixture，不启动真实N.E.K.O宿主。

首次多场runner整体exit1：前三场上述33checks通过，新encoding测试误用fetch(data:)被现有CSP拒绝，TypeError: Failed to fetch；原失败raw保留。仅改fixture为atob→Blob解码，不改产品CSP或权限，再定向重跑受影响encoding，exit0、3checks PASS（4.089s）；不重复已通过前三场。

## 原件

私有raw不入Git：

| 场景 | 文件（benchmarks/raw/evidence下） | SHA256 |
|---|---|---|
| 桌面flow | daily-companion-image-ui-1792008112800478200-flow-desktop.json | 55be327bfb998f4178bfcad6fbbcf0f20a22362d82cdc07bfab5097bea838eb7 |
| races | daily-companion-image-ui-1792008118894880400-races-desktop.json | cd93ebc32bf8650a31e6fdf1d3d5b3e283da6c6982181697f220aa2c33ae74f6 |
| 手机flow | daily-companion-image-ui-1792008126652814900-flow-mobile.json | e6bdcdf361c870f0ec4f9a4e5f35c1248876e20575d1c95dab364d28e9193d22 |
| encoding首次fixture失败 | daily-companion-image-ui-1792008128666765000-encoding-desktop.json | 3483b771d94b02acafcf7370b5ebf97958f997f6f3d1a9ad68e34f616b5ea0ea |
| encoding修正fixture通过 | daily-companion-image-ui-1792008166079738600-encoding-desktop.json | 92f6899b71493c3f09ab75e52c025527eb70e3dc35be3b24da980712ba215b69 |

实际输出截图Main查看了整页首屏；图片区域在下方，此截图不是小字视觉可读性证据。逐像素结论来自上面的实际DOM/canvas检查。

## 指纹、部署与接续

main.js SHA acde4db25cdcd7195853a1a2a477bb28ae4f99d2e1d8f1e6a1b0ce5c45953b25；UItest984059ced99e11728f2b9bff630b06685af1742e22d77dc2cc4dcef74af82c06；Node test0f8af59c8d92ca35d8e6e208bdda793f86871a4753ff1e19481be7465888077a。独立审查及default静态部署待终态后追加；旧default static SHA38cb30d8622fdf539b2754911b2a8663b4ff9e9d502672561a3434ff434e6185已核。只允许按旧SHA替换该静态文件，不拷贝或改用户DB/history/base plugin。

原账本bargein-autocheck-20261012仍810/2000、app76/null、tech0/0，无新的模型/CONNECT。必要speaker仍用户已设4%且未使用；禁mic/capture/loopback。测试fixture/server/本次task浏览器随runner清理，无live在线场。完整Goal未完成；B native工具continuation join、自然停顿/追问，C跨概念身份，A密集小字与可见入口、D/E/F集成及最后集中真人体验继续。

## 审查、精确部署终态

[独立PNG审查](daily-companion-png-encoding-review-2026-10-15.md) 已冻结：无新增P1/P2，独立Node7 PASS；独立只读核成功encoding原SHA/3checks和无console/page/failedRequests，后端既有PNG支持已核。其余33浏览器checks由Main执行，未混称独立跑过。

Main在48911/48916/9234无listener后，仅对default `plugin-code/study_companion/static/main.js`核旧38cb…6185、独占phase41-before备份、替换为canonical acde…3b25并逐字验证；产品manifest仅static项保留prior SHA并更新当前SHA/窄证据，manifest新SHA49bfbf9047b99e9c3554d2abde15955ea1b320b2c3b04ba2ee807ffa29618eb7。未改base plugin、用户库、host源码或host manifest；后者原SHA40c8…3da71保持。SourceGate实际再PASS。

契约原169行SHA FD518311C0B3FAFBE038B2BBD83D8EB0DE8986212BCB4B86FCCAB22464084C33保持，原ledger810/76/0，仍无live host/online scene。未为这5行编码修复重新付费跑旧图片闭环。发布只允许代码/测试/阶段文档/隔离草稿，排除raw/DB/录音/密钥/backup；commit与remote终态由后续记录追加。


阶段41发布核验：16精确allowlist（无损PNG+测试/审查/当前记录、可重放隔离producer/patcher与40失败证据）已commit/push 70de00c0fd36aff082ebbf48f677c8d86d496fa1 到codex/daily-learning-companion，remote同SHA、publisher clean、master仍f1e8f3f5605659f0526e43bc3b85c60ae46c85fb，Root index空。未发布raw/DB/录音/密钥/unused grade完整备份；contract原SHA、SourceGate、default static exact均再核通过，ledger810/76/0。无live exec/host/在线场，麦克风/capture/loopback及音量均未操作。
下一42先本地收窄真实tooltask→native sealed origin的同lane continuation设计，从actual _capture_tool_task_owner/_start_raw_tool_call/_send_tool_results_openai_realtime与隔离测试接续，不能只按connection/时间或当前seq认父输入；先实际工具callback、并行/新PCM/旧conn/取消fixture及独立review，不接生产/盲开模型。若归属资格仍无足够证据，记录缺口并转A/C/D/E其余集成，不把40局部阻塞当Goal终止；本轮PNG不重复验证，密集字/语义/物理可听/human仍独立待验。
