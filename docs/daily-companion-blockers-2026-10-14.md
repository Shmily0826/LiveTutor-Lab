# 日常学习伙伴阻塞清单

完整执行契约：`docs/daily-companion-contract-2026-10-14.md`。压缩或自动续跑先读 contract、plan、status、blockers；后续明确指令优先。局部项不等于全局阻塞，不能以时间或单项成果标整个 Goal 完成。

| 项目 | 具体状态与证据 | 已尝试 | 恢复条件 / 继续路线 |
| --- | --- | --- | --- |
| 本窗口模型配置 | 工具上下文不提供可确认模型与推理强度 | 已明确说明，不切换 | UI 明确配置确认；当前继续代码/证据接续 |
| Native Realtime 直接看图 | 继承 checkpoint：方向关系误读，免费文字视觉端点 400 | 历史已停止，无重复试探 | 当前复用已通过 Study vision，与角色语音整合 |
| 密集图小字 | 继承 checkpoint：部分小文字/连线误读 | 清晰深色图改善主要关系 | 支持清晰图/局部查看，诚实表达不确定，定向验证 |
| 真人语言/声音/长句与最终体验 | 本轮尚未做 | 夜间不采房间麦克风 | 用户明确“准备好了”后一次 10–20 分钟集中验收；继续固定输入/回环 |

不因以上局部项结束 Goal。新增失败必须记录证据、已试方法、恢复条件；服务失败按要求退避，继续本地工作。

新增局部失败：`daily-companion-20261014-model.json` 首次“two English sentences”输出中文；已修语言检测，修后实际DB输出两句英文（`language-fix-db.json`）。`voice.json/voice2.json` 均为量具启动/就绪缺陷：child未继承UTF8、错误假设/available含plugin ID；改用已有plugin_server_ready并显式UTF8。前两次未CONNECT、不影响额度，第三次单场继续，不做无效服务重连。

续记：voice3是文字触发产品offline handoff，0播放，已停止；voice-fixed改固定WAV+heartbeat，同场真实study_explain与71音频准入/161回环响声，room mic=false。自然停顿分轮仍PARTIAL；日志两段识别93/9字，两个study_explain。恢复条件：统一输入/ASR/tool/audio/playback时基并做停顿专项；不动已验普通打断架构来掩盖问题。观察socket不再接收native输出，逐字语音转述需native DOM/输出文本专项采集或集中真人确认，不能用空观察socketreply认定失败/成功。

Goal objective字段更新工具限制：内置update_goal只支持status；Local Bridge goal get遭schema validation（要求token_budget且剥离action），未重试写入，未改任何Goal预算或状态。完整contract已在现有Goal的plan/status与当前执行上下文明确绑定引用，不重建Goal；此UI字段限制不阻塞开发。

同步补证：native-timing已捕获真实role两句文本和回环，旧“最终reply未采”边界仅适用voice-fixed历史场景。三段75/93/9字识别确认自然停顿过早分轮；没有provider session.updated确认，不臆测silenceDurationMs被代理支持。MANUAL候选默认off；首次support量具在宿主补丁重放锚点冲突时退出（manual-support.json，额度314/33不变），先本地兼容修复再一次有界支持验证，不重复无效服务连接。局部项继续D/E/F工作。

最新MANUAL支持场景已完成（manual-support3.json）：null请求存在；commit前仍三段输入完成与两次工具，没有echo确认，不能交付RNNoise自动end候选。已撤下实验运行时代码，不再同场无效重试。保持局部B问题：下一步可离线设计输入/工具完成协同，或获得代理支持的明确协议；不改供应商、不把普通打断延后、不以这项失败阻塞其他交付。

日常直接Python启动编码失败已修并成功启动/重启；Study SDK将课程拒绝包成INTERNAL前缀，已按实际序列化修前端并专项通过。最新所有量具进程结束；额度330/34/0。仍待任意桌面指示、密集小字、更自然中文长句、真人术语/听感/新能力体验；继续独立本地工作，不作全局阻塞声明。
