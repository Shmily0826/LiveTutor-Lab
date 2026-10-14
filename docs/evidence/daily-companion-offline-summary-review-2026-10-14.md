# 阶段十三 offline relay / summary量具窄审

日期：2026-10-14。唯一写入为本报告。只读host新offline Sink/CLI、task-only summary prompt audit、fixed control与summary anchor两量具、`test_neko_offline_egress.py`两项及`test_neko_summary_audit.py`一项新增测试。没有修改源码/manifest/账本，没有运行测试、服务、API、Native或声音设备，没有派Agent。不扩大完整SDK或仓库审查。

Main报告root实际C31通过：原30prefix、2QA、题/eval/prefs/material不变，8明确offline neutral prior rows+1summary；实发prompt有2anchors（0,10）、prior8neutral/currentempty、seed{}；模型正确聚焦英文wrong0和既有nextstep，DS594→595、app58不变、无音频。本 Agent未读取其学习history或独立执行该场；其MODEL/DB证据归Main，不能扩成Native/device/human，也不影响整体Goal仍在执行。

## P2：offline构造仍可能重置不匹配或损坏账本

`neko_desktop_tutor_host.py:615–618` 不区分offline模式：先_load_ledger；无法resume就_persist。`690–698` 对缺失/损坏或round不匹配不resume；于是offline=True构造会把旧spent替换为空并改round。`983` CLI缺省round仍是当天round，因此新的 `--offline-egress` 单独使用时可以触发，即使所有后续网络都被拒绝。

当前fixed-control量具先检查实际原round，C31同round，因此这个发现**不否定已执行的28/29/C31**。它是新offline入口的账本保证缺口：拒绝请求不能补救constructor已清旧计数。

最小修法：offline且使用cap_file时要求现有合法、同round ledger，失败在任何persist前抛错并保留bytes；offline不创建新预算或更换round。补不同round/损坏/缺失的定向负例。同round保留原spent/budgets，普通非offline行为不扩改。该P2已消息交Main；本报告首版待其修复确认，不要求以未完成的全Goal阻止本阶段源码发布。

## 已确认的offline边界

`_handle:744–749` offline分支位于CONNECT/HTTP处理、_spend与upstream调用之前；记录offline_denied并403返回，不走_tunnel/_forward，不消耗既有provider计数。CLI将offline参数显式传Sink。它是**该HTTP relay的拒绝保证**，不等于OS防火墙；NO_PROXY本地线路或未使用该代理的客户端不由此拦截，不能凭此称所有进程绝对离线。

新增egress测试使用临时ledger与socketpair，检查CONNECT DeepSeek/Lanlan及absolute HTTP返回403，_spend/_tunnel/_forward未调用、原bytes保持；普通relay单请求仍记一次。只覆盖合法同round构造，原缺失/坏round情况未覆盖。测试不会写共享ledger；本轮未重跑。

## Task-only gateway与数据保存

`prepare_summary_prompt_audit:288–306` 要求task acceptance store名前缀，目标为该store的plugin-code，不改canonical。目标bytes必须与canonical gateway完全相同，否则抛错且不写；唯一audit("started")锚点必须存在一次，patch后AST确认才写。仅summarize_session附实际messages，不加入headers/runtime/credentials，不把prompt写入教学history。

新增summary-audit测试确认可逆单锚点、canonical bytes保持、edited unknown gateway保存且拒绝、非task store拒绝。该保证是这个helper自身的入口；host通常先prepare_product_plugin刷新受控任务代码，再调用audit，不宜表述为所有启动都保存任何自定义plugin-code。正常host CLI先把store resolve并限制在benchmarks/raw；独立helper仅核名字，本次受控量具使用固定已批准task store，不把名字前缀视作一般用户数据授权。

summary anchor量具使用固定任务DB、不复制原用户学习库。先和原quality19保存的prefix/QA/course比对，准备前检查端口无占用；使用实际Store ordinary append，先核history retention可保留原prefix，再追加明确标记test_fixture/source_scope=offline_fixture/learner_progress=false的neutral教师窗口。没有伪造学习者作答/掌握度。prepared与after都核原prefix/QA和题/eval/preference/material/course相关state保持；scope只在旧窗口存在时追加，currentempty不补伪新学习行为。

失败或timeout不删fixture行、不清历史、不reset DB；fixture_batch/index与summary原始结果留在私有raw报告。一次summary append检查不等于所有SQL记录全比对：脚本protected(state)按明确字段名筛选，Main所报C31具体不变项应依其实际证据，不能扩成完整用户DB每字节不变。

## 当前run的超时与音频边界

fixed_control_probe：output存在即拒绝覆写，端口占用就拒绝，不清别人的host；先核ledger round和现有隔离fixture。用offline relay/api-budget0，capture-blocked Native仅作控制diagnostic，报告明确session_start_sent=false/pcm_sent=false。attach的有限轮询只针对当前自建debug port/renderer，未另开Native或provider重试；notready/Timeout在finally释放固定来源、关闭observer、自建Native及host并保存finalized。28/29的失败归原场，不改成ready PASS。

该控制量具**会启动Native**，由独立speaker/output-only/capture guard限制；它并非一般无Native的纯summary量具。不发送start_session/PCM并不等于永远不可能收到环境音频，offline代理和实际renderer capture保护仍是必要条件。不能因summary C31无音频就外推控制28/29为设备无捕获证明。

summary_anchor_probe：host参数为source且无--voice/--output-only，env NEKO_TASK_SILENT=1，audio/native=false；走已有text-only gate，不launch avatar/meter/capture，固定材料/prefs/历史保持。ledger round显式使用bargein-autocheck-20261012、egress-budget2000/app unlimited/tech0，不重置计数。不是offline模型场：它有意发一次真实summary请求，spent变化应归实际请求，不借private audit复跑模型。

输出已存在即拒绝再运行，先落before/report再启动；LabClient只调用一次summary，没有blind retry。捕获到built-in TimeoutError时保留该owned run供Main后续定向poll，而不是换新output重发；其他失败正常定向停止并保存。保存pending_owned_host只是线索，后续必须沿原Popen/命令身份确认，不凭PID数字清复用进程。该文件没有通用resume CLI，本轮不扩为所有SDK timeout类别都已验证；C31 Main已terminal/finalized与旧timeout分别保存即可。

## 结论与证据层

有限范围当前只有上述offline constructor P2待修，gateway helper、owned数据保存、一次请求/timeout不blind retry和summary静音边界未见其他具体可复现阻断。三个新增测试为Main离线证据；C31实际prompt/model/DB为Main已报告的限定通过，不因其他B/E/设备/human未完成而否定此阶段交付。修复P2后只精确追加关闭确认，不扩大扫描/重跑旧批次。

本轮为 **SOURCE REVIEW**，没有新的运行证据、额度或进程操作。报告冻结。

## 唯一P2关闭确认（最新精确复核）

Main已修复。本 Agent只读host constructor `615–621`，确认cap_file未成功resume且offline=True时立即raise，位于_persist和socket创建之前；因此缺失、损坏或不同round不会被新offline入口创建/重置。普通非offline分支保留既有行为，合法same-round仍沿用原计数。

新增 `test_offline_never_creates_or_resets_missing_corrupt_or_other_round_ledger` 精确覆盖三种情况，每次要求RuntimeError，并核缺失仍缺失或原bytes逐字不变；两个原relay测试保持。Main报告Root三项PASS，本 Agent未执行测试，归Main离线证据。

该项 **SOURCE REVIEW CLOSED**，历史发现原样保留。当前限定阶段十三范围无剩余已知具体阻断；不因全Goal或设备/human尚未完成而否定C31限定通过。此次仅追加本段，没有源码/manifest/账本改动，没有服务/API/Native/设备操作，报告再次冻结。
