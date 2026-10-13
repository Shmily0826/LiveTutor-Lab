# 后端网络失败恢复：量具已就绪，真实 SDK 场景待主 Agent 执行

已完整承接 contract / plan / status / blockers。当前阶段仅新增 `scripts/neko_daily_failure_probe.py`、`scripts/test_neko_daily_failure_probe.py` 与本报告。没有修改共享源码、static、surface、日常配置、用户数据库或共享账本；没有启动宿主、在线模型、角色、音频或房间麦克风。

| 层级 | 当前结论 |
| --- | --- |
| 本地 HTTP stub / 隔离守卫 | PASS，7 项离线测试 |
| 实际插件 / SDK / DB 故障恢复 | **待执行**；量具已准备，不以 stub 自测代替真实后端结果 |
| 在线模型质量 / 设备播放 / 真人体验 | 未测，本场景不需要且不会调用 |

## 当前源码约定

已核对 current overlay 和部署的 stock 依赖：

- `study_model_gateway.py::_call_generic` 使用现有 host LLM factory、`max_retries=0` 和同一请求 deadline。HTTP 503 / 连接失败分类为 `provider_unavailable`；429 为 `rate_limited`；timeout、凭证失败、配置错误与本地额度拒绝另行区分。本量具不会把本地 stub 换成任何付费供应商。
- `entry_tutor_context_support.py::_finalize_tutor_call` 对 `reply.degraded` 只更新错误状态并返回 payload，不追加教学 interaction、不调用知识记录、不把 fallback 题目写成 live current question。
- stock `entry_tutor_answer_entries.py` 对降级评分释放 `attempt_evaluation_pending`，保留 pending question，再持久化状态；只有正常结果才标记 attempt evaluated、写知识 / 评分。
- `study_avatar_tools.py::_teaching` 把失败设为 `status=unavailable`，移除 question、hint、question_id、attempt_id、score、verdict，要求角色只转述明确失败句并停止。本量具实际 callback 将检查这份角色契约，而非仅看 HTTP 200。
- current UI 出题 / 评分的 `data.degraded` 分支显示 diagnostic 并刷新，提前 return，不更新生成题目 / 评分展示。上轮真实 DOM 网络恢复证明入口保图与主动重试，但不证明 backend 503 不写假评分；本阶段为这一证据缺口准备量具。

SDK 原始降级 payload 可能含内部 fallback 字段，因此不能把原始 HTTP 成功或 heuristic score 当作真实评分。必须结合 degraded、角色输出字段与 DB 事实判断。

## 注入方式与隔离

`serve` 只启动 127.0.0.1 随机端口 HTTP stub，并创建全新的 `benchmarks/raw/neko-failure-*` 目录 / 所有权 nonce / manifest。默认返回 503。控制端点需要随机 token；token 只保存在任务 manifest，stdout 不输出。模型端点只接受硬编码的非真实 dummy key，任何其他凭证立即 401 且不记录；日志只保存请求 hash、message 数量、mode 与时间，不保存 headers、API key 或 prompt 正文。

stub 支持 `http503`、断开连接的 `drop`、三个明确标注“本地量具”的成功响应。默认最多 16 次模型 HTTP 请求，超过后 429 + Retry-After 3600。成功内容只验证协议与存储，不能证明教学质量。沿用已有 OpenAI-compatible gateway；不新增模型架构 / 供应商。

`launch-plan` **只输出待审查 argv，不执行它**。拟由主 Agent 启动的独立进程在内存中：

1. 把 `read_key` 替换为 dummy key，避免读取真实 key 文件。
2. 把 existing `agentModelUrl` 指向 stub `/v1`，使用新 store 的现有配置槽。
3. 把 existing Sink 构造改为 **外部额度 0**、没有额外 allowed hosts，并把 cap_file 指向该 store 的 `local-deny-egress.json`。这只是本地量具的 deny sink，不是对共享 `bargein-autocheck-20261012` 账本的重置 / 替代。真正外部调用为 0；共享账本前后 SHA-256 必须不变。
4. 跳过源码补丁重放，保留当前已部署补丁及现有 audio gate 检查；text-only source host 不创建 native shell / 音频会话。

启动会生成 host 的正常任务 PID / log / 部署证据，故必须由主 Agent 检查固定端口空闲、记录该 host 归属并负责关闭。子 Agent 本轮没有执行此计划。main 内存 monkeypatch 不修改共享脚本文件。

`run` 仅连接已经由主 Agent 启动的隔离 host。执行前核对 manifest nonce、store 必须是本项目新建 `neko-failure-*`、DB 必须位于这个 store 且名为 `study_companion.db`、core config 确为 loopback + dummy key、DB 没有旧 interaction / 评分 / 题目、实际 status 课程与隔离 DB 一致。它还确认 stub 尚未收到其他模型 traffic、共享 ledger 从 stub 建立时未变。配置 / DB 检查本身不是 PID 归属证明，端口与进程归属仍由启动者确认。

所有 DB 检查使用 SQLite `mode=ro` + query_only，连接显式 close。量具不会直接写、清空或重置 DB；fixture 状态由真实 SDK / callback 方法建立。只读取该隔离 core config，不读全局或原用户配置；只比较 dummy key，不把配置内容输出。

## 主 Agent 审查后的有限场景

```powershell
python scripts/neko_daily_failure_probe.py serve --store-name neko-failure-20261014-scene1 --hold 600
# stdout 给出 manifest 路径和 stub PID，不给 token。
python scripts/neko_daily_failure_probe.py launch-plan --manifest <manifest绝对路径>
```

审查输出的 cwd / argv / environment 后，主 Agent 单独启动该 argv；不能把“打印计划”当成宿主已运行。host 实际就绪并确认唯一进程归属后，找到这个 store 的真实 Study DB，再执行：

```powershell
python scripts/neko_daily_failure_probe.py run --manifest <manifest绝对路径> --db <该store内真实study_companion.db路径> --output D:\CODE\project\LiveTutor-Lab\benchmarks\raw\evidence\daily-companion-failure-recovery-sdk-20261014.json
```

量具只运行一次，不覆盖已有输出、不自动重试失败场景：

1. 通过真实 SDK 新建隔离课程，stub 成功生成一题，取得真正的 question / attempt ID，并读取 DB baseline。
2. stub 切到 503；实际角色 callback 分别请求讲解、出题、评分。每次必须 degraded + unavailable、没有新题 / 分数 / 判定。interaction、qa_records、mastery、wrong_questions、FSRS 行数不变；原 pending attempt 保留，未消费、未留下 pending 预留。
3. stub 显式恢复为评分响应；同一原题 attempt 可再次评分，qa_records 恰好 +1，attempt evaluated。该 100 分是量具预置返回，不代表真实模型判断。
4. stub 恢复讲解响应；新的请求能走真实 gateway / callback，再返回带“本地 HTTP stub”标记的结果。
5. 收集真实 callback 输出、每步 DB、stub 请求记录和 shared ledger hash；恢复 stub 默认 503。实际 host 由主 Agent 清理，serve 在超时或 Ctrl+C 后关闭自己。

`PASS_REAL_BACKEND_LOCAL_STUB` 仅在上述实际 SDK / DB 事实全部满足后输出。尚未执行时不得引用该预设名字当作已通过。失败 report 保留每个已完成步骤，主 Agent 根据实际结果修复或记录局部阻塞，不把它变成整个 Goal 的阻塞。

## 离线验证与剩余

```powershell
python -m unittest discover -s scripts -p test_neko_daily_failure_probe.py -v
python -m py_compile scripts/neko_daily_failure_probe.py scripts/test_neko_daily_failure_probe.py
```

7 项通过：真实本地 HTTP 503→成功、request cap / Retry-After；非 dummy 凭证拒绝且不记录；control auth 与外网 / 带凭证 URL 拒绝；失败契约拒绝伪分数 / 题目；只读 DB 保题 / 行数且文件 hash 不变；launch-plan 在 mocked host 中验证 dummy key 与独立 cap_file，未执行真实 host；错误 nonce / 越界证据路径在任何 host 调用前拒绝。语法编译通过。

首次 DB 自测发现 SQLite connection context manager 不会关闭连接，Windows cleanup 被锁；已改显式 closing 并通过。自动审查拒绝递归清理任务临时目录，随后仅对已确认的单个任务 DB 文件和空目录做非递归清理成功，不触及任何用户数据。当前本子任务 HTTP 服务 / 测试进程已结束。

剩余：主 Agent 审查并执行实际隔离 host 场景，填入真实 SDK / DB 结果、请求数、shared ledger 不变证明和进程清理。真实自然网络断电、生产服务限流、人耳体验未覆盖；本阶段精确覆盖现有 gateway 收到失败并恢复的协议 / 状态边界。若 gateway 还有多阶段内部请求，stub 会逐条记录，不把既有分类 / 纠正阶段误称为重试；最大 16 条防止无界量具流量。

本轮外部请求 / 在线音频均为 0；没有修改共享预算、供应商、日常配置、已发布分支或任何原历史。

## 主线实际 SDK / DB 执行补证

主 Agent 已审查launch-plan并在固定端口空闲时创建唯一 `neko-failure-20261014-scene1` 隔离store。实际source宿主就绪后执行一次run，结果 `PASS_REAL_BACKEND_LOCAL_STUB`。证据：`benchmarks/raw/evidence/daily-companion-failure-recovery-sdk-20261014.json`，清理：`daily-companion-failure-scene1-cleanup.json`。

三个503教学callback均明确 unavailable，字段不含新题/分数/判定；每步DB计数与baseline相同，原attempt保留、未评分、pending预留释放。显式恢复后同一attempt被评分，qa_records恰好+1，下一次讲解返回本地stub标记。实际stub收到8次请求，无非dummy凭证、无付费provider或audio。共享ledger SHA前后同为 `4f0b898e8ba77d168af6ee37d588101f833e2c612b8233ae306b317581e4b85a`，344 DeepSeek / 38 app / 0 tech未变；ledger不是这个本地stub的计数器。

由主线持有Popen对象关闭本次host及其子进程、stub；原用户数据库未读取/清空/重置。结论升级为实际SDK/DB局部故障恢复通过；真实模型质量、实际网络断电、设备播放和真人体验仍未由此证明。Goal继续B/D/E及集中体验。
