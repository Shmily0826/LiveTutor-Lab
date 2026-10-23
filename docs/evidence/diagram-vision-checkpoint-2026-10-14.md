# 图像教学安全节点：Study 图片闭环通过，Goal 按用户请求暂停

用户指定的原图为 `D:\UoA\S2\COMPSCI 734\project\Sky Scout\sky_scout\.archify\architecture-sky-scout-20261003-192623\sky-scout.html`。它没有被改写。全局 web-inspector 打开原 HTML，输出浅色/深色截图；模型接收的是截图像素，不是 HTML 源码、SVG 属性或本地真值。用户提供路径后没有重新制作测试图；之前已准备的两个相同文字、反向箭头的对照图用于关系验证。

## 完成和证据边界

- 当前可用路线是 N.E.K.O 已有的 Study 图片提交入口 `study_submit_image` → 既有 `vision` 网关 → 当前配置的 `deepseek-flash`。真实 API 接受图片。没有新增视觉供应商、域名、音视频架构或声纹识别。
- 同会话 WEX/NUD/REZ 正向和反向图的连接方向均正确；不重新上传图片的 `study_explain` 追问也正确，换图后使用新图。该结果经过真实模型验证，不能等同于离线或 OCR 验证。
- Sky Scout 的已验收教学范围是：StartupPage 定位与地图服务、本地观测页面→本地观测流水线→打包星表、Flutter→客户端 HTTP 服务→Express→天气/百科数据源；图示读取/请求方向与推断的数据返回方向分开。解释、追问、相关出题、错答 0 分、纠错、新题正确回答 100 分和课程总结都已有真实结果。
- 缺失信息场景正确回答“没有机器型号和实际请求延迟”。不承诺所有密集图片均可靠：浅色全图曾读错上排连线，深色截图改善主要关系，但部分很小的连线文字仍被误读。不能宣称完整小字转写准确或任意图像都通过。
- 免费 Native Realtime 屏幕线路传出了图片，仍未通过关系理解可靠性验收：连续更新、干净会话和反向图先测后仍出现错误。它不作为当前可用图像教学入口。现有 `free-vision-model` 在 Lanlan.app 专用文字端点两次返回 HTTP 400；停止该路线，没有绕过服务限制。
- 当前闭环使用实际 Study 和模型可调用工具回调，不是新的人耳语音验收。没有采集房间麦克风或外放音频，未重新验证图片讲解的真人语音体验。

## 最小修复

1. 图片提交先建立已有 Study 会话，再把经过验证的图写入已有 `last_vision_image_base64` 字段，替换旧图并清除旧文本。后续教学/出题/评分复用已有学习上下文，不建立新的图片缓存或模型网关。
2. 开始新会话或换课程时清除图片上下文，避免旧图跨课程泄漏。原有序列化仍不把原始图片写进持久状态；重启后需再次提交图片。
3. Study 视觉请求的默认自动细节改用 `high`，保留调用方显式设置的 `low/high`，不修改调用方消息。
4. 实时角色需要给教学工具传入实际观察到的图关系，或使用明确提交给 Study 的图片。没有视觉材料的“这张图”问题明确返回 `visual_context_missing`，避免文字模型编造模块与箭头；明确区分 OCR 文字与图像关系。

产品覆盖清单现为 21 个文件，与本轮隔离测试部署逐一匹配。图像改动未 commit/push；此前已发布的教学提交 `1fa40f408354fed6822bd48b27326ce2e4dc43cc` 不变。本地 HEAD 保持 `2c541755344eb8bcf35e310f871c513ea809e1a5`，原有脏工作保留。

## 验证与预算

新增/相关离线检查：5 项教学边界、6 项课程记忆、11 项启动、19 项打断、JS 播放回归、工具注册形状、Python AST 和差异检查均通过。这些不是新的真人打断证明。

同一 `bargein-autocheck-20261012` 轮次，上限保持 DeepSeek 300 / Lanlan.app 30 CONNECT / Lanlan.tech 0；本图像阶段从已用 173/19 到 271/30，新增 98/11，账本未重置。DeepSeek 尚余 29，Lanlan.app 尚余 0。这是本地出站预扣计数，不是已确认账单费用。

第一次独立 SDK 测量的模型/认证配置错误和随后服务拒绝均保留失败记录；该测量方式已弃用。闭环测量曾复用已评分 attempt，被系统在模型调用前拒绝；只补做新题、正确答复和总结，保留原错题，未重跑已完成的图片场景。正式复现脚本已使用两个不同 attempt。

本轮宿主和子进程已关闭。清理快照显示 0 个活动任务进程，无剩余音频会话。按照用户“在最近安全节点收尾，先讨论”的指示暂停 Goal，不将整体图像 Goal 标为全部完成。

## 复现和继续

使用已有启动器的隔离 `--store`，保留同轮预算代理。Study 设置 `llm_vision_enabled=true`、`llm_vision_max_image_px=2048`，视觉组使用现有默认 DeepSeek 配置；提交清晰的 PNG/JPEG。图像更新必须通过图片提交入口，开始新课程后重新提交。不要仅使用 `study_read_window` 的 OCR 文字代表箭头关系。

`scripts/neko_diagram_study_acceptance.py --images <截图目录> --output <新的结果路径>` 可以复现图片→追问→出题→判题→纠错→总结，宿主需已运行并受同轮账本保护。截图目录需要 `diagram-input-forward.png`、`diagram-input-reverse.png`、`diagram-input-sky-dark.png`。脚本不启动宿主、不接触凭证、麦克风或扬声器，不自动重试，不覆盖旧结果。

继续前先讨论：以可靠的 Study 图片入口为主、是否需要把它接入角色的实际语音体验，以及密集图中小字/模糊关系的支持边界。若需要再次连接 Lanlan，须有新的额度授权；本轮停止，不请求用户立即复测。

原始证据在 `benchmarks/raw/evidence/diagram-vision-20261014-study-closure.json`、`diagram-vision-20261014-safe-checkpoint-audit.json`、`diagram-vision-20261014-safe-checkpoint-cleanup.json`。前期错误、原生线路和小字误读结果也保留在同目录，不用最终通过的场景替代失败记录。
