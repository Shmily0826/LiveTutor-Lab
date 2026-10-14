# 阶段49：源码改动对照量具独立审查

只读冻结三文件及实际调用的旧cleanup函数；未读取Sky源码、运行CodeGraph、启动host/API/browser/model/device或修改账本。仅新增本报告，不改产品、测试、共享记录。旧code-short-followup4的值交换/缺键混同和简短限制PARTIAL承接，不能由prompt修改追改旧场。

## 指纹与独立离线证据

| 文件 | SHA256 |
|---|---|
| `scripts/neko_daily_code_dialogue_probe.py` | `ea592eeb9b3dbc440b0107d7dd4fae9e4090260dcd06ff4d5467acf41cc93ff5` |
| `scripts/neko_desktop_tutor_host.py` | `b479ff01156efc1a132f464a33730c4928980e01f3e08e0ef95887e68d96911c` |
| `scripts/test_neko_code_contrast_plan.py` | `c925c1db8ee12b9116cb62c75a86c0c4f1ab1a832ded180ec372456b037b7835` |

三SHA实核一致。独立运行既有Source venv `python -X utf8 -B scripts/test_neko_code_contrast_plan.py`，3项PASS、0.016s；使用RAW内临时文件与mock，没有服务/模型/用户DB。测试涵盖strict text-only/原round与2000上限/无voice allowance、已有/逃逸store与外部output拒绝、只复制原授权JSON且拒另一个授权root。不是角色实际查代码或语义验收。

## 合理的最小实现范围

角色指导增量只要求按实际consumer/guards区分statement order、lookup key和assigned value，不自行补未问的邻接case，含不确定性总数仍≤两句。没有Sky行号、项目专属正确答案或固定结论，和原“错值非缺键、先查consumer、throttled不阻源码查询”的指导兼容；新≤两句与旧要求两句可同时满足。是否实际守两句、是否把另一边错说反向，必须读未来实际回复，不能靠guidance文本判PASS。

contrast-only三问分别改变map书写位置、保留键但交换值、单键改名；量具未预取源码，后续仅从实际role WS/CodeGraph receipts观察。fresh课仅拷现存已批准Sky code_project.json，不拷学习DB、源码或索引。host使用SOURCE/deepseek/text-only、TASK_SILENT、原bargein-autocheck-20261012 round/2000上限、无voice host allowance。WS错误/异常会话/100s单轮超时停止且不创建replacement session；host hold380s。32请求在WS接收循环间检查，是停止边界，不能当严格并发硬顶或额外账本额度；原2000硬顶仍必要。最终semantics=PENDING正确，transport完成不等于教学验收。

## [P2] fresh store/output缺少排他预留

prepare_contrast_grant先检查store不存在，之后target.parent.mkdir使用parents=True/exist_ok=True。在检查后到mkdir前若同名store被另一调用创建，函数会沿用它，后续host可写其DB；这不满足本模式“必须全新自有store”的承诺。output也只先exists检查，后续save使用write_text，可能覆盖检查之后出现的未知原件。已有3测试只覆盖调用前已存在，未覆盖该间隙。

最小修法是批准grant校验完成后以store.mkdir(exist_ok=False)获得唯一场目录，再建其子目录；启动host前exclusive创建report输出保留位置，不覆盖未知winner。并发/异常只操作本次已创建对象，不清理别人的路径。定向用例应在原检查后模拟store/output winner，确认拒绝且原bytes/DB不变、不会Popen；不需新增服务或付费验证。此项已即时发Main，等待修复闭合。

## [P2] 复用旧host清理函数不保持新量具的ownership契约

本probe仍导入neko_daily_voice_probe.stop_owned_host。精确callee在其110行：process.poll非None就直接return，不处理已启动后仍存活的后代；后面通过psutil.Process(pid)当下枚举children和裸PID清理，最后还读/删共享neko-desktop-host.pid。probe本身没有记录launcher kernel创建时间或已证child身份。因此launcher先退出时可跳过backend清理，不能据owned_host_exit或无cleanup异常声称所有owned已停；也未具备此前relevant-history量具已审的PID复用保护/不咨询共享pidfile路径。

建议在本probe复用已有process_creation_time、owned_browser_pids、stop_owned_tree方案：Popen后立即记root创建时间，ready时在root身份匹配下记已证children；cleanup即使root退出也逐一检查已记录实例，不咨询或删除共享数字PID文件。无须修改全局voice_probe旧函数或扩大音频范围。至少需要root先退出仍清记录child、foreign/reused身份不清、单清理异常保留报告的离线负例。此项为当前新量具继承的SOURCE缺口，不是本Agent已观察到实际进程泄漏。

两P2均已通知Main；三测试PASS不覆盖它们。当前报告初稿冻结，59尚未运行，真实三种源码结果、CodeGraph工具自主取证、两句语言与事实/推断仍PENDING。Main修复后再按精确增量审查，不调用在线或设备，也不借旧SDK成绩/语音场冒本阶段证明。

## 两P2修复复审与新增顺序缺口

冻结probe SHA `4f1b34bb34576cb5d86104745ea698f3741f43f576085f15521805da862faa73`、test SHA `f6abc94759a2f1716a6755d4fed049d8c1c6dc54b1d2797cfe8e464063b7170d`实核吻合，host guidance仍b479ff…911c。独立运行同一离线suite，5项PASS、0.030s，没有host/网络/设备。

store在grant校验后mkdir(exist_ok=False)，新负例强制exists预检漏掉真实winner仍由mkdir拒绝，原marker逐byte保持。report在Popen前exclusive x保留，未知已存在文件不被首次创建覆盖，后续write_text仅更新已保留的本场原件。原fresh reservation P2在这些源码/离线范围关闭。

旧stop_owned_host import已移除。Popen后取得kernel root创建时间，0.25s tracker复用已审remember_children：先核root仍live且创建时间匹配，再保存child创建时间并去重。finally先cancel/gather tracker，记录异常，然后无论parent poll状态均stop_owned_tree已记录身份并wait；无共享pidfile读/删，tracker_error导致CLI非0。新负例只证明parent已退出时仍把child记录交scope gate，不冒真实结束进程。原cleanup P2在本次SOURCE/OFFLINE范围关闭；未被tracker发现的早逝root后代仍不能凭假想记录认领，实际退出需场59证据。

### [P2] 新exclusive输出发生在路径围栏之前

main新增options.output.open('x')位于prepare_contrast_grant之前，contrast output必须在RAW/evidence的检查仍在后者。因此调用者传一个外部output路径，会先创建该文件，再在prepare处拒绝；已有外部路径测试直接调用prepare，没有覆盖main的先写行为。这是此次调整引入的具体顺序问题，不需要实际API即可由调用顺序构造。

最小修复是在main任何output.open前，先独立验证contrast output.resolve().parent等于RAW/evidence，prepare中的重复核可保留。新增main层外部output负例应确认目标仍不存在、Popen未调用；socket/ledger等前置边界用离线mock即可。此项已即时报Main，59继续待修复闭合，未运行任何在线线路。

## 输出顺序P2最终关闭

最终probe SHA `7bf483802cc28d5ae7fbd2f9117ea3cc02f23933254e3c0e8fdeb0d3f1739df8`，test SHA `44b51f366d70d8fed45154834e914df35b80f1fde07e42e12a08a98745d9b637`，host仍b479ff…911c，均实核吻合。main第一步现已校验contrast output解析后parent，位于exists、socket/ledger及任何open前，prepare的重复检查保留。

新增负例直接asyncio.run实际main，外部output立即ValueError，原目标不存在且Popen未调用；因为检查先行，不需要任何网络/账本fixture。独立完整6项离线PASS，0.025s。该顺序P2在SOURCE/OFFLINE范围关闭，前两项保护修复保持；未扩审无关legacy行为。

当前未发现剩余具体P1/P2，可交Main唯一59实际对照场。报告冻结；没有host/API/浏览器/设备/预算或用户数据操作，尚无本阶段模型语义通过声明。

## 唯一真实59原件与语义独立复核

仅读`daily-companion-code-contrast59.json` SHA `b24ca1b2b8e768eb8f8fc5d7a7dc688f2703c515ed785f84e915c02fb8021419`及terminal另件SHA `2e6959db77cbe0e8357aa263ffbaef9242243e47b0687d6eb006ba2098fbe21d`，两值实核吻合且terminal的report_sha256绑定原件。未运行任何新测试、CodeGraph、Sky文件读取、API、应用或设备；以下只按本场reply与已保存actual receipts判断，不用旧场正确答案补齐本场。

### 实际源码证据范围

本场8个CodeGraph receipts均commit/repo_commit=7aae20f，首个index_sync=synced，其后throttled仍正常返回查询，不等于源码服务失效。角色自主从explore/query再node定位，未由量具预取源码。

真正shown包含客户端weather_service.dart:1–29（15–18构造lat/longitude各自的named query map，21 HTTP GET）、server/routes/weather.js:1–25（8/9按lat/lon解析，10–13不合法400，17正常res.json，18–20下游异常502）及coordinates.js:1–18（5非string/空串→NaN，7/8数值有限性，12–15有限和范围判断）。server/src/weather.js一次node receipt只有空代码header、shown=[]，不能借此认领下游实现已读或成功率已知。首个explore的主体其实是SkyMapPage，不能把探索header所述多文件数当这些weather文件已实际shown。

### 三轮语义

1. **仅调换map书写行序：本场FAIL。** 实际reply整个是DSML invoke/parameter/calls标记，要求study_code find routes/weather.js，没有中文教学答案。即使已读客户端或后续补查服务端，也没有本轮有效回答，因此不能继承旧场“行序不改变键值映射”填成本场通过。工具语法泄露是实际角色文本输出缺陷，不是教学结果。
2. **保留键但交换值：PARTIAL。** “不会缺值、也不一定400”及需按对应范围校验的方向正确，保持键值与缺键区分。但是“坐标一定传错”对一般问题过强（两值相等时交换没有变化）；把结果归结为“返回200还是400”遗漏本轮已shown的fetchWeather异常→502分支，也未取得可证明下游必成功的源码/运行证据。“原经度是否超过90”是对原合法经纬度交换后范围的条件推演，应明确前提与绝对值，不能冒全部输入或完整HTTP结果。
3. **仅lon改名：核心链有证，整体PARTIAL。** 在题设服务端仍按原键且没有其他lon参数时，req.query.lon缺失→typeof非string→NaN→areValidCoordinates=false→400，且提前return不调用route导入的fetchWeather，均由实际shown行支持。回复又加入“值写反通常仍200”既无频率/下游成功证据，也重犯上轮200/400过简二分，且是本轮没要求的邻接case；这段不应因缺键主链正确而一起判PASS。

后两轮各有两个句号终结句，未出quiz，但句子偏长且夹多处函数、文件路径/行号与紧贴代码标识符，不能据句数称自然简短表达全面通过。三种结果本场未全部交付；通用guidance已部署也不能保证模型始终遵守。

### 终态与证据层

原report无failure/cleanup_error/tracker_error，三WS turn完成；controller exec13483退出0，owned_host_exit=1是本任务forced-stop，不是自然退出0。terminal记录owned_alive=[]、48911/48916/9234无listener、post59_source_gate=PASS，audio/microphone/capture/loopback均false。原round不变，DS835→847恰12，app78不变、tech0；这些是Main保存的实际终态只读核对，没有本Agent新查询当前进程或账本写入。

原件semantics=PENDING保留不改；本独立语义审查判整体PARTIAL，与Main一致。已获得真实角色自主CodeGraph查询和部分改动影响分析证据，第一轮工具标记泄露及后两轮HTTP/确定性过度断言仍未解决。后续Main可针对工具语法过滤实际路径修复；本报告不预判根因或新增实现，不将完成transport、退出0或源码已读冒教学PASS，更无Native/物理音频/human证明。报告再次冻结。
