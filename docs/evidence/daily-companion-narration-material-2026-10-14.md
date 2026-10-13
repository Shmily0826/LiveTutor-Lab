# Session summary 本地叙述 producer / queue 材料保护

日期：2026-10-14。先完整读取 contract、plan、status、blockers，承接已发布 `537e573` 与主线记录的 552/55/0、no online；没有直接读取/调整账本。现有 Goal active。本轮仅实现本地 producer/queue，不把局部交付视为整个 Goal 完成。

## 交付范围

仅新增 canonical overlays `payload/study_companion/entry_communication_tutor_events.py`、`_event_bus.py`（从现有部署 base 拷贝，保留其他事件行为），在既有 canonical `__init__.py` 的 `StudyEventBus` construction 增加一行同步 validator injection；新增定向离线测试及本报告。manifest、summary entry、StudyAvatar、材料 helper、host 和其他源码未修改。默认 communication OFF 的配置/条件原样保留。

1. summary helper 不再读取 live `session_summary_seed`。首次 await 前深拷贝入口传入 payload，要求明确 course/session subset、captured seed 和私有显式 target；获得插件状态锁后检查原 context，才构造 origin 和固定统计。缺少 provenance/目标/当前状态时不 schedule；不更改任何已保存 history，也不替 summary entry 伪造新 context。
2. 复用既有 `bind_material_output` 的 boot/seq/context 记录和材料通知目标。summary **不覆盖已有目标的 native image binding**，避免 course/session subset 使原图片的 photo-only 控制不再发送。尚未注册的明确目标才注册 summary subset；只换图片时，原 history summary 仍有效。
3. event bus 深拷贝 protected event 的 payload/origin，在 schedule、queue/semaphore/锁等待之后和 SDK push 紧前重新同步核对。未知 validator、异步 validator、异常、错误 boot、未来 seq、缺目标、未注册目标、未知 context、legacy 无 origin summary 或 unsupported event 的 origin 均 fail closed。stale 是正常 drop，不进入 worker failure/backoff；final push 前失效释放已 reserve 的 throttle/respond，不 commit 成功计数。
4. 来源仅进入 `metadata.study_narration_origin`，formatter/text/parts 不输出这些私有标识。非本分支的 timer/review/general/answer 等原事件保留既有行为；本交付没有为它们新增材料安全保证。

## Main 的精确接入接口（尚未越界修改）

在 `study_summarize_session` 首次 await 前从可信 kwargs `_ctx` 捕获 role，不能在 helper/drain 时取新当前角色或广播兜底。沿现有 narration 私有字典附：

```python
narration = {**payload,
             "_material_context": dict(expected),
             "_session_summary_seed": captured_seed,
             "_narration_target_lanlan": captured_trusted_target}
```

目标必须非空且最多256字符，course/session 也必须明确、非空且各最多256字符。helper 不从 UI public schema、模型文本或新的当前角色自行猜目标。缺目标仅不发独立叙述，不损坏正常 summary 的历史保存/返回。若已有 Native summary result 会自行朗读，是否同时安排独立 summary event 由 Main 明确，不能默认产生双重朗读。

输出供未来 host admission 使用：

```json
{"target_lanlan":"<explicit trusted role>","metadata":{"study_narration_origin":{"v":1,"boot_id":"<32 lowercase hex>","change_seq":0,"context":{"course_id":"...","session_id":"..."},"event":"session_summarized"}}}
```

私有 event payload 字段名为 `_study_narration_origin`，SDK metadata 使用无下划线的 `study_narration_origin`；context 严格只有 course/session，无图片身份。host 必须独立检查 bridge 派生 plugin/channel/source、目标和权威当前 producer/context；不能仅凭 metadata 或“没有新控制”放行。

## 本轮真实离线验证

执行：

```powershell
& 'benchmarks/raw/neko-product-host/.venv/Scripts/python.exe' -B -m unittest discover -s scripts -p test_neko_narration_material_guard.py -v
```

**14 tests PASS，0.106s**。测试加载 canonical 实际 event bus/material helpers 和实际 communication mixin class，并使用 base 实际数值归一 helper；受控锁/semaphore、假内存 push sink，不启动宿主/SDK endpoint，不访问数据库或模型：

- captured seed 与 live seed 不同，统计仍为原2题/50%，明确 target 和 metadata 正确，私有 course/session/boot 不进入 text；
- helper 等待插件锁期间换课，零叙述/零新注册；调用方等待期间修改 seed/context/summary，固定副本不被覆盖；
- missing/unknown context、target、seed 拒绝；
- 原 full-image binding 保留，photo-only material change 仍通知其 role，subset summary 同时有效；
- protected payload/origin/text 在 semaphore 等待期间被外部改写仍保持原副本；等候期间换课则 drop，worker failure=0，后续正确课程事件恢复一次；
- direct emit 等锁后换课拒绝；final reserve 后换课释放 throttle/respond reserve、emit_count=0、无成功 cooldown/throttle commit；
- wrong boot、future seq、missing/unregistered target、empty context、bool seq、wrong event、无/async/抛错 validator 均拒绝；unknown event 私有 payload 不进入 fallback text；
- unrelated timer 没有 validator/target 时保持原 respond 行为；close 后拒绝新事件。

3个 canonical 文件 AST parse PASS。相对原 base overlay 的窄 diff 已检查；root `__init__.py` 的旧脏差异保留，本轮自有增量只有 construction 的 validator 一行。没有编译缓存写入、原用户数据修改、宿主/音频/房间 mic、网络请求、供应商调用、额度变动或子 Agent。

## 证据与剩余边界

| 层 | 本轮状态 |
| --- | --- |
| 本地 producer/queue 源码与定向离线竞态 | PASS（14 tests + AST） |
| manifest/部署、真实 SDK metadata 透传 | 未执行，交 Main 整合 |
| host callback queue/claimed drain/hot-swap admission | 未实现，本地保护不能替代 |
| 实际模型叙述、已生成 Native owner cancel、设备播放/静音 | 未验证；不能借上一工具 owner 取消 |
| 真人体验 | PENDING |

最后校验保护的是进入 SDK push 之前。push 调用/await 之后在途消息、host 已领取队列、provider 已接受文字或已排 PCM，仍必须由宿主层精确 admission/ownership 处理；这次没有通过 holding plugin lock 跨网络掩盖该边界。默认 OFF 必须保持，不能因本地14项通过就启用完整独立叙述。

冻结：自有五文件已交付 Main；不继续修改其余 Phase 6 文件、manifest、host 或已冻结报告。后续最小步骤为 Main 私有 target 透传与 manifest 整合，再按既有只读 queue-review 处理 host 的权威 current/最终入模检查。
