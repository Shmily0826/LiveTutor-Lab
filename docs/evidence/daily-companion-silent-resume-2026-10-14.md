# 静音恢复阶段：源码与离线交付

用户最新指令为不发声、不使用麦克风并恢复原 Goal。已完整读取 contract、plan、status、blockers；contract 原169行及SHA256保持不变。用户在界面恢复后，get_goal 已核实原 Goal01a13531-0341-7611-afc2-5c472a7ccf50 为 active，不重建。

## 已交付

- phrase uplink 每个分块自行生成 UUID wire event_id，冻结 wall clock 的两段、多分块实际 Core/Omni/local socket 检查通过。不改变 provider utterance 身份，不声称已发现供应商去重事故。
- 记录原输入、输出、压缩零样本、成功写入样本以及 seal/queue/first successful write/completion 时点。输入结束/封口仅 arrival-derived sample estimate，非物理捕获时钟；发送耗时使用 monotonic，日志不含PCM、识别文字、owner token、请求payload。
- `scripts/test_neko_phrase_input_transport.py` 17项通过（8.770s）。helper指纹为aa27c5ce56cf6c9cf0061acb0dead4e0d59c3f1ffb1983cbc9f1d193f1edb0b1；仅更新该helper指纹，不改变其他host文件。verify_source_audio_gate通过，没有启动宿主。
- 图片纠正支持明确material_source=auto/current_picture/literal_text。自动裸纠正只接续同boot、同角色输出目标、同课程/会话/材料身份且最新已有interaction仍是相同材料解释的情况；使用现有SQLite一条记录，忽略旧summary并重新附当前像素。未知、换图、換文本、换课、换会话、其他角色或后续源码解释时要求明确对象；不付费、不写新学习记录。
- 来源不明时的明确提示与服务不可用区分；literal源码/笔记保持独立；模型不能用source参数推翻学习者明确拒绝图片。原全链材料替换guard继续生效。
- 5项新增来源检查先复现失败（2个FAIL/10个subcase ERROR），修复后原14项及本阶段新增检查共20项通过（2.586s）；单次语言原4项通过（0.333s）。这是路由/SQLite/假模型检查，不是PNG视觉正确率。
- 已同步canonical wrapper到固定daily plugin-code，26/26完整相对路径指纹通过。最初验证脚本误以basename展开UI子目录，检查报不存在index.html；修正验证路径后全26匹配，未改UI子目录或用户数据。
- 常用启动入口新增任务音频拒绝检查：Native launch、产品UI启动/浏览器、voice host/probe、loopback枚举/录制/自测在设备初始化/进程创建前拒绝。PortAudio import移到guard之后。`NEKO_TASK_SILENT=1`或本地任务policy的audio_allowed=false任一生效；无效policy拒绝。4项实际入口检查通过（0.023s）。
- 当前本地policy `benchmarks/raw/daily-companion-audio-policy.json` 为false，保留于ignored task raw；普通环境无policy时不改变现有入口行为。未来恢复声音设备须另有用户明确授权，不能靠audio_input假设备、mute或environment=0覆盖拒绝。

## 支持边界与后续

以上SOURCE/OFFLINE通过，没有本轮真实模型、ASR、Native、设备或真人新证明。自然停顿仍默认OFF；handoff整段bypass限制不变。密集“未”字仍需一次必要的纯文字/图片后端复核，不能把正确附图称为已看清。Native角色真实选新source参数与真正听感未验。

静音guard是本任务受控入口的防误启动，不是Windows全局禁音，不控制其他程序，也不能声明所有独立旧测试入口均已覆盖；自动接续依然先读四记录并按静音allowlist操作。

恢复实核ledger为bargein-autocheck-20261012，DeepSeek581/2000、Lanlan.app56/无固定累计上限、Lanlan.tech0/0。上述离线工作没有供应商调用，没有声音设备/录音/回环；原用户历史、Sky Scout源码和无关脏树保留。

阶段九仍未发布；完成静音文字/材料集成及允许范围复审后只push既有codex功能分支。整个A–F Goal继续，局部声音验收待授权不构成全局阻塞。
