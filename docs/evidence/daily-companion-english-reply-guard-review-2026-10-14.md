# 英文局部回复修复：只读审查

严格静音继续有效：没有服务/SDK/供应商/Native/声音设备/回环启动，没有改生产、测试、manifest、ledger或派Agent。仅创建本报告。主要范围为 canonical tutor_llm_agent_concept_explain.py、entry_tutor_explain_entries.py 与 English/image-course定向测试；按Main追加的runtime/gateway优先审查，补读直接调用的runtime getter、既有gateway有限片段，没有全仓扫描。

## 旧发现与当前修复

初读实现有三项具体P2，Main收到后已修：

1. “未命中”只要求译文出现 miss/not/no，`weather cache hit, not a miss` 与 `weather cache hit, no retry` 可绕过。最新限制为不带反极性/复杂否定的 cache miss 名词短语，拒绝hit/not/no/never/without等，并为复杂中文否定诚实返回无法修复。
2. 被学习者以反引号引用的普通中文图标签因isidentifier被误作代码，两级语言guard都可跳过。最新Unicode inline只凭明确source fenced代码提取；图标签、text fence即使复制原source也不豁免；已识别代码类别中缺source的Unicode代码fence不进行翻译重命名。未列代码语言仍有下文JSON缺口。LF/CRLF同源源码比较不改变返回字节。
3. English路径重新resolve当前runtime并显式传入，覆盖已有ContextVar绑定。最新新增 `_current_model_runtime` 私有getter，保留任意既有bound snapshot；若group不匹配仍由原gateway拒绝，不静默切provider。公开resolve行为未变，primary及optional repair共用同一个snapshot。

复审中发现same-source text fence仍可豁免普通标签；Main再次修为“明确_CODE_FENCE类别且原source内容相同”同时成立。新同源text标签负例已加入；源码复核该点闭合。Main报告相关12项离线通过，所读断言包含反极性、inline label、same-source text、未知Python Unicode、CRLF源码、真实runtime getter与entry/SQLite；本Agent不重复运行整组或外部场。

## 调用与保存边界

helper仅替换定位出的Han span，原span之外的数字、ASCII标识符、Markdown与事实句不重新生成。输入最多12span/1200Han/8000总字符、8秒且至少剩2秒；只一次 `_call_model_result`，无helper重试。返回必须同数量的ASCII非空字符串，数字/backtick/换行、输出截断/invalid JSON/长度超限均拒绝。图片沿用primary相同image_url对象，以保持pinned vision group，不新抓图或换供应商。

既有SDK gateway在call前校验runtime.model_group与消息是否含图；SDK工厂明确max_retries=0，使用同runtime.model/base_url/provider_type/api_key。此结论是所读SDK路由源码，不能扩大成对所有独立供应商客户端重试政策的现场验证。

入口复制agent_context并传私有材料复核callback，不将callback塞入历史context。primary后、optional repair前、返回entry后、finalizer前及已有材料finalizer guard继续保护材料变化；CancelledError在helper和agent都传播。超过primary deadline由entry外层wait_for控制，修复失败是诚实degraded英文，不把错误中文解释伪装成功。solution结构repair仍是原独立路径；它之后新增final English guard，在history append前拒绝仍含非豁免Han的结果，不再循环语言修复。state lock不跨模型网络持有。布尔 reply_language_repair_attempted 只表示走过修复流程，不能单凭它证明供应商调用成功/语义正确。

## 当前具体发布阻断：JSON原代码被改写

最新读取 concept SHA256 `ec4946b61c16055a737fa7b1a95d916af58b1f64dcda16aa148ba43a4def450c`。

`_CODE_FENCE`已知代码类别未包括json；同源fence保护和未知Unicode代码拒绝都依赖该白名单。真实source与reply同时为 `json` fenced数据 `{"城市":"北京"}` 时，两个Han span进入翻译。原AST/helper配合纯本地async stub返回 `["city","Beijing"]`，结果为 `{"city":"Beijing"}`，code_changed=true。未调用SDK/模型，也未修改任何原文件。这是原代码/数据键和值被改写，不能由图场英文通过覆盖。

最小修法：明确json等常用code/data fence，在与原source相同的情况下完整保留；对非text/plain且未知语言的Unicode代码fence保守拒绝修复，不把未知代码当普通标签翻译。至少补同源JSON与未知lang拒绝的actual helper负例；不需要扩泛prompt、不需要再付费复验这个离线代码问题。源码修复前该点为P2阻断。

## 模型证据限场

Main报告recheck24已terminal/finalized：一个必要静音correction-only场、两句English，weather miss/not hit与wiki unknown准确，非错误附和；真实DB repair_attempted=true、最终reply等于DB输出、旧interaction/QA未改。DeepSeek+3至594/2000，app56不变、tech0，原账本不重置；自有host53964已结束/端口free。

这是Main新guard实际repair路径的限定模型/SDK/DB证据，本Agent未启动或重新运行。它不证明全部英文、多语言Unicode代码/数据处理、Native/设备/真人；此前recheck21/22/23失败与纯English FAIL应原样保留，新24不得追写旧失败为通过。等JSON阻断离线收口后可封版；后续更宽教学质量按原Goal推进，严格静音不变。

## 最终 code/data 增量复审（ba5cdd4）

本次重新读取 canonical concept 与实际定向测试，SHA256 为 `ba5cdd4d17ff0783b1794498d1d807978aa6e8b1f2751f42243200477b154269`。上述 ec4946 JSON 失败保留为旧实现证据，**不再是当前 JSON 阻断**：明确 code/data fence 白名单已增加 json/jsonc/yaml/yml/xml/html/svg/css/toml/ini/mermaid，必须同源原文才完整保留；未知非 prose 语言的 Unicode fence 在翻译调用前 fail closed。inline 同源 JSON、Call、Subscript 及 Dict/List/Tuple 由标准 AST 分类完整保留；assignment 等带已检查语法、但未确认为可保护 literal 的形式拒绝转换。text/plain/markdown 与普通图标签仍进入 prose 处理。Main报告 `daily-phase10-literal-data-fix12.log` 的12项实际 helper/agent/runtime/entry/SQLite离线通过；本Agent只核源码、断言与下列纯本地 AST 复现，没有重跑全组或外部场。

仍有一个具体 P2：`_literal_inline_code`（第76–83行）只识别 Call/Dict/List/Tuple/Subscript，`repair_english_prose`（第113–115行）的不确定代码拒绝正则仅含 `{ } [ ] ( ) = ;`。实际同源 inline `config.城市` 是合法 Attribute，既不受保护也不被拒绝；`城市 + 1` 是合法 BinOp，同样遗漏。提取当前真实 helper AST，以纯本地 async stub 返回 `["city"]`，分别得到 `config.city` 与 `city + 1`，两例各调用一次 stub，code_changed=true。这不是模型事故证明，但足以复现修复路径重命名原代码；测试现有 JSON/Call/Subscript 断言不能覆盖它。

最小修法是将已确认且同源的 Attribute 明确保留，或对其拒绝修复；对其他解析成功的非 Name 表达式（例如 BinOp），在未纳入支持范围时保守拒绝，不将 Unicode 标识符送入翻译。需保留纯中文/空格/slash 图标签的既有行为，不能仅扩大字符正则误伤它们。增加同源 Attribute 与 BinOp 不被修改且不调用 provider 的定向负例即可，无需付费重验。该点已通知Main；其闭合前仍为本审查范围的发布阻断。

recheck24 的实际模型指纹为上述 **ec4946**，它只证明修复后的图标签窄场；此次 ba5cdd4 code/data 增量仅有源码/离线证据，不能追认已模型、Native、设备或真人通过。严格静音、原历史和账本均未被本Agent改动。

## Attribute/BinOp P2 闭合复审（最终32889c6）

最终 canonical concept SHA256 已实际核对为 `32889c6bac3438d78bcd5ce50a677d850ed648ecbcae71dcb2a779817c1289c6`。本次只读取该文件与对应实际测试的受影响片段，未重复运行测试、SDK、服务、模型或设备。上节 ba5cdd4 的 Attribute/BinOp 反例保留为旧失败，**当前已闭合，审查范围内无剩余已知发布阻断**。

同源 `config.城市` 现在由标准 AST Attribute 明确保留；未证明的 Unicode inline token 一律在翻译调用前拒绝，不再靠枚举标点判断。于是 BinOp `城市 + 1`、单 Unicode name、未知 Call、assignment 和模糊 backtick 图标签不能重命名。已证明的源代码 Unicode identifier 在普通 prose 中也保留原 token。未闭合 fence/backtick 在有待转换 Han 时拒绝；primary 已截断且仍有待转换 Han 时直接返回诚实 `output_truncated`，不翻译半截代码。源码分支与测试中新添的 Attribute 原文相等、BinOp/单名/assignment 不调用 provider、破损边界拒绝断言一致。Main报告12项实际离线检查 PASS；本Agent本轮只读复核该收口，不将其记为独立重跑。

本次以保守拒绝换取源码完整性：反引号中无法证明是代码还是图标签的 Unicode 不自动翻译，普通引号的图标签仍可走原 repair 路径。该可用性边界应保留，不声称支持所有代码语言/表达式。recheck24 的 ec4946 模型/数据库窄场证据继续有效但不外推为最终32889c6 code/data拒绝增量的真实模型通过；该增量为 SOURCE/OFFLINE。报告冻结，源码、测试、manifest、账本与原历史均未由本Agent修改。
