# 阶段24：Native 显式答题的正式评分路由（开发中，2026-10-15）

状态：SOURCE/OFFLINE PARTIAL；已受旧指纹保护部署到两宿主，默认关闭；源码已发布 d520252c001f8d95a1f682f9fd15b27084a9d05b；尚未验证真实 Native 服务及设备播放。

## 本轮完成

- 新增默认关闭的 NEKO_STUDY_AUTO_GRADE 路由。首次带 speech_active=True 的实际输入帧只读现有 SQLite 四身份；ASR 使用实际连接/scope owner，禁止晚到后改认最新题。
- 实际 Core transcript admission/route/echo 之后后台调用原 study_session/study_answer，经现有 SDK 和 SQLite 保存；ASR 接收不等待模型。
- 原始答案原样传入，正式结果必须返回对应 question/attempt；更正保留旧错答并生成新 attempt。
- 自由输出 hold；正式结果通过一次无 PCM replay 的受控连接和真实 response arbiter 的普通 message/response.create 发送，不伪造 provider function_call_output。新语音、scope、activation、socket 变化拒绝迟到发送。
- 原生模型同时调用 study_answer 时合并同一任务；受控结果连接不能再次评分或擅自出题。
- 重连只有一次；失败保留已提交成绩并显示失败。不得据此宣称用户听见、provider ACK 或完整设备链通过。

## 本地证据

scripts/test_neko_native_grade_route.py 当前17项通过：实际 Core 方法、实际 transcript policy、SDK 参数/回调/序列化、评分/Store SQLite、实际 response arbiter；模型、连接、wire、设备、活动/UI/总线/telemetry sink 为隔离替身。没有启动 host/网络/捕获/播放。覆盖零 provider 工具调用、非阻塞 accepted transcript、route/echo 拒绝、换题拒绝、首次 pin/歧义拒绝、新语音迟到抑制、单次重连失败、同时 provider grade 合并、逐发送前新输入、受控 relay 去重、显式纠正。

辅助意图/只读 pin 测试由既有 Agent 完成：13 PASS/1 Windows symlink privilege SKIP；运行时 helper 9 PASS。原真实模型阶段23、真人反馈及失败均保留，当前不增加真实模型通过声明。

## 尚待与边界

- 独立审查进行中。learning_memory 审查因模型 capacity 失败；不擅换模型，交由另一个现有 Agent 只读审查，无新 Agent。
- legacy speech_active=None、旧 PCM replay 及重叠/不可确认输入目前 fail closed，不能取得新题 pin；这不是全音频模式支持。poison 要实际连接替换才清除。
- 需要完成 helper/host/product 清单指纹、完整 patch replay 与幂等、审查修复，再部署。当前运行时未应用该新路由，manifest 尚待封版；不要在此状态启动测试宿主。
- 需要真实 Native 单场固定 WAV（无捕获）验证 accepted ASR→正式 QA→受保护结果音频；此前人工口头评分绕工具缺陷仍按未交付记录。

## 约束与当前运行状态

Goal active，完整 contract 原文不改。账本实际读数 DeepSeek677/2000、Lanlan.app63/null、Lanlan.tech0/0，round bargein-autocheck-20261012，不重置；本轮0外部请求。没有本轮创建的服务或音频进程，全部离线测试已退出。扬声器仅用户4%必要输出，不改音量；不启用麦克风/捕获/回环，不要求本人重复测试。局部失败继续其他工作，依据实际证据完成。

## 当前草稿指纹

- scripts/neko_native_grade_patch.py SHA256 eadd23718ac76203c6df72fd89f349d94de87f277dc6b8c4d3302728e50db1bf
- scripts/test_neko_native_grade_route.py SHA256 78e266432ee11d053baa4ff95a4c6d7cdbea98071be82987edceb41bf373cf7f
- scripts/neko_study_answer_intent.py SHA256 515fab3f66ba7c33fc72871ff399644d820c92eccba776dc35d1582ae537083c
- scripts/neko_runtime_helpers.py SHA256 d1d26c8eb1c28338cd5a903ddf1539dfa1a23922d43eaeccac6b1a5ab77189c0

## 封版与部署（本轮后续）

初稿首次输入未固定Core activation/socket/scope的P2经独立审查确认，现首帧保存原authority/ws/token/scope，只有真实协议用户边界允许一次scope前移；ASR前换activation/socket/foreign scope均拒绝，不把旧语音改绑新owner。17项Main及独立PASS；最后feature OFF回调绑定条件的一行独立精确复核，未重复整套。LANLAN_APP实际协议profile本地覆盖item驱动，仅普通conversation.item.create，并非必须发送response.create；ticket.sent仍不是provider ACK。

完整回放初次在候选turn缺历史text-only三行处失败，改为共同handle_audio_data稳定锚保留各版本既有gate；最后两个副本共30文件首次/重复幂等及AST通过。实际两host受旧字节/原host manifest指纹保护应用，三helper实际cwd child import通过，host SourceGate通过。产品avatar工具返回正式qid/attempt，以LF新hash封清单，原daily只替换这个已核旧SHA的代码文件，未操作学习DB/config。新路由默认OFF，未启任何host/在线会话。部署后普通native handoff12、phrase transport20通过，保护原打断/停顿路径，仅本地socket fixture。

实际账本仍677/63/0，无新增服务/设备进程。下一步发布受审defaultOFF源码，再用有界固定WAV验证真实ASR自动正式成绩及受保护转述；没有真实服务或播放通过声明。legacy None/replay/歧义输入限制仍开，完整A–F继续。

最终源码指纹（优先于上文草稿）：
- scripts/neko_native_grade_patch.py SHA256 88486379352e021604e93aa250fb59364363b90172fa6cc01c243e24f8f0565b
- scripts/test_neko_native_grade_route.py SHA256 60f01ffffcc29821f57c4c7d86b5c35f6696e09dd62a471ef3e91908fd8e3938
- scripts/neko_runtime_helpers.py SHA256 d1d26c8eb1c28338cd5a903ddf1539dfa1a23922d43eaeccac6b1a5ab77189c0
- patches/neko-study-2026-10-10-host/manifest.json SHA256 2609b384b412de672a011b61857663b913df21cdc6f26d46141d4978963cae69
- patches/neko-study-2026-10-10-product/payload/study_companion/study_avatar_tools.py SHA256 afb52dbbc047fd3cf20eab2c536fcdde9d1cba36fe4056a489bda27fe6123af9

发布记录：d520252c001f8d95a1f682f9fd15b27084a9d05b（codex功能分支，未merge/force），17 exact allowlist文件；远端同SHA及master未变已核。
阶段24源码已review/commit/push d520252c001f8d95a1f682f9fd15b27084a9d05b，远端codex/daily-learning-companion同SHA且candidate clean，remote master仍f1e8f3f5605659f0526e43bc3b85c60ae46c85fb。17 exact文件，staged LF产品29file及helper全部fingerprint核通过；Root index未stage，原脏树/.workbuddy保留。真实Native自动评分与设备仍待。下一轮先四文件，再准备自动评分专用observer：沿用既有任务材料/固定WAV，无mic/capture/loopback；先核真实任务库pending四身份（不得伪造、重置原历史），必要只创建本场新题，核ASR→QA及迟到音频owner/诚实失败。现有voice_probe默认只验study_explain，不能直接把其结果当grade PASS，先补针对性量具。未开online前先核账本和8API保护，保留单场超时/异常停止，不循环CONNECT。若局部protocol受阻，记录并转其余A–F，不停止全Goal。当前无新增host/音频会话，离线进程已terminal，Goal active。
