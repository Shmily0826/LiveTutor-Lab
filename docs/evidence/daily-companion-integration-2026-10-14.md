# 日常伙伴第一阶段整合证据

本阶段执行依据是完整 `docs/daily-companion-contract-2026-10-14.md`。Goal active；本报告不是全部A–F完成验收。

## 已交付与实测

- 日常入口 `Start-Daily-Tutor.cmd` 固定 `benchmarks/raw/neko-daily-companion`，配独立浏览器profile、同轮账本、仅Lanlan.app。学习surface使用已存在原图，日常入口不再额外打开Flutter测试课窗口。新store默认启用已有Study vision / 2048px，已有数据库保存的设置优先，重启不覆盖学习者修改。
- 图片可文件选择或粘贴；真正提交走现有 `study_submit_image`。换图清上一讲上下文；网页发现角色换课时清旧预览。每课最新明确提交图复用Store kv存储；换课不混图，返课及宿主重启恢复。原checkpoint中的“不持久原图”历史支持范围已改变，原数据不被清空。
- `study_preferences` 明确长期设置才入kv；临时默认只在下一次教学context消费，临时语言不改课程。已选概念作为稳定topic用于出题、评分及FSRS，不对旧自由标签作无证据模糊归并。角色工具已注册 `study_material` / `study_preferences` / `study_point`。
- 受控surface有材料hash、当前选择和版本绑定，支持HTML模块/连线与图片归一化区域，滚动/缩放重测、离屏隐藏、换材料清除。原文件不改。角色status只提供当前材料bounded定位metadata，不能把HTML属性当图像理解证据。

## 证明分层

| 层级 | 本阶段范围 |
| --- | --- |
| 源码 / 离线 | 新daily材料3、偏好6、surface5非浏览器guard；受影响既有课程6、入口11、教学边界5、回复形状与AST/JS检查通过。surface另1项默认跳过的opt-in browser测试不能算离线PASS |
| 实际浏览器 | 指示desktop/mobile各14几何检查，6原材料hash未变。Study网页desktop/mobile无横向溢出、无page error；mobile有一次404须进一步定位，初始截图在加载中，不能称整套UI交互通过 |
| 真实模型 / API / DB | `daily-companion-20261014-model.json`：图片身份、换课隔离、返课、两宿主重启、明确偏好和临时不保存通过。实际Study工具回调是后端证据，不等于角色自行选工具 |
| 实际角色 / 设备播放 | 固定SAPI WAV经真实RNNoise / Lanlan.app，宿主实际 `TRIGGER __llm_tool__study_explain` 两次；原生窗口使用fake silent input；71个native audio callback / output / frame admission；WASAPI默认输出回环161个响声片段，max_peak0.9901。没有采房间mic或改音量 |
| 真人体验 | 继承基础教学和普通真人打断已确认；本阶段新图片、偏好、停顿、指示与听感仍待一次集中真人验收 |

## 真实失败与限制

第一次 `two English sentences` 问句输出中文，保留在model原始结果，不能标为初次通过。修了自然表达及长期请求大小写识别；`daily-companion-20261014-language-fix-db.json` 的actual interaction5是两句英文，保留原图中文标签。单次语言没有升级为长期偏好。此处是修后专项证据。

声学量具前三步失败保留：voice.json为child未继承UTF8；voice2.json错误假设 `/available` 有plugin ID；改用既有 `plugin_server_ready`；voice3.json把文字提交到音频session，产品主动handoff到offline text且无播放。前两项没有任何CONNECT；第三项有一场连接但0响声。没有把这些当服务通过或重播已通过场景。

改用固定WAV后实际有播放，证据 `daily-companion-20261014-voice-fixed.json` + `.loopback.wav`（私有原始记录，不提交）。旧输入socket保有25次pong，但输出转到了实际native显示socket，因此该观察socket的reply为空、没有binary不等于native无播放。本量具未采native最终DOM或完整文字输出，不能宣称角色逐字转述或全部语义都通过。

宿主同场记录两个ASR片段（93字 / 9字）和两次Study调用：自然停顿分轮仍需检查；不能凭71帧或161响声就认为长句通过。第一工具开始01:50:02，完成01:50:06.977，首audio.delta01:50:09；第二工具开始01:50:38，完成01:50:42.388，首audio.delta01:50:44。当前日志足以指出第一段工具约5秒、工具后首音频约2秒；固定输入end=23.828s、loopbackfirst_loud=25.25s各自相对时间基准不同，未额外校准前不能相减声称完整延迟。下一步补同步时间线和自然停顿专项，不改普通barge-in门槛冒充优化。

Native直接看图仍不可靠；图像教学依赖Study。密集小字及部分连线措辞仍PARTIAL。受控surface已验，任意桌面编辑器定位未实现。

## 额度、部署、当前进程和下一步

同轮 `bargein-autocheck-20261012` 从271/30/0到302/32/0：DeepSeek新增31、Lanlan.app CONNECT新增2；累计cap2000/null/0，spent从未重置。这是请求计数，不是金额。

本轮隔离部署23个canonical product文件曾23/23匹配；最新最后几项入口与point精简之后应再部署刷新manifest。测试host/native/surface已在fixed场景结束清理。共享ledger保留。原master脏树、.workbuddy、Sky Scout源码未重置或提交。Sky Scout已授权隔离测试store，实际git7aae20f/221前缀内文件；既有父级索引同步，没有在Sky项目重建索引。

已创建附加隔离worktree `C:\Users\Shmily\.codex\worktrees\daily-companion\LiveTutor-Lab`，从已验证远端教学提交1fa40f4开始。只复制必要依赖闭包后审查，再在codex/分支commit/push；不发布local master历史、密钥、学习DB、录音或无关改动。

接下来继续B分轮/时延、D源码与角色指示闭环、F连续学习/断网恢复与日常入口实际启动；准备集中10–20分钟真人验收。单项限制不结束Goal。
