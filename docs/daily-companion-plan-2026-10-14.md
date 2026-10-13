# LiveTutor / N.E.K.O 日常学习伙伴长期执行计划

本 Goal 已创建并 active；不因单项完成或单线路阻塞而结束。用户要求 GPT-6.1 Sol / High；当前工具上下文未暴露本窗口模型配置，未自行切换。

执行契约（原始完整任务说明）：[daily-companion-contract-2026-10-14.md](daily-companion-contract-2026-10-14.md)。本计划和状态不是契约替代品。

现有 Goal 绑定：thread `01a13531-0341-7611-afc2-5c472a7ccf50`，status `active`；该 Goal 的执行依据就是上述 contract。内置 Goal 更新工具仅支持状态，未改 objective、未重建 Goal。已在同一 Goal 的执行上下文与接续记录明确引用完整路径；Bridge Goal 工具 schema 无法接受 get，未进行任何写入或预算变更。

每次上下文压缩后或自动续跑开始时，必须先完整读取 contract、plan、status、blockers，再继续工作。后续用户明确指令优先；同步更新对应记录，保留原 contract 原文与变更轨迹。关键约束：沿用账本不重置、夜间不采房间麦克风、局部阻塞继续其他任务、完成依据实际证据。不得重建现有 Goal 来替代接续。

## 接续与边界

已完整读取 2026-10-14 图像 checkpoint、2026-10-13 教学 accepted、2026-10-11 源码教学、2026-10-10 产品记忆报告。已验收真人普通打断、基础教学、真实模型教学/评分/续课、CodeGraph 和 Study 图像闭环作为继承证据，仅改动相关链路或发现回归时重验。Native Realtime 直接看图可靠性未过，不作为当前图像入口。

保留当前 master 脏树、未发布图像修复、.workbuddy 与原用户历史。Sky Scout 只读。夜间只用固定输入、输出回环及已设音量，不采房间麦克风，不提高音量。只有主 Agent 可改共享账本、安排在线音频。最终真人验收等待用户明确“准备好了”。

## 工作阶段

| 阶段 | 输出 | 验证与依赖 |
| --- | --- | --- |
| A 入口与材料 | 固定日常 store、持久课程与配置、就绪/错误提示、图片入口、Study 图像接角色 | 冷/重复启动、换图/换课，真实模型及输出回环分层 |
| B 语音教学 | 语言记忆/临时切换、长句停顿、术语口语、分段延迟、纠正后重查 | 固定语音与时间线，普通打断仅必要回归 |
| C 学习记忆 | 现有 SQLite 明确偏好、历史取用、稳定 topic、续题/返课 | 临时 SQLite/重启、真实模型定向验证 |
| D 真源码 | 复用授权/CodeGraph、版本/引用/流程/影响 | 既有证据继承；受影响范围定向验证 |
| E 指示 | 先受控 HTML/图片指点，高亮/箭头随布局变化 | 核许可证与源码，global web-inspector 截图/布局检查 |
| F 交付 | 连续学习、替换、重启/断网恢复、说明与 codex/ 分支发布 | 审查密钥/学习数据排除，10–20 分钟集中真人体验 |

## 接续文件

- `docs/daily-companion-status-2026-10-14.md`：当前阶段、证据、额度、进程、下一步。
- `docs/daily-companion-blockers-2026-10-14.md`：局部失败、尝试、恢复条件；单项不阻塞整个 Goal。
- `docs/evidence/daily-companion-memory-2026-10-14.md`：记忆 Agent 独立阶段证据。
- `docs/evidence/daily-companion-guidance-2026-10-14.md`：指示 Agent 独立阶段证据。

## 文件分工

主 Agent：launcher、host、native shell、study_avatar_tools、__init__、新集成/预算/音频验证及 manifests。记忆 Agent：context/question/summary entries、llm_prompts、prompt_templates、新 learning_preferences 与对应测试。指示 Agent：仅新 neko_learning_surface 前缀文件与对应报告。共享文件由主 Agent 整合，最多两名子 Agent。

每实质阶段同步交付、证据层、剩余、预算、进程、下一步。完成判据是实际可用交付与证据；人工未验收保留待验收。

阶段二已完成A图片UI/课程竞态、C偏好接续、E受控HTML/图片/过滤源码指示，真实图像后端与设备路线分层补证；B长句代理MANUAL支持实验未通过，保持局部任务。使用与集中验收见 `docs/daily-companion-use-2026-10-14.md`。下一步独立worktree codex/阶段发布后，继续B/D/F未验收部分。两个子Agent当前已完成，无共享文件并发修改。

后续阶段：第一阶段已发布3c2bc065；晚ASR本地scope竞态增量离线/部分设备补证，真实role源码指示→DOM→音频通过但仍两片提前动作；本地503实际SDK/DB失败恢复通过。原英文刺激三句及MANUAL后续tools更新混杂已修正历史推断。此阶段增量发布后，主线优先B：受控Study付费工具及point准入必须同时考虑最后speech静默、最后ASR接收时刻和host callback ready，保留普通onset/cancel与连接/scope隔离；方案/证明边界见spoken-turn-analysis，不以单一请求计数代替完整约束正确。任意桌面指示/密集图/新能力真人仍待验；只读Sky Scout与原历史继续保留。

当前接续：465da5b第二阶段已发布，B opt-in all-Study准入仍默认off。实际point adjacent6通过单固定指令；图片gated7暴露旧prefix升格和重复paid工具，最新限制200ms邻接ASR接续、14/6/5离线过后进行neighbor8单场。不把candidate检查/英文形状当完整语义或真人通过。D真实文字结构/file窗口/纠正续问补证，保留值写反与缺key混淆、超出两句的模型失败；最新persona短答/事实规则源码修正待实际确认。先核本场结果与清理、更新证据和范围；在同managed worktree提交必要B/D增量，再继续B延迟/术语与F多轮日常整合。旧status全文存evidence/status-history，压缩仍先读取当前四文件，不大范围扫描。

neighbor8补证仍PARTIAL（旧prefix拒绝、中文实际播放，但重复三次/英文失败），432/45/0、场景已终止；新一次language schema/检测/临时解释锁4项离线过。阶段三发布后继续最终ASR重复工具及result/audio owner离线复现、必要英文设备补证与F连续日常操作，不重复已验旧教学/图片题/503。集中真人未做保持pending。接续规则和完整contract不变。
