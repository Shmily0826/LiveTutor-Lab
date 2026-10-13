# 教学闭环 Goal：完成审计通过（2026-10-13，NZDT）

现有 Tutor 的解释、加法举例、出题、判题、针对性纠错、重启接续课程与错题已取得真实后端证据；基础真人教学与普通真人打断已有用户确认。最后追加授权后的自动验证补齐了真实客户端切换的语音连续性和最新提示效果。所有实现沿用现有插件、SQLite、原生语音入口与启动器。

## 修复和最终行为

- 出站额度拒绝有专用原因，SDK异常链正确映射为agent_quota_exceeded；普通网络问题仍保持provider_unavailable。失败教学工具明确说明服务暂停，去掉伪造的题目、评分和判定。
- 判题从持久化当前课程取题目身份；同课程未答题跨进程保留，已评分、主动换课或新建课程按既有规则清理。课程状态包含实际wrong/correct记录，重启后的回忆以真实答题记录为准。
- Tutor启动复用上游的持久引导状态，保留已完成和手动重开意图；原生壳重复启动保留已有配置。独立测试目录避免加载原用户旧历史。
- 播放反馈只发送一条完整回执，保留audible。新显示客户端接入时，旧voice owner仍能收到pong并继续送PCM；只有真正的语音接管才撤销旧owner。未更换VAD、持续门槛、PCM handoff或取消架构。
- 语音教学移除与用户句数冲突的默认数字范围。追加的真实宿主重启检查发现了网页解题合同要求四节与额外练习、同时语音合同要求无标题/无测验的冲突；现在已携带语音合同的请求只使用该合同。网页完整解题合同保留。实际修后回忆是简短三句、不出题；明确两句话的解释恰好两句。

## 验收对应关系

| 要求 | 实际证据与范围 |
|---|---|
| 解释与合适举例 | results.json内真实add(a,b)、total、return、result、print(5)回答；SQLite记录保存了对应材料 |
| 出题、判错、纠错、判对 | 实际题目ID/attempt匹配，错误“自动返回最后结果5”得到wrong/0，针对性解释None，后续正确回答correct/100 |
| 重启续题和续课 | 原宿主PID53972→53156，题目身份跨宿主重启保持；当前再完整重启33476→34428→42896，同一课程恢复wrong/correct/partial记录，最新模型准确引用旧错误及后来正确回答 |
| 真人基础教学 | 用户确认声音、出题、判错、纠错正常；本场实际答案是不完整的return解释，实际评分partial/55，不能将这场改称wrong/0 |
| 保留普通打断 | 原普通真人打断有用户确认和两次handoff日志；当前19个实时语音回归、3个所有权/完整ASGI双客户端回归及生产JS取消/解码/重连回归通过 |
| 客户端切换后的真实语音连续性 | 一条真实Lanlan会话、两段固定WAV、真实RNNoise；原录音socket在独立显示socket及后来原生聊天socket变更后继续收音，期间5个旧socket pong，录音保持至约165秒，随后自动停止 |
| 最新提示质量 | 原生聊天实际完整显示两句；真实插件avatar回调另行验证两句话及重启后错题回忆，无标题、额外测验或代码块，非degraded |
| 启动与部署可复现 | canonical product覆盖19文件，两份测试部署哈希一致；host manifest17文件、两部署根20个语音补丁目标核对通过；冷/重复启动、损坏配置保护的既有回归保留 |
| 预算、数据、清理 | 同轮账本无重置；只在隔离测试根写学习数据，不改原用户历史、不提交/推送；最终stuck=[]、left_over=[]、log不再推进 |

## 新增授权与实际使用

同一bargein-autocheck-20261012轮次，上限从160/18/0提高到300/30/0，批准时spent160/18保持不变。追加授权后实际到173/19/0，新增DeepSeek出站预留13、Lanlan.app CONNECT1；整个教学Goal从60/11起，累计新增113/8。计数包含启动和辅助请求，不是实际账单金额。没有为用完额度而继续测试。

原生连续性场景先完成并关闭输入、角色和宿主；之后两次仅后台宿主的完整重启，用来检查课程回忆和验证语音合同修正。后两次没有原生角色窗口、硬件麦克风或扬声器。最终宿主也已关闭。

## 原始证据和复现

主要证据位于benchmarks/raw/evidence：

以下除完整写出的名字外，简写文件名均带有`teaching-quality-20261013-`前缀。

- teaching-quality-20261013-results.json、final-human-events.json、final-human-db.json、final-audit.json：早先真实教学与真人验收。
- window-live-events.json、window-live-routing.log、window-live-loopback.json、window-live-audit.json：真实独立WebSocket、RNNoise、接续回答和回环；旧输入socket没有close，聊天窗口采到68个播放回执、65个audible=true，回环60个响声片段。
- final-host-restart-history.json：保存修前回忆正确但违规追加题目的失败；实际新宿主PID34428。
- final-spoken-contract-callbacks.json：修后实际新宿主PID42896，同课程、真实wrong/correct记录、简洁历史回忆及恰好两句话解释。
- final-contract-cleanup.json、goal-completion-audit.json：最终清理与逐项完成审计。

生产补丁重放：`python -B scripts/neko_voice_host_patch.py`；只检查可用`--check`。产品覆盖与引导/角色提示由scripts/neko_desktop_tutor_host.py的--source启动准备过程应用。保留原部署树和数据，不能用git reset/clean代替部署。

本场历史命令如下，后续使用前应先核对同轮账本与当前授权；不带--audio-input会使用物理输入，必须先和用户约好。

```powershell
& benchmarks/raw/neko-product-host/.venv/Scripts/python.exe -X utf8 -u -B scripts/neko_desktop_tutor_host.py --source --voice --core-provider free --store neko-teaching-long-pause-20261013 --hold 900 --seconds 100 --api-budget 40 --egress-budget 300 --allow-host www.lanlan.app:30 --budget-round bargein-autocheck-20261012
& benchmarks/raw/neko-product-host/.venv/Scripts/python.exe -X utf8 -B scripts/neko_native_shell.py --store benchmarks/raw/neko-teaching-long-pause-20261013 --chat-surface compact --cdp-port 9227 --audio-input benchmarks/raw/voice-input/quality-agent-return-and-window-20261013.wav --wait 45
```

固定WAV为原问题、25秒额外静音、原问题的组合，长179.279秒。等待角色toolbar和socket就绪后开始输入；约50秒接入独立WebSocket，约165秒关闭输入，早于文件循环；保存所有任务窗口数据。输入采用Fake Default Audio Input，不读取房间麦克风。调用既有neko_native_shell --stop和neko_session_guard stop进行清理。

## 证明边界

本次没有新增真人打断验收、跨播放结束真人专项或长期稳定性证明。原生语音场景直接作答，没有调用Study工具；最新工具提示的实际模型效果通过独立真实回调验证，不把两者冒称成同一次工具语音转述。初始聊天窗口的早期帧未采齐，后续窗口的完整DOM、音频帧和回执已核对；不宣称完整首轮逐帧记录。回环证明设备输出，真人听感采用此前用户的明确确认。

本场句数和不出题要求通过，不保证任意未来提示都绝对遵守。服务失败说明未再安排人耳专项；评分反馈中的疑问语气是否独立影响分数也未专项测试。OCR/真正图像理解以及声纹识别不属于本Goal，本次未扩建这些功能。
