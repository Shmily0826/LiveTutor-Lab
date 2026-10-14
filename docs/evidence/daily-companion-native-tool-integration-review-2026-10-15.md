# 阶段43：Native 工具续接 canonical 集成独立审查

日期：2026-10-15。本文件由独立审查 Agent 写入，Main 独占实现、共享记录、manifest、部署与在线安排。本轮不启动宿主、服务、provider、Native、浏览器或设备，不读用户DB，不改额度。当前初稿先记录只读接线意见；Main 冻结前不运行测试。

## 已承接范围

阶段42最终冻结原型 patch SHA `ceb906653b2fdcd143c3467915d4cd98536512876f163272eab662460167474a`、test SHA `23070f99c386e6f23bd34891f6dedaaaa7fda59f8cf2f9fdb88b464e6fbc32c4`，独立26 SOURCE/OFFLINE通过；原wire-ID及新PCM取消等待两个P2已按该范围关闭。

取消缺合法terminal时是约3秒grace后的安全失败关闭，不是不断连恢复。两30秒deadline未合并，单outstanding本地origin不是provider严格因果，多ASR/第二round仍未支持。原49/50 PARTIAL不因canonical集成改判。

## 冻结前定向意见

1. **只升级一次。** 当前42/40 staging显式 `upgrade_targets(canonical.TARGETS, canonical._OWNER_TRACE_REPLAY)` 是原型组合手法。canonical接入后，测试必须直接消费最终TARGETS/REPLAY，不能再upgrade一次或导入旧原型组合，否则会重复hunk、掩盖实际运行版本差异。临时实际host副本的canonical apply/AST/state/二次幂等检查保留。
2. **normalizer最终绑定一致。** `_tools.py` 的state和apply都调用canonical模块级 `normalize_ordering_helpers`。join的exact HELPERS+已审增量wrapper应与最终targets同一次接线；不能仍用先前导入的旧normalizer将新版helper恢复成旧块。未知helper编辑仍必须拒绝。不得放宽成仅靠marker截取替换。
3. **运行producer与测试producer同bytes。** 复制已审phase40隔离producer回运行 `scripts/neko_phrase_input_transport.py` 时，须明确源/目标完整bytes或SHA一致。集成后的实际测试应导入运行producer；不宜仅继续加载draft而声称已测canonical运行路径。
4. **helper源与deployed分别核。** 现有 `neko_runtime_helpers.helper_plan` 只允许三个明确stdlib叶子部署，排除unknown、逃逸路径和未知已存在文件；host实际cwd child import核 `module.__file__` 精确位置。这些保护保留。join/audio patcher等仅源码import依赖也要进入host manifest runtime_helpers的source hash检查；不需伪装成deployed helper。host `verify_source_audio_gate` 会核全部runtime_helpers源hash，并核部署的三个叶子及实际cwd import。
5. **默认OFF的证据分开。** 日常启动不应新增phrase/AUTO默认启用；actual automatic_audio默认False，新增join仅由明确原Native automatic slot接纳。普通无origin工具仍走旧lane，但已有phrase driver且无合格Native slot的迟工具明确拒绝，不能把该收紧说成所有文字/UI入口已验。需要相关ordinary回归，不能只用26项原型证明。
6. **历史known-blocker保持历史。** 阶段40actual tool_result死锁曾确认且原报告保留。接入join后若旧测试还断言工具互等，它应标记为旧草稿历史测试/由新真实路径替代，不得将该旧断言失败当新bug，也不能将旧“阻断仍在”的断言PASS冒作集成成功。

冻结后仅补实际文件/hash、Main预验证/部署层级、必要独立离线回归及具体发现。本初稿未运行测试、未验证新canonical/manifest或两树部署，不是接入批准。

## 冻结源码与计划manifest复审

下列指纹均独立读取一致：

| 文件 | SHA256 |
|---|---|
| `scripts/neko_voice_host_patch.py` | `5e86fd7db925d268b80a9b6957efb514f1bc49920dd0e4a6681a7adaf790dfb2` |
| `scripts/neko_native_tool_join_patch.py` | `7b9098373bdfda8b14b55bc4d48de79ba776d290a1305d9df4dd1b94ed2e6907` |
| `scripts/neko_phrase_input_transport.py` | `d247be713381aae91a71608441f9a06d3be0b5ccb868a8b667c9d70f44ce548b` |
| `scripts/test_neko_native_tool_join.py` | `bd826fa35011d82e150cd415fddc2c1305a100904f56d10015a2d2d58935f857` |
| `scripts/test_neko_native_audio_dispatch.py` | `062ade9425230b49709fc1c46d23950da4190043e82fd10f87139c0f2218da42` |
| 私有计划 `benchmarks/raw/evidence/phase43-staged-manifest.json` | `4226ab40401a419bd1618b6e54dac13dde64c731b4bed40072d2182c03713210` |

独立运行 `python -X utf8 -B scripts/test_neko_native_tool_join.py`：**26 tests PASS，27.753s**。这是最终canonical接线后、运行producer路径下的完整26项。临时实际host三文件都经过apply、AST、state与二次幂等；未写实际host。

随后只读核验/临时staging结果确认：

- canonical尾部在全部既有grade upgrades之后调用join upgrade一次，`_NATIVE_TOOL_JOIN_PATCHED=True`；最终模块级normalizer精确绑定join wrapper。42和40测试的sentinel避免再upgrade，未知HELPERS变更拒绝负例仍在26套件内通过。
- audio fixture的 `producer_path` 为实际 `scripts/neko_phrase_input_transport.py`；其完整bytes与已审phase40 draft相等，不是只验证文件名。没有用draft替身冒认运行producer。
- 三个临时canonical输出的SHA逐一等于计划manifest `_transport.py` / `_tools.py` / `_response_arbiter.py` 的patched SHA。
- 计划12个runtime_helpers源hash全部与当前文件一致，包括新voice/audio/join source-only依赖；三个明确deployed叶子保持原helper allowlist，不把patcher当宿主运行helper复制。
- 计划与现有manifest的host差异仅三项。transport与tools的phase43 prior分别等于实际source旧bytes及旧manifest；arbiter原manifest没有条目，新增base=null并保存实读旧SHA `f041135b335a22655bffe14a0856d11f105aa50b56355a0921ec853e7be9aaff`，没有虚构upstream base。实际source当时仍旧bytes，不能据计划写成已部署。
- 本轮没有修改日常启动flag；automatic_audio仍默认False，运行producer仍仅由既有phrase/AUTO显式opt-in创建。普通无driver工具lane的实际负例/正例在26中通过；动态切换、Avatar typed/UI与全部ordinary行为不能由此全称已验。
- 40 known-blocker断言在canonical已接join时明确skip并指向actual tool-join suite；它是被新真实路径替代的历史死锁证据，既不抹去原P2，也不算额外成功场景。

Main报告的完整临时project SourceGate及actual-cwd child import正/篡改拒绝/恢复正预检，本Agent只核其代码与计划、未独立执行该Gate。此前其余52项相关回归也不记为本Agent执行。部署前应保留exact oldSHA与backup门禁，未知差异拒绝，已授权Main自行负责。

## 新deployed-runtime量具只读检查

`scripts/test_neko_native_tool_runtime.py` SHA `895f1aa84713a778e06c8add6ddf4ccf53e0773db795f10213edcbdfa313560a`：HOST优先插入sys.path后，先导入实际producer/arbiter/tools/transport，再加载既有Core/QueueSocket fixture。没有staging或替换上述host方法；检查模块位于HOST、arbiter与producer的实际type、raw-tool方法的sourcefile。两个场景分别验证同ticket工具输出→真实ID-bearing内容/terminal，以及missing-wire-ID执行前拒绝。

复用fixture有隔离env、local callback/socket/Core manager seams；这仍是实际部署模块的离线行为检查，不是启动真实应用、provider ACK、音频设备或human。新增脚本本轮只读未运行，必须等部署后由Main记结果，不能预先计入通过。

最终窄结论：上述冻结源码/计划及独立26套件未发现新的具体P1/P2；最初六项接线疑点已在SOURCE/OFFLINE范围收口。它不代替两树实际部署/Gate，不预判必要在线场，不将缺terminal时安全关闭称为不断连恢复。原49/50 PARTIAL、两30秒时钟与provider严格因果/多ASR范围均保持。

## Main精确部署后：独立只读8文件与实际SourceGate复核

Main报告已按8个exact oldSHA与独占备份完成部署；本Agent随后独立只读核对实际两个目录：`benchmarks/raw/neko-product-host` 与 `candidates/N.E.K.O`。

| 每树相同文件 | 两树实读SHA256 | 独立检查 |
|---|---|---|
| `main_logic/omni_realtime_client/_response_arbiter.py` | `0dc4d0349d518d4bac4a8a1da034e46bde4624e9fa9aa4079af8539ca32e922e` | 两树均match manifest、canonical state=patched |
| `main_logic/omni_realtime_client/_transport.py` | `3f15318310c75880a27f4fc1ef2ec961b5472204f36056068df30ea8043bdae8` | 两树均match manifest、canonical state=patched |
| `main_logic/omni_realtime_client/_tools.py` | `81a2bb42ac2ac8d264189cb648e655b9dec4097686be1366a013e2b88345489f` | 两树均match manifest、canonical state=patched |
| 根目录 `neko_phrase_input_transport.py` | `d247be713381aae91a71608441f9a06d3be0b5ccb868a8b667c9d70f44ce548b` | 两树完整bytes均等运行scripts源 |

实际 `patches/neko-study-2026-10-10-host/manifest.json` SHA为 `4226ab40401a419bd1618b6e54dac13dde64c731b4bed40072d2182c03713210`，独立完整bytes比较与上述staged计划一致。

独立实际调用 `neko_desktop_tutor_host.verify_source_audio_gate()` **PASS**：检查当前source全部manifest文件、helper源指纹、三个deployed叶子和实际Source Python / launcher cwd child import位置。本调用只读校验并启动无应用导入的stdlib child；不启动host/server/provider，不接触设备或用户DB。没有再次apply任何实际文件，也没有重复26测试。

下列执行归属明确记为Main：8文件备份/写入、实际target二次apply=already patched、实际无staging runtime2 PASS(0.634s)、ordinary12 PASS(4.491s)、helper9 PASS(0.978s)。Main音频自动路由离线40+1 historical skip在本次通知时尚运行，未在本段认领其终态；名称中的audio不等于设备测试。

本次窄结论：实际部署字节与canonical/manifest/Gate一致，未发现新的具体P1/P2。默认日常phrase/AUTO OFF不变；所有结果仍为SOURCE/OFFLINE/实际部署模块校验，不是provider ACK、Native设备播放、physical或human通过。本报告冻结，不预批下一付费场或改变原49/50证据。
