# Phrase runtime helper部署窄审

日期：2026-10-14。只读审查runtime_helpers.py、对应test、host新deploy/verify接线及host manifest两项deployed_path/源指纹；仅新增本报告。不运行测试、服务/API、宿主、音频、设备、DB或账本，不修改生产/manifest/四记录；用户已要求安全节点收尾后暂停，未安排新联网场。

## 改变优先级的具体证据

Main在voice34对应host日志确认每2秒出现 `No module named 'neko_phrase_input_transport'`；SourceApp cwd下两个helper的find_spec均false。已有脚本测试把scripts目录放入import path，掩盖了真实launcher.py cwd缺部署。该错误能解释实际DSP后native routing失败及无append的具体条件；不从一次日志外推所有历史失败唯一根因，也不将部署修复当provider/声音/自然停顿通过。counts诊断helper保持未接入，不先扩大hooks。

## 初版发现及最终P2关闭

初版deploy在最后exists检查后write_bytes，允许并发创建未知文件/链接再被覆盖，违背never overwrite unknown。已即时交Main。最终代码用Path.open('xb')独占创建；FileExistsError重新核non-symlink、regular is_file及exact bytes，未知拒绝，同字节并发winner接受，不使用覆盖写入。原先两目标预验证保持。

新增负例在xb前模拟未知并发创建，明确核未知bytes不变且第二文件未复制；正例模拟同字节winner并执行真实临时cwd子import。Main报告 **OFFLINE8通过**，本 Agent只读断言未运行。该竞态P2 **SOURCE REVIEW CLOSED**。限定已审源码未见新增具体阻断；不扩成对外部任意目录或恶意文件系统的普遍安全保证。

## 路径、来源及启动接线

helper_plan只接受两个literal deployed filename，且source必须严格为scripts/同filename；../、缺项、重复项或未知目标拒绝。每个源blob核SHA/UTF-8/AST后形成plan，所有源和现有目标在任何copy前检查，损坏/缺失source或未知target不能被重置。已存在symbolic-link目标拒绝。此接口依赖Main传入的可信project_root/两host_root常量，**不独立证明任意caller提供root或所有ancestor junction的containment**；支持限现有SourceApp/candidate树，不将manifest path allowlist误称OS沙箱。

只读源指纹匹配manifest：buffer `2bb1a65c72ac4bbf122ea9327de58df9d806572d6fa30f04c3eeca3132d9e99b`；transport `79cff29ca529ebc2e2e421288f48f0a384ed6d88399707d24711223ecfa324bb`。两deployed_path分别为根层同名.py。当前runtime_helpers.py SHA为 `d311098c90fbcc8906e1b1be34782e9f8eae05f36d0e668732b2de0a366cfbe8`，Main尚待把其新SHA更新至manifest后再offline部署/SourceGate；本 Agent不代改。

host apply_voice_host_patch在每树可靠性patch前deploy两helper；verify_source_audio_gate仍核runtime helper源，再verify_runtime_helpers(ROOT,SOURCE_APP,manifest,SOURCE_PYTHON)，全部在prepare store与Popen实际launcher.py之前。实际source command使用SourceApp .venv Python，cwd=SOURCE_APP，与子preflight一致。部署两树不等于两树都执行过完整app。

verify先核deployed bytes/symlink/file，再用同Python、`-E -B -c`、cwd=host_root import两模块，核__file__ resolve是host root同名文件且NativePhraseUplink所属模块正确；没有scripts注入或app/ConfigManager/Core/provider导入。两个helper本身只有stdlib依赖，import不实例化DSP/Native或启动设备。失败退出阻止host启动，不自动重连或改supplier。

## Proof范围与冻结

Main8项含真实临时cwd import：部署前可复现missing module，部署后成功、无pycache；缺失/篡改target、未知target、source hash错误、manifest escape/重复/缺项、幂等与helper import抛错拒绝，并含两个race用例。只读初查实际两树根层helper仍missing（Main尚未apply），因此本报告仅 **SOURCE REVIEW及Main提供OFFLINE8**，不能说实际SourceApp已部署或真实provider缺口已消失。最终offline apply/SourceGate结果由Main记录。

部署只是使默认OFF代码在实际cwd可解析，不修改phrase开关、普通capture/onset、owner/registry或provider准入；默认OFF/ordinary行为边界继承原已审补丁，不能从子import证明完整运行行为。用户集中体验前，不新开联网语音、不重复WAV/付费重连。唯一写入本报告，最终冻结。

## 2026-10-15恢复后containment及9项独立复核

承接四记录后按Main最新授权恢复本窄审；仍禁止mic/capture/loopback，必要speaker约4%不调。本轮独立执行的唯一测试为 `python -B scripts/test_neko_runtime_helpers.py`：**OFFLINE9 PASS，0.600秒**。仅stdlib、临时目录和只导入两stdlib helper的子Python，未加载应用/Core/模型/设备，未触及用户DB/账本或启动服务/API。

最终代码在deploy与verify入口均先核host_root非symlink且resolve后位于project_root.resolve内部；helper_plan同时核源文件非symlink、resolve containment。因此literal path allowlist之外，当前root/source通过已解析路径做越界拒绝。第9项同时覆盖部署及验证传入project外host时拒绝，核host目录无复制；其它8项包含真实临时cwd import、未知file/race不覆盖、同字节winner、缺失/篡改/坏hash、重复/escape/缺项、幂等与import错误拒绝。不是任意恶意文件系统修改期间的全OS沙箱，支持仍限定明确host roots。

宿主接线只读再次核：每树deploy在可靠性patch前，SourceGate source/deployed/实际cwd child import在prepare_store/Popen launcher.py之前；SOURCE_APP/SOURCE_PYTHON都是明确绝对路径，同启动cwd，-E不靠scripts/PYTHONPATH注入，-B不产生pycache。默认OFF功能未被import preflight启用，ordinary capture/owner/registry业务未改。限定实现 **SOURCE REVIEW无新具体P1/P2**，初版竞态关闭保持。

当前只读源与manifest runtime_helpers.py SHA均为 `c4e411e48b231e607631dca16620d8ce2d597c3de6b7fe14dc6e38b993c14fd6`。两phrase源SHA保持前段值；benchmarks/raw/neko-product-host与candidates/N.E.K.O根层两个deployed helper现均存在且逐byte SHA与canonical/manifest一致。这关闭本报告先前“仍missing/待部署”的当前文件证据范围；Main此前实际SourceGate/launcher-cwd import结果仍归Main，本 Agent本轮只跑temp9，没有启动真实SourceApp。

用户恢复Goal后不得沿用旧暂停/旧额度为当前事实，本 Agent不更新共享记录/账本，也不根据文件部署认领voice34修后ASR/provider、声音、自然停顿或新真人通过。唯一写入仍本报告，最终冻结。

## 发布前第一负例修正的精确复核

仅只读新增test第一负例及既有production verify片段。Main/candidate使用当前Source venv时，其搜索路径还可找到已部署的host父目录helper；所以临时cwd未部署并不保证bare import必然ModuleNotFoundError。旧负例的“任何地方都不能import”断言会因此失败，属于环境相关测试条件，不是production门禁遗漏。历史9项在此前解释器的通过保留，不外推所有venv。

新负例在真实子Python import后核module.__file__.resolve恰等于当前临时cwd的同名leaf，未部署时无论完全不可import还是借到其它host文件均失败；部署后仍通过production verify对两module来源逐项核验。该test增量与production既有exact-origin要求一致，**SOURCE REVIEW无新增具体P1/P2**。Main报告修正后Root9、两实际host cwd与SourceGate通过，本 Agent本轮未重跑或加载应用。

production部署/verify逻辑未改变，LF规范化不改变业务。本轮只读runtime_helpers.py与manifest source SHA仍相同：c4e411e48b231e607631dca16620d8ce2d597c3de6b7fe14dc6e38b993c14fd6；完整helper源指纹更新与实际Gate复核由Main承担，不据bare import认领正确部署，更不认领provider或设备成功。唯一追加本报告，最终冻结。
