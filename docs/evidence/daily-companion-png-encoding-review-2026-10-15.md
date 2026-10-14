# PNG图片入口编码独立窄审

2026-10-15。只读canonical static/main.js的compressImageForStudy五行增量、新Node编码测试、既有图片UI fixture更新；精确核既有后端PNG白名单。只新增本报告，不改源码、manifest、共享记录、raw或账本；未启动host/浏览器/网络/模型/音频设备。

## 结论

本次最小增量未发现具体新增P1/P2。**SOURCE/OFFLINE通过**；Main正在执行的真实web-inspector结果不由本报告冒领。PNG支持与图中文字的真实模型可读性是不同层；不得因无损编码就把密集小字教学标PASS。

## 编码与兼容范围

- 与已发布a1a431d同函数定向比较：原load/decode、AbortSignal检查、尺寸计算、canvas白底填充与drawImage之后，仅在blob.type严格image/png时先toDataURL(image/png)，总URL长度<=既有TARGET_DATA_URL_LENGTH才直接返回。
- 原预算仍1000000**字符**且包含data URL前缀；不是把上限偷改为1MB原始字节。PNG超过预算后完整沿原JPEG .82→.56→.3三档，全部超限仍null。JPEG来源不额外走PNG，未新增提交/重试/模型调用。
- 原最大边配置与不放大规则未变（默认768，实际由配置决定）；sourceWidth/Height无效、context失败、decode取消/异常的原处理保留。该编码不移除课程/session/material revision及旧回调取消守卫。
- PNG是**对最终canvas像素无损**；此前缩放重采样和白底透明度合成仍会改变原图。本次没有提升默认分辨率，也没有声称保留原文件字节/hash/透明通道。
- 既有canonical study_submit_image委托base entry_common._normalize_submitted_image_payload；实际base `benchmarks/raw/neko-app/resources/bin/plugins/study_companion/entry_common.py:98–100`已经明确支持data:image/png;base64及JPEG，未发现仅JPEG入口假设。本次没有更改backend。

## 独立Node离线验证

```powershell
node scripts/test_neko_image_encoding.js
```

实际从canonical main.js抽取原函数，在Node VM与限定canvas输出seam执行，结果 **7 PASS**：PNG预算内直接保留、不调用JPEG；PNG超限回JPEG；JPEG按原质量降档；全超限null；已取消不编码；1600×800按768上限变768×384；宽0拒绝。

fixture预算缩为100便于分支检查，不是实测图片质量/浏览器toDataURL实现。没有把字符串seam当真实像素证据。

## UI fixture更新审查（本次未运行浏览器）

- flow原preview断言由JPEG改为实际PNG前缀，并继续核同一image_base64/expected_course_id交study_submit_image，未弱化换课/替图/late callback的原判断。
- 新encoding场景读取已有图，按与产品相同配置尺寸和白底合成构造reference canvas；对PNG重新decode后逐RGBA sample比较，并核尺寸及<=budget，再确认同一验证过的data URL确到Study提交fixture。
- 使用原fixture材料，没有生成或修改Sky Scout/已有比较图。fake提交仅验证DOM与payload；它不证明真实vision服务理解小字，也不是新模型场。
- Main拥有共享web-inspector实际desktop/mobile、races及encoding运行；本审查仅读其fixture，不重复启动本地服务或浏览器。

## 最终审查指纹（SHA256）

| 文件 | SHA256 |
|---|---|
| canonical static/main.js | `acde4db25cdcd7195853a1a2a477bb28ae4f99d2e1d8f1e6a1b0ce5c45953b25` |
| scripts/test_neko_image_encoding.js | `0f8af59c8d92ca35d8e6e208bdda793f86871a4753ff1e19481be7465888077a` |
| scripts/test_neko_daily_image_ui.py | `9555fa65ea7749621e59912982ee81f93a568c7f76b628742e39f82339d8e017` |

报告冻结。源码/VM与实际浏览器/模型/物理设备/真人证据分开；不改此前密集小字失败或整体Goal状态。

## Main实际浏览器结果只读复核追加

Main完成shared inspector：desktop flow13、races7、mobile flow13检查通过（运行由Main执行，本次不重跑）。encoding首版fixture用fetch(data:)被既有CSP阻断，Main保留原失败raw，仅将fixture解码换为atob→Uint8Array→Blob；独立核该精确变化，产品代码/CSP未因测试放宽。

成功原件 `daily-companion-image-ui-1792008166079738600-encoding-desktop.json` 独立SHA256 **`92f6899b71493c3f09ab75e52c025527eb70e3dc35be3b24da980712ba215b69`** 一致：三个实际DOM/canvas检查均True（全部rendered pixels相等、原尺寸cap不放大、exact PNG交既有Study提交fixture）；missing_routes=[]，inspector consoleErrors/pageErrors/failedRequests=[]，horizontalOverflow=False。此为Main运行的真实浏览器编码/提交fixture证据，不是backend模型理解或密集小字教学通过。

source main.js与Node测试指纹未变；UI fixture最终SHA256更新为 **`984059ced99e11728f2b9bff630b06685af1742e22d77dc2cc4dcef74af82c06`**，上表旧值仅对应首次审查时fixture。未认领部署，Main报告default static仍核旧SHA。无新增具体P1/P2，再次冻结。
