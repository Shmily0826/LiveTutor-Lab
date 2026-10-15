# 第二轮最终验证与保护边界

- 开工105个模块独立进程：98通过、7历史失败。新增5个模块后全回归110：最初发现新增summary_audit失败，已修任务审计锚点；修复复跑103通过、7失败。逐已执行测试名/异常原因比对一致；导入即失败的模块明确记录为未开始单测，不用整模块豁免掩盖新失败。原始比较codex-r2-final-failure-comparison.json的same_failed_test_names_and_causes=true。
- 最后只增加大行号摘要防崩边界，先红后绿；独立补测摘要7、审计2、语言6通过。没有为凑数字重复在线场。
- 产品source/manifest/deployment32项一致；SourceGate PASS，voice_host_patch检查全部patched。真实临时归档重建宿主31项全部匹配，没有新增宿主/arbiter/打断/传输补丁。
- 每次payload变更先核验旧SHA/保存代码与manifest，再部署并复核；P3曾发现Git换行规范化使一个发布SHA不匹配，已追加bf94cea修正。后续发布逐staged blob核对全部manifest条目，密钥扫描后精确提交。

历史失败仍是：autocheck_readiness、first_asr_ordering、late_asr_tool_patch、material_audio、study_singleflight、study_speech_gate、tool_result_lifecycle（对应test_neko_*模块）；原始完整异常与比较保留在本地raw/evidence。

## 实际模型与证据层

| 层 | 本轮结果 |
|---|---|
| 源码/离线 | 已列模块验证与文件校验通过；原7个历史失败保持 |
| 真实文字SDK | 源码教师、重启数据、0→100评分与保留历史通过；泛问曾遗漏字段，后续增加本地事实措辞 |
| output-only Native | 18场，均核验capture policy且无cleanup错误；包含成功和失败，不把场数当通过数 |
| 软件播放/取消 | 插话/换图有旧token取消、队列停止、新token音频；自然答错意图、自主指示、若干教学语义仍未通过 |
| 物理可听性/真人 | 未验证。没有录音、回环或真人麦克风验收 |

## 数据与运行保护

- audio_allowed=false；18场均room_microphone=false、capture_devices=false、loopback_enabled=false、volume_changed=false。固定WAV可输出扬声器；未改系统音量。
- 日常原SQLite的SHA与第一轮开工只读快照相同（e849d5a3…51c39）。本轮没有写学习数据。唯一日常部署是授权plugin-code文件，旧代码均在任务证据中备份。
- 原宿主日志仍114708行、mtime与第二轮首次session guard观测一致；所有新宿主输出都重定向到任务日志。
- 收尾session guard进程列表为空；仅清理自己记录的PID/创建时间，任务学习库和失败记录保留。
- 根目录保持master与既有脏改动，不reset/clean/stash，不新建工作树。只在既有codex/daily-learning-companion工作树精确发布，未合并主分支、未强推；raw/学习库/WAV/备份/密钥不提交。

账本1270/110→1541/130：DeepSeek271/400，Lanlan.app20连接；Lanlan.tech0，原轮次bargein-autocheck-20261012、全局DeepSeek2000/Native策略不变，Goal tokens不限。未用完的额度没有被消耗成无界重试。

最终产品仍PARTIAL；待复核与用户准备见[彩排报告](codex-r2-p8-rehearsal-2026-10-16.md)和[验收v2](../claude-acceptance-guide.md)。
