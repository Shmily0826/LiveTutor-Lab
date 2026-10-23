# Narration：实际接口与权威 current / submit 契约

2026-10-14。已完整承接 contract、plan、status、blockers，并读取冻结的 narration-host-plan。当前阶段十 `c3cab4294fec75b30a20788ba035dc9ad289eeaf` 已发布；594/2000、app56、tech0及无活动宿主仅引用 Main 当前记录，本轮不查询、调整额度或进程。用户现在允许必要时已设约4%扬声器、仍禁止麦克风且未恢复回环；本任务只离线只读，没有设备、服务、SDK执行、模型/API、测试或新 Agent。唯一新增文件为本报告。root 与所读 `benchmarks/raw/neko-product-host` 均无 `.codegraph`，使用定向 rg。

## 结论

**实际 IPC 和当前运行实例对象足够实现一个小的权威 current adapter；现有 `study_status`、SDK config getter、旧 control/origin 都不能直接作为它。** 当前源码也没有贯穿 provider 提交的材料 permit。先交付权威读取、变更失效及完整拒绝路径可行，不需新队列/数据库；未接精确最终提交边界前，protected narration 正向 provider route 应继续默认 OFF / 明确拒绝。

这比旧计划明确了可复用的方法和真实缺口：不是缺通道，而是缺窄的原子 producer 快照、运行实例封装及有界提交协议。以下新接口名与 permit 均是**拟议契约**，不是已有实现或运行证据。

## 已存在的接口与边界

|源码|实际行为|用于 authority 的结论|
|---|---|---|
|base `benchmarks/raw/neko-app/resources/bin/plugins/study_companion/entry_status_entries.py:440–470`|注册真实 `study_status(locale='', **_)`，`to_thread(self._status_payload)` 后返回 `Ok(payload)`。|可以查 UI/诊断状态；没有 state lock 原子快照，不应为授权调用它。|
|canonical `payload/study_companion/__init__.py:1250–1290,1326–1327`|`_status_payload` 查 SQL 历史、知识/习惯并构造 awareness 信息；`_state_snapshot` 只返回 `state.to_dict()`。|二者均不返回原子 boot/seq authority；不是低成本专用 getter，也不应向 host 搬整份学习历史。|
|canonical `__init__.py:232–236` 与 `study_materials.py:14–35,49–78`|实例内随机 boot、递增 material seq、course/session/material hash 及精确 target map 确实存在；材料 setter 的 lock 内调用 `material_changes`，lock 外提交。|从这些现成状态投影即可，不重新查询 SQL、建记忆或从最后工具结果推导 current。summary 只需 course/session subset；photo-only seq 增长不应撤回它。|
|SDK `plugin/sdk/shared/core/context.py:249–295`|公开 config/profile getter、`query_plugins`、`trigger_plugin_event`，转发 host context。|profile/config/running 列表不等于学习材料 current。SDK 没有公开 producer 的这组原子 getter；不读取私有 `_current_lanlan` 或当成运行实例证明。|
|`plugin/core/host.py:2527–2553`，`communication.py:307–369,715–734`|`PluginHost.trigger(entry_id,args,timeout)`→同 comm manager 发送随机 req_id→对应 future→成功只返回 data，失败抛异常。|真实 request/result IPC 可复用，不必借模型 tool 调用或最后 tool owner；RPC timeout/异常/晚到结果均 unknown。|
|`plugin/core/host.py:1615–1728` 与 SDK `entry_runtime.py:52–95`|真实 async entry 调用经过 prepare kwargs、watchdog、handler/run/role scope；`Ok.value` 序列化进 data。|新增窄 entry 可以沿用这个实际链。主机生成角色与 nonce，不能信模型/普通请求自填 `_ctx`。|
|`plugin/core/communication.py:736–743`、`zmq_transport.py:443–478`|每 transport 认证上行，宿主覆盖 plugin_id；控制和消息消费者分离。|身份是该 transport 的 sender，不是 metadata 宣称的 sender；两条通道没有材料总顺序保证。当前没有 runtime generation stamp，延迟的旧 process 消息不能凭 plugin_id 自动接管新 boot。|
|`entry_communication_tutor_events.py:181–207`、`_event_bus.py:31–48`|summary 原 origin 有固定 boot/seq/course/session/event/target schema，并在 plugin lock 内 current 后 bind；本地 queue validator 可复用。|origin 是待核的证据声明，不是当前运行实例证明；现有 target map 是精确角色通知登记，不能当 narration provider output owner。|

## 运行实例怎样权威确认

`PluginHost` 实际拥有 `process`、`transport`、`comm_manager`（`host.py:2168–2237`），`is_alive()` 为进程 alive 且 exitcode None（2633–2637），`health_check()` 另返回 pid（2653–2681）。启动握手后的 applied config fingerprint（2381–2400）证明加载配置，不唯一标识一次进程；PID 会复用，plugin_id/entry 注册 revision 也不是启动 generation。

宿主侧新增 adapter 应在 **plugin-server 进程内**读取 `state.plugin_hosts`，捕获确切 host/process/transport 引用，调用它自己的 `trigger`，并在 await 前后重新检查同注册引用和 liveness。不要让 main-server 导入另一进程中的 `plugin.core.state` 后误认两者是同一对象。现有 main 远端工具通过 HTTP callback（`main_routers/tool_router.py:348–378`），说明跨服务 adapter 应有固定的受信内部通道，而非把插件 Python 对象带到 main。

权威检查用短的 registry 读锁或 uncached snapshot；拿不到锁为 unknown，不能沿用缓存。`state.py:374–395` uncached 超时返回空；缓存 TTL 0.5s，nowait 竞争时还会返回旧缓存（444–455,489–518）。普通列表/状态服务和 dispatch 的 cached snapshot 不是此处的最终 proof。

最小实例身份是 host 生成的随机非 secret `runtime_instance_id`，归属于实际一次 process/transport；RPC 返回由 server 封装，消息/control 也由同一 comm owner stamp，不能由 plugin metadata/调用者填写。引用检查发现 registry 替换、host dead、transport shutdown、nonce 不符，立即撤销该实例的确认。不得外传/打印现有 uplink token、模型 token或配置密钥。具体 host 注册/替换在 `registry.py:1767–1778,2151–2184` 和 `lifecycle_service.py:736–755`；生成身份最好放实际 host/process 创建点，而不是分散在卡片查询/每个 start HTTP response。

拟议只读 entry（例如 `study_narration_current`）只在现有 `_lock` 中复制 `{v:1,boot_id,change_seq,context:{course_id,session_id},ready}`；不 await SQL、模型、push，不初始化空 session，不持锁跨 IPC。实际 `ready`、boot 和 seq 来自实例；空 course/session、not-ready、类型错误返回 unknown。host adapter 回 `{runtime_instance_id,request_nonce,producer:snapshot}`，由当前实进程的关联 req_id 成功回复确认 boot，而不是 origin 首次出现建立 boot。该 entry 不作为 LLM tool/UI action 暴露，也不允许模型提供 adapter 地址、角色或 authority envelope。

intake 捕获显式 target 与 `_get_session_manager(target)` 对象（`character_runtime.py:794–799`）；adapter 返回后检查 role slot 仍指向同对象。成功确认只用于本次有限检查，不能永久缓存 True。origin.boot 必须等于这次 producer.boot，origin.seq 不大于当前 seq，相关 course/session 完全相同。旧 control 只能使已确认同实例变 stale；任意晚到新 boot/control 不能新建 authority。刷新失败不得恢复之前的授权。

## 所有生产 Core manager 构造点

定向检索所读 runtime 全部 Python 的 `LLMSessionManager` 构造，生产实际创建仅 `app/main_server/character_runtime.py:1914–1920`，方法为 `_init_character_resources`；`main_logic/core/__init__.py:265` 只是导出同一个 class。声明在 `core/manager.py:53,82`，独立 test harness 构造不是生产路径。

首次启动/统一刷新通过 `initialize_character_data`→2141，添加或更新单角色通过2198，均进入同一 `_init_character_resources`。新角色 slots 1792–1812，manager 发布到 slot 在1942；活跃/正在启动时保留旧实例（1855–1889），没有另一构造旁路。因此最小注入只需 manager 初始化默认 checker=None→受保护消息拒绝，加1914构造后/1942发布前的 app-owned adapter 绑定。role 重建不复制旧 authority/permit，仅语言、websocket和工具注册按原规则恢复；保留旧实例的热更新路径继续原绑定，但最终仍核 current role slot。

这个结论只覆盖所读实际部署源码的生产构造路径；未来新 factory、游戏/测试直接创建 manager 缺注入必须 fail closed，不通过继承旧 tool owner 自行授权。构造和协议本轮没有执行验证。

## 变更与最终 submit 的最小契约

可先实施的层：窄 current RPC + 实例 stamp + host-owned provenance + 既有 queue/filter/claim/drain 的 stale/unknown 拒绝。每次已接受材料变更的 seq 保持递增；来源与实例正确的控制仅对该角色相应确认失效，不广播，不删除 SQL/history，不改变题/尝试身份。summary context 只含 course/session，换图本身无需取消；换课/end session 必须使旧 subset stale。丢失控制通过下一次 current RPC恢复，不能把“没收到控制”解释为仍 current。

**不能把这层直接称最终提交保护。** `Core proactive.py:1851` 调 `session.prompt_ephemeral` 前还有 lock/其它 await；actual Offline `_lifecycle.py:574–583` 有独立 `reply_owner` 参数，但内部865–914继续等待和尝试。`on_committed` 在1129可见文本确认后才调用，不是 wire 提交前 callback。response generation 可围栏旧输出，不是材料 authority。provider 内部重试也需要逐次核准，外层一次 True 不覆盖它。

若开放正向首版，建议**一个有界、一次性的材料 admission permit**，只给明确角色 `session_summarized` 的纯文本、course/session subset；不新增消息队列/SQL。permit 是短期控制状态，最多一份正在提交的 permit/role，以现有 delivery id 和 host-only独立 narration owner去重。字段至少含 runtime instance、boot、seq、context、target、manager/session引用、delivery id、随机 permit id、期限与 consumed 状态；private字段不得进模型文本。

1. 当前检查通过后，producer 在 `_lock` 内条件性登记 permit，立刻释放 lock，回复 permit；未知/变更正在撤销/重复 delivery/容量满拒绝，不安排重试循环。
2. 相关 setter 在改变 course/session **之前**，短锁内标记 revoking、停止新 permit；锁外通知确切 host/target、等待原 permit 的提交/撤销结果。host 收到同实例 revoke，先使本地 permit不可消费，再取消它自己的独立 narration generation，回执不能借前次 tool output owner。
3. 真正发送接点必须新增独立 guard：经过全部会等待的 preparation 后，在实际 transport 写前检查并一次性 consume准确 permit；每个重试同样需要新核准，不能 replay旧 instruction。完成 request提交后通知 producer finish，释放 permit；已经提交的输出由 narration 自己的精确 generation绑定控制。`reply_owner`可沿用现有接口，但它需为这次 narration新建，不能等于上一次 `_study_material_output_owner`。
4. producer 只有在该提交已线性化在变更之前、或 host 确认已撤销未提交 permit 后，才提交相关新状态。等待不得占 state lock；材料验证失败/相同身份不进入 barrier，photo-only对subset不进入 barrier。超时不能把未确认当安全：若尚无强制不可再发送的期限/transport fence，保持该 narration route关闭，不能靠 TTL 自动释放后继续旧发送。若未来实现强期限，必须让 exact send task/transport在期限后不可提交并真实离线证明，不能仅删 producer permit map。

第3项的实际写前 hook 和第4项的有界 failure fence当前不存在；本报告不把 proposed permit 当已实现。只给最终check的 RPC、或 material setter 先接受再异步控制，都仍有 reader/write竞态。第一版可实际交付 authority adapter/拒绝路径；provider正向支持应等待这些精确接点，或明确降为“读取时current、发送窗口未保证”，不能宣称满足全过程材料正确。首版不接媒体、hold/takeover sink、Native/pending-prime冻结字符串，避免沿未保护路线旁路。

## 后续最小离线证明与证据层

使用真实 SDK entry/Ok序列化与 producer实际锁，不只 Fake current=True：同 host/process请求关联返回；registry await中替换/dead拒绝；旧 authenticated transport control不能改新实例；畸形/空session/readiness失败unknown；明确target无fallback；新manager不沿旧确认；photo-only summary有效而course/end stale；claim/drain后换课对应callback/mirror/ack/claim只释放原记录；丢控制下一current读拒绝。

开放提交前另证：permit consume前等待时change拒绝；真实send await/重试前revoke不能提交；缺finish/超时/cancel/capacity满有界且无旧 replay；确切 narration owner与用户新turn隔离；private provenance不进模型。这些检查尚未由本报告执行，不引用 producer queue14 或历史普通打断作为新协议通过。

本轮为 **SOURCE REVIEW / CONTRACT**，非SDK运行/模型/设备/真人 proof。仅本报告写入并冻结；其余源码、测试、manifest、部署、账本、接续记录全部只读。
