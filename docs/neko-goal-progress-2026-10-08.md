# N.E.K.O 本轮接手记录（2026-10-08，交接暂停）

本记录对应“真实 Study 带学链路验收＋awareness 修复验证” goal。用户要求本轮收尾并交给另一 agent，目标未全部完成；下述“通过”仅限明确列出的样本和运行层次。本轮没有 commit/push，没有升级或替换整个安装包，没有主动启用麦克风。接手入口为 `docs/neko-handoff-2026-10-08-goal-wip.md`。

## 版本与部署方式

- Lab 接手基线：`65beaf6b3e4049b6c71c4fa3cbd4353c44e50164`。
- 候选源码：`1d814cf32fba8c02b5727d2890710e4e7b8ece24`，工作树干净。
- 实际后台为 Nuitka 冻结的 Python 3.11 程序；不能把候选源码行号、版本或旁置 `.py` 修改当成正在执行的代码。
- 先在 `benchmarks/raw/goal-isolated/` 修补和验证；运行环境改用显式源码入口，配合两个插件导入根中的同名源码，以及 Study 子进程的临时循环兼容层。原始文件、插件 manifest 和原始 Study 数据库均有本地备份。
- 当前临时兼容层是实验性部署方式。正常源码构建应采用 `patches/neko-study-2026-10-08/host-loop.patch`，不能把兼容层当作正式发布方案。

## 已获得的真实 UI 证据

固定材料为 `benchmarks/materials/study-chain-rule.html`，只包含人工编写的链式法则内容，标记 `NEKO-LAB-20261008`。

| 环节 | 本次结果 | 样本耗时 |
| --- | --- | --- |
| 屏幕输入 | 在 Study 明确选择“整个屏幕”，核对桌面前台确为固定材料后，识别到标记、链式法则和 sin | 6.238 s |
| 直接解释 OCR 输入 | 正确说明 `y=sin(x²)` 的内外层，给出 `2x cos(x²)` | 3.700 s |
| 连续追问 | 勾选“沿用上一轮解释”，沿用上一轮 `(2x+3)³`，给出 `6(2x+3)²` | 5.684 s |
| 出题 | 通过原生 Adaptive Practice 生成 `y=(3x+1)^5` 求导题 | 6.161 s |
| 错误答案 | 同类链式法则新题中，“答案是 42”得到 `WRONG / 0`，反馈具体指出缺失步骤 | 7.648 s |
| 正确答案 | 新作答 ID 下提交完整推导，得到 `CORRECT / 100` | 5.617 s |
| 学习记录 | 只读 SQLite 核对新错误、正确记录分数与不同题目/作答 ID，未删除历史 | 已通过 |

原“选择区域”入口仍报 `capture_busy`，不是选择区域验收通过。新增全屏选项由使用者明确选择，保留默认选区行为并提示会读取其他可见窗口。

一次全屏尝试采到其他前台窗口，已判为无效；浏览器的 `bringToFront()` 只切换标签，不能替代 Windows 前台窗口核对。随后用 Windows 工具激活本轮材料窗口并核对实际画面后，才取得上表的成功样本。原始证据留在 ignored 目录，不上传未经整理的屏幕内容。

质量限制：OCR 仍会混入可见的 N.E.K.O 对话浮层；该样本首次解释未应用知识图谱，追问恢复了 semantic routing。数学结果正确，但追问中“假设内层不变”等措辞不严谨。几个正确样本不代表评分器或教学语言已达到广泛可靠性。

正常角色聊天与 Study 操作仍分开判定。本轮在额外浏览器打开同一角色页面的发送出现 `Send failed`，已关闭该测试页面并确认桌面 capture health 恢复；不把这个额外客户端失败直接判成正常桌面角色聊天失败。此前 handoff 的唤醒态角色聊天 PASS 仍是此前的结果。

## 修复前评分坏记录

修复前的真实 UI 曾将 `sin(x²)` 题的“答案是 42”判为 `CORRECT / 100`，并提高掌握度。数据库记录 `interactions.id=24`、题目 `q_13a3d8aeaed84b389e6afc4d7fc574ff` 留存。

源码压力测试独立证明：上下文压缩会丢弃后插入的 `answer` 等必要字段。修复保护题目、学生答案和参考答案，必要内容本身超出预算时拒绝评分。实际坏分是否完全由这一条原因造成，仍不能仅从压力测试下结论。

修复后的记录：`id=29` 是错误 0 分；`id=33` 是正确 100 分。前后题目不同，属于实际样本复测，不能替代相同题目的大规模评分回归。坏记录及其掌握度影响未被抹去；当前掌握度含本轮合成测试影响。

## Awareness 与消息平面证据

1. 旧设置入口没有解析 awareness 分支，源码回归复现并修复；现在公共设置入口可以解析、规范化开关，并实际启动/停止循环。
2. 正式宿主的 startup 后台任务会被取消：成功启动的测试插件在约 15 ms 内观察到任务取消。宿主分阶段使用 `asyncio.run`，消息队列还出现了绑定到另一事件循环的实际错误。
3. 复用进程生命周期事件循环后，实际测试插件后台计数从 6、13 增至 21，多个入口调用期间仍存活。
4. Study 实际启用 awareness 后出现持续完成 tick 与截图观察，`sensor_available=true`。原先连续 39 s 的配置复现样本中 sensor 为 false、消息为零。
5. 正式嵌入宿主只有 request router，`_message_plane_runner` 为 None；启动 delivery 所需组件后，消息平面绑定、接收和 proactive bridge 均出现运行日志。
6. 后续暴露 watcher 的同步启动被放在异步循环中执行。改为工作线程后，实际 `command_subscription_active=true`、`subscription_retry_active=false`。
7. `respond` 样本在 19:58:56 有 `proactive bridge forwarded`，主程序也记录提交到 delivery manager。角色界面最终展示与该 awareness 消息的关联尚未完成，不能只靠 forwarded 判定全链路完成。
8. 完整后台冷启动后的第一 Study 实例持续运行：`completed_ticks` 和 `captured_observations` 从 12 增到 13，订阅 active、retry false；验证结束恢复原 awareness 配置且运行循环 inactive。此时分类是 `other`，不是正确识别学习材料的证明。
9. 超时、降级及恢复已加入组件回归；晚到的 watcher 启动也会停止清理。运行状态区分 `submitted` 和真实投递。旧 HTTP `/plugin/messages` 返回零不能当作消息平面没有消息的证据。

新增 runtime 指标区分 `completed_ticks`、`captured_observations` 和最后分类；不再把 supervision 的 `last_activity_at` 或 `recent_classifications` 当作 tick 计数。

## 本地复现与回滚

所有命令从 Lab 根目录执行。诊断 Python 为本轮隔离的 Python 3.11，位于 ignored 的 `benchmarks/raw/goal-python/`；新 clone 没有该运行时、安装包、用户数据库或截图。

- 源码回归：`scripts/test_neko_lab_regressions.py`，目前 14 项通过。包含评分上下文、超预算拒绝、私有字段过滤、配置、读取超时、订阅恢复、同步 watcher、循环生命周期、冷导入兼容层和 OCR 入口约束。
- 前端逻辑：`node scripts/test_neko_lab_followup.js` 与 `node scripts/test_neko_lab_ocr_ui.js` 均通过；它们验证上下文序列化、显式截图模式及 busy 不回退，不代替真实 UI 结果。
- 公共入口：`scripts/neko_lab_client.py`，默认只输出筛选后的 Study 状态，禁止改成读取主模型凭据的工具。
- 真实 UI：`scripts/neko_lab_ui_step.py`；OCR 全屏用 `ocr --fullscreen`，解释已有 OCR 输入用 `explain --current-input`。先确认 Windows 前台和固定材料；不要仅依赖标签切换。
- 可逆 awareness 样本：`scripts/neko_lab_live_awareness.py`，默认 `read`；`--mode respond` 会触发真实主动消息测试，结束后恢复原 awareness 分支。
- 数据库证据：`scripts/neko_lab_verify_records.py`，只读，不恢复或修改数据库。
- UI 回滚：`scripts/neko_lab_deploy_ui.py --rollback`。先校验部署后哈希，拒绝覆盖外部修改。
- 后端源码回滚：`scripts/neko_lab_deploy_source.py --rollback`；随后重启已确认归属的后台，清掉内存中的兼容层和导入缓存，再启动原始 Study 入口。UI 是独立备份，按需单独回滚。

严禁用初始完整数据库备份覆盖当前数据库：那会抹掉后续学习记录。回滚代码与配置应分开执行。

## 交接时状态与剩余验收

- 冷启动持续 tick、消息平面与订阅已通过上述运行样本；源码正式集成仍未完成。
- 在角色唤醒态，关联一次新 awareness 消息与最终角色 UI 展示，而不是只看桥接日志。
- 选择区域仍失败。最新严格选区不回退、截图模式元数据已通过组件测试；需补实际桌面复测。
- 新 OCR 模式控件初次桌面截图出现局部裁切，单项 grid 修正后 desktop/mobile 浏览器检查控件可见、无页面错误。实际桌面最后阶段曾不可交互并观察到 LogonUI；不要把窗口激活失败误判成应用缺陷，接手重新核对桌面状态。
- 文档、补丁和脚本已整理；原始屏幕、旧配置、模型相关上下文继续保持 ignored。原始错误评分和新记录都保留。
- 语音听感、现场麦克风、打断留给用户回来后；本轮未验收。
