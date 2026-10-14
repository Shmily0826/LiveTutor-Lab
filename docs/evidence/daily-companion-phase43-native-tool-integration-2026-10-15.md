# 阶段43：Native 工具续接的受控集成

2026-10-15。完整 contract/A–F 保留，Goal active。上一42有真实开发、独立审查、78离线及功能分支发布，属于progress。本轮完整重读四记录后继续。

## 已完成 SOURCE / OFFLINE

canonical `neko_voice_host_patch.py` 在全部原grade/text trace升级后单次组合42join，并同步最终exact ordering normalizer。两个staging测试依明确sentinel消费最终targets，避免重复升级。运行producer精确等于已审40draft d247be713381aae91a71608441f9a06d3be0b5ccb868a8b667c9d70f44ce548b，audio测试已改为读取实际运行源。join实现只有首docstring由隔离改为opt-in描述，其余42implementation未改。日常phrase/AUTO仍OFF。

原40 known-blocker测试是旧草稿死锁重现，当前标为historical skip，由实际26工具续接及2项无staging运行导入测试覆盖，未当通过计数。旧失败/49/50 PARTIAL保持。grade route测试AST手工namespace因新owner的field出现NameError，在产品执行前失败；只补已有dataclasses.field到namespace后38项通过，没有放宽产品owner。

| 验证 | 实际结果 |
|---|---|
| Main接线26 | PASS27.963s（后续testaudio切至同bytes实际producer） |
| 独立最终接线26 | PASS27.753s，核最终运行producer路径/bytes |
| 部署后无staging实际host导入2 | PASS0.634s，实际module.__file__/class identity/方法sourcefile，真实工具同ticket闭环及缺wire-ID拒绝 |
| 实际自动20+phrase20 | PASS40，14.115s；另1历史skip单列 |
| 普通NativeHandoff12 | PASS4.491s |
| runtime helper9 | PASS0.978s，unknown/escape/concurrent/hash/import拒绝 |
| actual Core/SDK/SQLite grade route38 | PASS6.415s，原claim/来源/回放/正式grade与relay保护 |

## 部署与校验

6源码/manifest原bytes独占备份 `benchmarks/raw/evidence/phase43-pre-integration`；后增grade test原件也保留。两个宿主的3目标+producer共8原bytes独占备份到其runtime子目录、逐项oldSHA核验后才部署。无用户库/配置/历史、无Sky修改。

两树均为 `benchmarks/raw/neko-product-host` 与 `candidates/N.E.K.O`：

| 文件 | 原SHA256 | 新SHA256 |
|---|---|---|
| _response_arbiter.py | f041135b335a22655bffe14a0856d11f105aa50b56355a0921ec853e7be9aaff | 0dc4d0349d518d4bac4a8a1da034e46bde4624e9fa9aa4079af8539ca32e922e |
| _transport.py | 78df4190470f8d6ec43ae94c2995fa1eef9b3e30a59b3673418b32c6ddacdd65 | 3f15318310c75880a27f4fc1ef2ec961b5472204f36056068df30ea8043bdae8 |
| _tools.py | 41c50034fbba268f58214df34e5f167fb2f45b906d8d8bd4d854ec4922cc05cc | 81a2bb42ac2ac8d264189cb648e655b9dec4097686be1366a013e2b88345489f |
| neko_phrase_input_transport.py | 58bfe9f9513d45b6cb92a4adcedb4d81014e5a85c02870a3f712ac5407f5d07b | d247be713381aae91a71608441f9a06d3be0b5ccb868a8b667c9d70f44ce548b |

manifest由40c8f65425f0ed61a9a64318316b540043e2990b14f63e23b3fda0dcc3f3da71更新为4226ab40401a419bd1618b6e54dac13dde64c731b4bed40072d2182c03713210，原条目保留priorSHA；新增旧清单缺失的arbiter fingerprint（base未知留null，不造base证据）。新增voicepatch/audio/join三个source-only helper hashes，原三个deployed stdlib叶子仍严格allowlist。

先在完整临时project复制所有manifest受核文件/依赖，实际 SourceGate+cwd child imports PASS；未知修改joinhelper negative如期拒绝，恢复再PASS。第一计划生成因旧清单没有arbiter而StopIteration，在任何部署/manifest写入前停止；随后显式补此条目再预检通过。两个实际宿主各目标canonical patched/二次apply already patched，真实SourceGate PASS；独立再次只读核两树8SHA、actualmanifest exact计划、Gate与cwd child import PASS。[独立审查](daily-companion-native-tool-integration-review-2026-10-15.md)未见新增具体P1/P2，不当在线预批。

当前源码：voicepatch5e86fd7db925d268b80a9b6957efb514f1bc49920dd0e4a6681a7adaf790dfb2；join7b9098373bdfda8b14b55bc4d48de79ba776d290a1305d9df4dd1b94ed2e6907；testjoin bd826fa35011d82e150cd415fddc2c1305a100904f56d10015a2d2d58935f857；testaudio062ade9425230b49709fc1c46d23950da4190043e82fd10f87139c0f2218da42。回退只可核current等本轮newSHA后，从独占backup恢复本轮指定文件/原manifest/原source链，不能覆盖未知修改。

## 下一项真实验证与边界

下一唯一场51使用fresh任务store、既有forwardPNG与47三个固定WAV，output-only/speech-gate/phrase-input/grade-chain，复查真实8API保护；不预造题、不用房间/物理/虚拟mic、capture或loopback、不调音量，必要speaker仅用户已设4%。原账本启动前核810/2000、app76/null、tech0/0，不重置。保留单场上限/失败停止/退避，无限重连禁止。

尚未启动时不冒live；未来exec handle/实际报告/额度/cleanup终态另记。仅此阶段部署和离线不代表原50输入失败已解决，不代表provider严格因果/多ASR/第二round、不断连恢复或实际可听/真人通过。全A–F继续，局部失败记录后转其他工作。

## 唯一场51终态：真实连续学习 PARTIAL，有新增通过边界

exec88660已实际terminal/exit1；原report finalized=true、failure=null、turn_timeout未置、cleanup_errors=[]。exit1来自原严格连续检查，不是运行崩溃。raw `benchmarks/raw/evidence/daily-companion-20261015-continuous51.json` SHA256 `851407e50398964ceda04ccc69eca0b360f0eda8a6ad63bbde2260ed414cfef4`，未修改。终态账本原round DS810→831/2000、app76→78/null、tech0/0；只一场，无重跑。Native31820/本场带store的任务进程已不存在，48911/48916/9234无listener，SourceGate结束后再次PASS。

实际renderer policy installed/captureBlocked/readonly、8API均阻断；speaker仅使用用户已设音量，未调音量、未初始化mic/capture/loopback。实际Native AudioContext排程不等于物理可听，human仍PENDING。两个CONNECT包含正式评分的受控换连接，不当无限重连。

| 轮 | 实际证据 | 限制 |
|---|---|---|
| 出题 | 1实际ASR、1实际study_quiz，当前WEX→NUD方向题，未公布答案；0 QA/0正式grade；7正PCM+1空/401720bytes | 单场证据，非全部题型 |
| 答题 | 1实际ASR，同题同attempt唯一正式correct100；1QA/1formal，正式评分20 checks全部true；6正PCM+1空/328680bytes | 排程和文本完整，非物理听感 |
| 追问 | 2实际ASR；保持原1QA/1formal、未换题；解释箭头尖端决定方向且WEX→NUD，未引入50的调用语义猜测；22正PCM+3空/1318040bytes | 第一study_explain实际执行，第二仅wire事件未见执行；尾部约束晚识别，不能当长句分轮已完善 |

完整Native sequence1..554无缺，40 binary=35正+5空，总2048440bytes；不是40个正帧。本场3原输入均完整actual write，第三末尾source_ended并正常结束，没有50的ASR_INPUT_DELIVERY_FAILED/30秒等待失败。可说本场未复现，不能回改原50或断言唯一因果。原first-two同连接、唯一正式评分与追问不误评分共6/7连续checks true，`three_completed_native_turns`仍false；逐轮原checker=[true,true,false]。其第三其他条件成立，唯一两ASR违背原len(asr)==1；未放宽checker、未回写raw冒PASS。

第三实际fixed speech_end1792010864.562、全部输入结束868.370，首文字872.153/PCM872.991均晚于用户输入，但早于第二ASR873.469。第二ASR是后半段短解释/不再评分出题约束，仍有识别分段与晚到约束风险，不把本场无提前发声扩大为自然停顿已全修。实际first study_explain有插件TRIGGER/HTTP200/绑定reply/callID output，second wire study_explain尚无第二TRIGGER/HTTP/output；不凭wire事件冒第二执行成功。

正式feedback19chars/hash a6c6a81135c0ba278b5e4985c070791631e37b93c01d25162f1debac7a403add 与 actual relay裸reply完全同hash；616bytes envelope另hash，不混比。provider5delta累计21chars/hash b3887dcc67b4e0b6e0f8033a5d5fba707fc05b9c83f2d5bf97a1c91cb4c9c4fe == Omni/Core entry/queue/WS/Native21chars，较正式只增2空格；本场无本地反馈截断，仍不解释或改判49。212条无正文study_text_trace由本场probe自动保存。

## 延迟与后续方向

时间从固定WAV实际speech end计，属于这一设备/本场输入的实测，不外推总体性能：

| 轮 | 首ASR | 正式评分完成 | 首Native PCM | 首排程 |
|---|---:|---:|---:|---:|
| 出题 | 6.642s | 不适用 | 11.485s | 11.990s |
| 答题 | 3.834s | 5.917s | 8.713s | 8.715s |
| 追问 | 3.656s（第二8.907s） | 不评分 | 8.429s | 8.431s |

原输入sealed后writer分别16/15/31ms，排队近0ms；上传不是当前主要耗时。答题实际grade_complete→relay_written约0.581s，relay裸reply→首PCM约2.218s；普通quiz/explain工具完成的统一精确测点仍不足，不能凭HTTP事件等同全部下游写完。下一优化要沿真实ASR/工具/generation时点，不随意调timeout或压缩普通打断保护。

[独立场51复核](daily-companion-continuous51-review-2026-10-15.md) 单独冻结。场51是有真实角色工具、模型、SQLite、Native接收/排程的PARTIAL；没有声音采集或本人评价。当前不盲开52。将provider两ASR/晚尾约束、严格多轮与双30秒范围写入blockers，保留恢复条件；转C复用既有store_qa/entry_tutor_context_support/knowledge_graph_guidance，核跨题同概念身份及相关历史真实用于回答，不猜合旧记录、不另造记忆库。A/D/E/F余项和最终集中human仍保留，Goal active。


阶段43已部署/唯一场51：canonical单次join+exactnormalizer、producer exact d247…548b、8oldSHA备份部署+manifest4226…13210；Main无staging runtime2 PASS、自动/phrase40 PASS+1历史skip、handoff12/helper9/grade38 PASS，独立26与实际两树8hash/Gate/cwd imports PASS。启动前账本810/2000、app76/null、tech0/0，policy真实speaker允许/mic/capture/loopback false，原47三WAV哈希与50完全一致。唯一Main exec88660已实际返回live session，fresh store neko-daily-speech-acceptance-20261015-51，report benchmarks/raw/evidence/daily-companion-20261015-continuous51.json；output-only/speech-gate/phrase/grade-chain/prepare-picture/verify-picture，不预造题。尚未终态，不冒通过；poll同handle，不因观测超时重启，不开第二场。默认日常phrase/AUTO OFF、禁mic/capture/loopback、不调4%音量；剩余A–F/原49/50 PARTIAL/Goal active保留。
