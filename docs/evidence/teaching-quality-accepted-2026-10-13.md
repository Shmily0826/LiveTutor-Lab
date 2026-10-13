# 教学闭环：本场真人阶段验收通过（2026-10-13）

最新完整Goal已完成，详见[最终验收](teaching-quality-goal-accepted-2026-10-13.md)。本文保留本场真人体验的历史范围；后续自动验证与最新修复有独立证据，不将它们合并成新一场真人体验。

用户先明确“准备好了，现在开始”，随后确认“已完成：声音、出题、判错和纠错都正常”。启动时实际界面无教程、无人格提示，麦克风关闭；确认工具就绪后才开真实 AMD 阵列麦克风。完成反馈后立即关麦并清理。

本场角色调用了实际 study_quiz 与 study_answer；Study provider audit各有1个完成请求。题目是“在 Python 函数中，Python 如何决定函数调用后返回给调用者的值？”用户答“通过 return 吗？我不太清楚”，工具保留为“通过 return 吗？我不确定”。实际评分 partial/55，反馈指出 return 方向正确但缺少没有 return 默认返回 None；不是把本场伪称成 wrong/0。疑问语气在反馈中被提到，后续评分质量检查应确认它不会独立成为扣分依据。

## 证据核对

- final-human-events.json：用户确认、68条本场事件、109条真实播放反馈，其中105条audible=true。
- final-human-db.json：实际出题、评分与最新QA记录。final-audit.json核对该QA题目对应本场题目，反馈对应本场评分，页面实际语音文字与题目/反馈一致。
- 真实后端完整闭环仍见teaching-quality-20261013-results.json：解释/加法例子、出题、完全重启后继续未答题目、已知错误0分、针对误解纠正、新题正确100分、总结以及再重启后回忆具体旧误解。
- 真实回调切课：切数学记录0条，返回Python恢复同课程wrong/correct两条记录。
- 19个product文件哈希及部署字节重新验证。两个宿主各10个可靠性补丁目标；9对文件一致，tts_runtime的源宿主额外dev_text_only门禁差异是预期的，另由host manifest验证，不能声称两树所有文件完全相同。
- 本轮重跑：19个实时语音回归、2个overlap/迁移用例、生产JavaScript取消/解码/重连用例通过。此前真人普通打断的用户确认仍保留；本场教学没有要求再做插话。

## 额度和清理

本场本地出站累计预留计数DeepSeek120→140/150，Lanlan.app15→16/18，tech0。只有2个Study请求，其余包含宿主请求/出站连接预留；这些计数不能当作账单金额。整个教学Goal从60/11起，累计新增80/5；账本未重置、未换轮。宿主清理stuck=[]、left_over=[]、host_log_still_advancing=false，角色壳关闭；原学习历史与脏工作区保留，未提交/推送。

本场成功的历史启动形状（不应未经当前账本/用户准备核对自动复测）：

```powershell
& benchmarks/raw/neko-product-host/.venv/Scripts/python.exe -X utf8 -u -B scripts/neko_desktop_tutor_host.py --source --voice --core-provider free --store neko-teaching-quality-20261013 --hold 600 --seconds 220 --api-budget 30 --egress-budget 150 --allow-host www.lanlan.app:18 --budget-round bargein-autocheck-20261012
& benchmarks/raw/neko-product-host/.venv/Scripts/python.exe -X utf8 -B scripts/neko_native_shell.py --store benchmarks/raw/neko-teaching-quality-20261013 --chat-surface compact --cdp-port 9227 --wait 60
```

## 当前边界与用户最新安排

基础真人教学场景PASS。后续固定13秒长句验证已完成一次真实语音解释与跨心跳播放，详见[最新进度](teaching-quality-progress-2026-10-13.md)：4个识别片段合并成1次工具解释、完整语音文字与数据库一致、无提前关闭。精确两句话实际仍为三句话；旧voice owner被新独立socket替换的分支仅离线通过。完整Goal仍active；本场并不证明跨播放结束真人插话或长期稳定性。

用户澄清：以后可能不能亲自读音频测试内容，但允许电脑外放；不需要声纹或识别谁在说话。后续自动输入可用固定wav/本地TTS，经实际语音入口送入服务；输出可外放并使用WASAPI回环观察。无需把用户安排为每一轮的朗读员。真实硬件与合成夹具证据仍分别记录。

图像问题的当前源码/配置结论：指定窗口截图复用RapidOCR模块，默认rapidocr；当前llm_vision_enabled=false，角色study_read_window主要转交OCR文本。项目已有study_submit_image以及根据含图消息选择vision组的网关，架构图应优先复用这些入口，把原图送给可用视觉模型并测试箭头/关系；不能把OCR标签解释当作架构图视觉理解验收。本次未进行任何视觉provider调用。
