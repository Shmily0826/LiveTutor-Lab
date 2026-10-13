# 原生真人打断：本场 PASS（2026-10-13，NZDT）

用户从网页 Chat 转到当前 Codex，授权继续已有修复、原生桌面操作及麦克风/扬声器测试；累计上限保持 DeepSeek 60、Lanlan.app 12、Lanlan.tech 0。同轮 `bargein-autocheck-20261012`，不清空 spent。

**普通真人插话与新回复恢复：本场 PASS。完整教学质量：未通过本次验收；跨播放结束的边界和长时间稳定性：未做修后真人专项测试。**

## 接管与修复

- 接管前实际账本为 DeepSeek 48/60、app 7/12；网页端旧任务已中断，接管其原生进程后清理，再使用既有独立目录 `benchmarks/raw/neko-native-physical-20261013`。
- 启动器已有 `--store` 改动，未重做。独立目录的 `user_preferences.json` 实际为 `proactiveChatEnabled=true`，覆盖了 core config 中无效的同名关闭意图；只在这个测试目录关闭主动搭话，保留修改前快照。旧用户数据未删除或覆盖。
- Windows 工具能读取实际 N.E.K.O 窗口，但点击位置被缩放到下层程序，未重复盲点。共享 `web-inspector` 对本地页面返回 HTTP 200，无控制台或页面错误。使用共享安装的浏览器运行时连接本次 Electron 的原生验收端口 9227，未接管用户 Chrome。
- 一次已有提问 WAV 经真实扬声器播放，真实麦克风经过 48 kHz → RNNoise/soxr → 16 kHz，出现持续语音 onset declined，但没有回答音频。**不计为打断 PASS。** 未新建环境录音。
- 原生文字入口实际选择 `OmniOfflineClient`，没有原生音频；这条尝试用了 6 次 DeepSeek 本地账本请求。随后结束这条验证路线。

**本轮确认并修复的缺陷：** 两个部署根的 `app-audio-playback.js` 每次更新播放状态发送两条 `native_speech_playback_state`：第一条有 `audible`，第二条是旧版本、没有这个字段。生产接收函数以 `message.get("audible") is True` 保存状态，第二条会把刚保存的 True 覆盖为 False，破坏跨播放结束资格的依据。

重复来自补丁升级重放：短原始锚点先于完整旧 hunk 处理，且重放仍用中间版本的“已应用”标记。修复让完整升级先执行、重放使用最终 hunk，并清理旧部署遗留的重复 sender；`--check` 现在会拒绝带旧重复 sender 的部署。没有改变 VAD、0.5 秒持续门槛、0.15 秒间隙、PCM 缓冲或 handoff 架构。

这能证明本次发现的代码缺陷，**不能回溯断言它解释了 16:24 场次的全部失败原因**。

## 回归与部署

- 新 JS 断言在修前失败：`every receipt must preserve audible eligibility`；修后 PASS，包括每次播放更新只有一条完整 socket receipt，以及原有旧音频取消/新回复存活场景。
- `test_neko_barge_in_overlap.py`：既有 15 个边界场景，加 4 种部署状态（原始锚点、旧反馈、重复反馈、当前版本）的迁移和幂等性，全部 PASS。该脚本不导入宿主/配置管理器，不打开设备或 provider。
- 两个部署根共 20 个目标 `--check` 均为 patched；播放模块字节一致，manifest 播放文件和两个补丁源哈希一致；JS syntax、Python AST、`git diff --check` PASS。
- 改动保留在工作树，未提交或推送。未改 `.workbuddy` 记忆文件。

## 本场实际事件（L2）

第二次宿主启动横幅 `20261013T051823Z`。真实麦克风会话于 **18:21:32–35** 建立：`input_mode=audio`、`client=realtime`、RNNoise 初始化、前端 `isRecording=true`。没有 fake-device / fake-audio 参数。

| NZDT | 实际记录 |
|---|---|
| 18:22:42 | 第一个真实语音转写事件，len=32 |
| 18:22:49 | 首个 `response.audio.delta`，12,216 bytes；原生 owner A 的 active/audible 反馈随后到达 |
| 18:22:55 | `local speech onset (speech-sustained): isolating old native connection` |
| 18:22:56 | `[native-barge-in] handoff complete connection=1->2` |
| 18:22:58 / 18:23:00 | 替换会话的语音转写事件，len=11 / 31 |
| 18:23:03 | owner B 新回答首个音频增量，10,928 bytes；本回答共 14 个增量 |
| 18:23:07 | 第二个真实持续语音 onset；播放反馈仍 active/audible |
| 18:23:08 | `[native-barge-in] handoff complete connection=2->3` |
| 18:23:10 | 第三代会话的语音转写事件，len=19 |
| 18:23:13 | owner C 新回答首个音频增量，11,388 bytes；本回答共 15 个增量 |

实际 WebSocket 观察记录 **166 条**播放反馈，**0 条缺失 audible**，148 条 audible=true，覆盖 3 个 native connection owner。记录 70 个 audio_chunk 和 2 个 audio_done；观察器只收集这些类型，未保存 stop 事件，因此不能以该文件声称抓到了取消消息本身。

原生播放器事件在 **18:23:07.541** 显示 owner B 仍有 **2.2138 秒**待播放；**18:23:07.669** 变为 inactive、remaining=0。这证明客户端提前清空了仍有播放工作的旧 owner，随后 owner C 的实际 Web Audio 调度和反馈正常出现。未采集系统回环，不能给出独立声学停播延迟。

原始行号与摘要：`benchmarks/raw/evidence/direct-takeover-20261013-log-excerpt.txt`；真实页面/发包记录：`...-playback.json`。第一代 owner 的前端 CustomEvent 观察器尚未安装完整，但 WebSocket 反馈覆盖三代；不得把观察器窗口说成覆盖全部现场事件。

## 用户听感（L4）与限制

用户在这一个测试窗口明确回答：**“已测试：停了，并回答新问题”**。结合实际 onset、两次 handoff、提前清空旧播放工作和新连接音频，本场普通真人 barge-in PASS。

回答内容并不证明教学质量：owner B 的转录说“我无法使用计算器加法的例子解释”，现场也有 Study provider request failed；owner C 恢复了后续对话。不能据此说计算器示例讲解已正确完成，也不能证明插话 PCM 每个样本无损或所有句首均完整识别。

用户未单独确认“同一句话跨过原回答自然结束”的边界，此项仍仅有离线证据。成功场次不代表所有声学条件和长期使用都稳定。

## 账本与清理

| Host | 接管前 | 收尾后 | 本轮新增 |
|---|---:|---:|---:|
| DeepSeek | 48/60 | 60/60 | 12 次本地出站计量 |
| Lanlan.app | 7/12 | 11/12 | 4 CONNECT（前置声学会话、真人初始连接、2 次 handoff） |
| Lanlan.tech | 上限 0，spent 未列 | 同前 | 0 |

这是本地请求/连接计量，不是已核实的 provider 账单金额。上限和轮次未变；没有重试真人场次或新增轮次。app 余 1 CONNECT 不覆盖新的初始连接加 handoff；DeepSeek 已触顶，停止进一步在线调用。

原生麦克风已关闭，Electron 和本轮宿主进程已停止。守卫：`stuck=[]`、`left_over=[]`、`host_log_still_advancing=false`；after snapshot `processes=[]`。额外核对没有 Python/N.E.K.O 进程，48911/48912/48915/48916/9227 无监听。

前后快照：`benchmarks/raw/evidence/direct-takeover-20261013-before.json` 与 `...-after.json`。
