# 日常伙伴：Study 图片入口与恢复

## 交付与证据层

本阶段修改 `patches/neko-study-2026-10-10-product/static/main.js` 与 `index.html`，保留主线上一轮图片入口及界面风格。新增 `scripts/test_neko_daily_image_ui.py`。未改宿主、launcher、共享账本、用户课程数据库或 Sky Scout；未重复 E 指示几何与已验图片教学闭环。

| 层级 | 结果 | 证据 |
| --- | --- | --- |
| 源码 / 离线 | PASS | JS syntax、既有 product-ui OCR / course 守卫、Python compile、diff whitespace 检查 |
| 实际浏览器 / 本地假 API | PASS | 50 项实际 DOM 检查；真实图片解码、canvas 压缩与真实 runs HTTP 请求；desktop 1440×900 / mobile 390×844 |
| 本轮真实模型 / 角色工具 | 未做 | 不将模拟 API 的 FAKE 回复视为模型输出；继承主线已有模型证据 |
| 设备播放 / 真人体验 | 未做 | 未启动音频、native shell、房间麦克风或系统输出捕获 |

总证据：`benchmarks/raw/evidence/daily-companion-image-ui-20261014.json`，包含分场景 JSON 来源、每项检查、浏览器截图 / console / network 状态、代码 SHA-256 与输入三张既有 PNG 的 SHA-256。三张原材料均保持不变。

## 确认失败与最小修复

基线真实浏览器确认 6 个竞态失败：换课后迟到文件 / paste 解码恢复旧图；较新 paste 被旧文件回调覆盖；换图后的旧讲解重新启用追问、把新图声称为已提交；旧课程讲解覆盖新课 UI。普通文件 / paste、换图后的新 payload 原本通过，没有重制测试材料。

修复：文件与 paste 共用每类输入的 AbortController；清除图片和换课会取消未完成解码，较新文件 / paste 取代旧输入。输入开始或图像改变推进材料代次；讲解的成功 / 错误回调必须同时匹配材料代次和课程，旧回调不写 UI。并发 status 请求仅采纳最后发起的一次，避免迟到状态把课程切回去。取消的是图片读取 / UI 旧回调，不宣称已取消后端正在执行的模型请求。

另一条问题是角色在后台换课、网页尚未刷新时，点击讲解会把旧预览提交给新课。现在图片讲解先做一次本地 `study_status` 检查；发现换课立即清图，不提交旧图片。提交携带 `expected_course_id`。主 Agent 同时在 `study_submit_image` 的既有锁内核对该字段，不匹配返回 `course_context_changed` 且不保存图片；此后端修改与真实方法守卫由主 Agent负责。本前端保留 run error code，并兼容既有中文拒绝消息；收到拒绝刷新当前课、清除旧预览。真实 DOM fixture 已验证状态与提交之间发生换课时的拒绝协议，未声称这是在线模型验收。

未就绪时明确提示“点击刷新，连接恢复后再讲解”；网络请求失败保留选中的图片并提示恢复方法。刷新恢复后可再次主动讲解，不自动重发图片、不无限重试模型。文件格式、20 MB 限制、损坏图片均有可恢复提示；损坏输入不替换最后一张有效图。移除或课程切换清除旧“图片已交给”状态、错误和追问。`study_submit_image` 客户端超时与普通讲解同为 120 秒，避免图片路径沿用默认 60 秒。

浏览器截图额外确认初次学习阶段 modal 遮住所有输入；程序化 DOM click 不会自动发现遮罩问题。已取消 status / bootstrap 自动打开 modal，改为原 first-run 引导中的“设置学习阶段”按钮显式打开；原 modal 样式、阶段设置、跳过与本地存储保持。desktop / mobile 的实际 `elementFromPoint` 检查确认图片按钮没有被遮罩挡住，主动打开与跳过后的状态保持均通过。

先前 desktop / mobile 的唯一 404 已通过本地请求日志定位为 `/favicon.ico`，不是图片 / CSS / font。`index.html` 加空 data favicon 后，全部成功场景 missing routes 为 0。

## 实际浏览器检查组成

- 文件 / paste 完整流程：desktop 13 + mobile 13。真实 PNG → 浏览器 Image → canvas JPEG → `study_submit_image`，核对实际 HTTP payload 精确等于当前预览 data URL，携带正确课程；换图不携带旧解释；文件错误；移除后走文字入口。
- 延迟与竞态：desktop 7。延迟解码、晚返回讲解、换课、文件与 paste 交错、较旧 status 迟到。延迟由量具控制，但读取 / 压缩、DOM 事件处理、HTTP 与 UI 更新均由实际产品代码执行。
- 未就绪与网络恢复：desktop 4。HTTP 503 与主动断开 `/runs` 连接，随后恢复；没有页面重载或自动模型重试。故障场景中的 503 / `ERR_EMPTY_RESPONSE` 是明确注入的网络失败，已保留 console/network 原始记录。其他场景无 console error、page error 或 failed request。
- 原 Sky Scout 预览：desktop 1 + mobile 1。截图验证原图可见、实际解码尺寸不超过配置 2048 px，无页面横向溢出。
- 初次引导：desktop 4 + mobile 4。初始不遮罩、按钮实际可点、用户主动打开 modal、跳过后刷新保持关闭。
- 换课提交协议：desktop 3。未刷新网页的角色换课 preflight 清图；状态→提交间换课拒绝且新课程未存图；拒绝后 UI 清图并显示新课程。明确 code 和既有消息兼容形状均单独通过。

Fixture 使用浏览器合成的 File / ClipboardEvent，复用三张已有 PNG，实际运行产品输入处理器；没有读取系统剪贴板或操作系统文件选择弹窗。它证明浏览器入口 / 协议，不冒充用户实际文件选择、模型关系理解或真人体验。

桌面与手机预览截图已保留：

- `benchmarks/raw/evidence/daily-companion-image-ui-desktop-20261014.png`
- `benchmarks/raw/evidence/daily-companion-image-ui-mobile-20261014.png`

截图中的部分 i18n 标签是 fixture 空字典的 fallback，不作为生产翻译缺陷。没有借机重做首页或修改 CSS。

## 复现、失败留存与支持边界

```powershell
python -m unittest discover -s scripts -p test_neko_daily_image_ui.py -v
# 仅回归具体变更场景，避免重复已过长流程：
$env:NEKO_IMAGE_UI_CASES='course-submit'
python -m unittest discover -s scripts -p test_neko_daily_image_ui.py -v
```

所有浏览器检查统一调用用户指定 `node D:\AI\tools\web-inspector\cli.mjs <本地随机端口URL> --screenshot --json`。未在项目安装或 import Playwright。API fixture 在 `127.0.0.1:0`，只提供该 Study 页需要的本地 assets / runs 与三个授权 fixture 图。没有线上 provider、认证、CAPTCHA 或现有浏览器 session 操作。

每次尝试均独立保存 `daily-companion-image-ui-<时间戳>-<case>-desktop/mobile.json`，不删除基线失败。第一次修复后的唯一残余 race 是量具过早把已有预览当成新 paste 完成；调整等待真实 src 改变后通过。真实截图发现 modal 遮罩后新增可点击性检查并修复产品。后端 course error 从普通 SdkError 消息升级明确 code 时，只定向验证该协议，不重跑已过 UI 长流程。

Impeccable detector 对这两文件执行一次：overlay static 本身没有 stock CSS，静态工具无法加载 stylesheet，给出继承的 flat hierarchy 与两个无 src 的隐藏 preview 警告。实际 fixture 按部署同一 overlay 方式加载 stock assets，所有必要资源 200，预览有 src 且显示，没有页面横向溢出。此检测限制已记录，不将静态 warning 默默当 PASS，也不为它改动本阶段之外的视觉体系。

当前无需为本子任务继续等待外部条件。仍待主线最新版部署 / manifest、真实角色与图片接续的产品集成确认，以及用户集中真人体验中的真实文件选择 / paste 和换课体验。主线后端原子课程核对是本前端新协议的依赖，不能只发布两个 static 文件到尚未支持 `expected_course_id` 的旧 backend。

额度与进程：DeepSeek / Lanlan.app / Lanlan.tech 新增均为 0；共享账本未改。所有量具进程均已结束，随机端口服务在 finally shutdown / server_close / join，未清理主 Agent 宿主。没有改系统音量、采集房间麦克风、启动在线音频或生成新合法测试图。
