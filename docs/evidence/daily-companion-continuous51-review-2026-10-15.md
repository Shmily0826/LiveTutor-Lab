# 场51：连续出题、评分、追问的独立原件复核

日期：2026-10-15。只读范围：本场原始report、现有纯验收函数及原forward PNG；不改原件/实现/共享记录，不读写实际用户DB，不启动服务、provider、Native或设备，不操作账本。执行退出/清理由Main确认，本Agent独立复核report字段与底层观测。

原件：`benchmarks/raw/evidence/daily-companion-20261015-continuous51.json`。
独立实读SHA256：`851407e50398964ceda04ccc69eca0b360f0eda8a6ad63bbde2260ed414cfef4`。

## 结论

本场正式评分链窄通过：真实角色出题、同连接自然声明作答、唯一正式correct100、受控新连接输出，追问后题/成绩不增不变。**连续三轮总体仍PARTIAL**：第三输入在provider端形成两条ASR，严格判据要求恰一条，未因回复语义改善或运行无异常而放宽。

第三回复确实有一次实际 `study_explain` SDK执行/返回证据，并解释正确的箭头尖端方向，区别于场50无工具的“被调用”猜测。另一个后来的study_explain只看到wire请求，没有第二次执行/返回证据，不能算两次成功教学。原49/50及本场原strict FAIL均保持。

## 验收函数与底层正式记录

独立调用现有纯 `grade_chain_acceptance(report)`，结果与原件完全一致：7项中6真，只有 `three_completed_native_turns=False`；内嵌正式评分20项全真。没有修改helper或生成宽松判定。

逐轮 `_completed_native_turn` 为 `[True, True, False]`。第三轮除ASR数量外，其窗口、ASR晚于speech-end、正PCM、同token、文本、system end、排程、source-ended终态条件逐一成立。不是缺帧或环形trace丢失导致的假失败。

| 状态 | QA记录 | 正式answer_evaluate | 题状态 |
|---|---:|---:|---|
| 健康空题baseline | 0 | 0 | 无synthetic pending题 |
| 第一轮真实study_quiz后 | 0 | 0 | 同课程/会话的非空qid/aid、pending |
| 第二轮后 | 1 | 1 | 原qid/aid、evaluated=True、correct100 |
| 第三轮后 | 1 | 1 | 四身份、题、last evaluation、QA及formal对象均与第二轮完全相同 |

新QA的JSON公开题投影qid/aid与held题一致，原ASR全文 `我 的 答 案 是 WEX 指 向 NUD 。` 同时进入QA.user_answer与唯一formal input_text；formal metadata有相同qid/aid和course/session材料context。新QA原row hash为 `d02a09a2379820ec824e66de6739fe307d7ff569b8334bde80e4c32d2ade25c3`，第三轮保持。baseline无旧QA，因此此场“旧QA保留”是空集合检查，不外推已有长期历史的保持验收。

formal feedback：`正确：WEX 出发的箭头指向 NUD。`，reference同方向，covered points明确起点WEX、目标NUD，step_feedback一致、error_type=none、score=100。独立查看原forward图，确为WEX→NUD→REZ；出题未公布答案，作答与评分语义正确。

grade markers为accepted→grade_complete→relay_written，原连接1/scope3的qid/aid一致，result_attempt_id保持原attempt；relay到连接2/scope5、新Native token。前两次完整输入delivery的connection_generation均1；第三输入delivery为2。旧输出退役为真实Native stop receipt，answer终态使用已审完整观测中“source_ended后late cancel”的原规则，不将cancel本身当成功结束。

## PCM、观测完整性和三段输入

最终Native trace实际为seq **1..554连续**，collection完整；累计binary计数与全部audio_frame相等：40帧、2,048,440 bytes。其中**35正帧、5空帧**，不能写成40正PCM。

| 轮次 | audio_frame | 正帧 | 空帧 | bytes |
|---|---:|---:|---:|---:|
| 出题 | 8 | 7 | 1 | 401,720 |
| 评分 | 7 | 6 | 1 | 328,680 |
| 追问 | 25 | 22 | 3 | 1,318,040 |

原三个phrase delivery均 `written_waiting_provider_boundary`，source≥output=written：

- 第一：145,238→140,610=140,610 samples，generation1。
- 第二：75,264→75,264=75,264 samples，generation1。
- 第三：154,046→138,294=138,294 samples，generation2。

每轮仅一个本地sealed delivery。日志timebase仍为 `arrival_derived_sample_estimate`；完整本地写入不是provider ACK。原件没有failure/turn_timeout/native_observation_error，finalized=True、cleanup_errors=[]；所含本场timing没有ASR_INPUT_DELIVERY_FAILED或phrase_provider_boundary_timeout。Main已确认exec88660 terminal/exit1；exit1与严格总体非通过一致，不能因failure为空改成PASS。

## 第三轮停顿与两ASR：不能称完整单轮自然分句通过

下表为原wall时间去掉共同前缀 `1792010000` 后的秒数，仍全部来自同一本场wall观测，非声学物理起止。

| 事件 | 秒 |
|---|---:|
| 固定WAV有效speech end | 864.561983 |
| 本地seal / 完整write完成 | 865.798824 / 865.817278 |
| 第一ASR：为什么这道题要看箭头尖端？ | 868.218 |
| 固定输入发送结束（含tail） | 868.369882 |
| 首Native文字 | 872.153 |
| 首正PCM / 首排程 | 872.991 / 872.993 |
| 第二ASR：短解释，不要重新评分，也不要出新题。 | 873.469 |
| audio_done / system turn end | 876.902 / 876.905 |
| renderer source_ended、remainingSeconds=0 | 887.855 |

本地collector未因内部停顿提前seal成两个输入，且Native回答开始晚于整个固定文件的发送结束。因此本场不能称“还在发送后半句时已发声”。但它**确实在第二段ASR完成前开始回答**，第二段的篇幅/不评分/不出题约束没有作为完整一次ASR进入首答之前。严格恰一条ASR失败有真实产品意义，不能当作无关紧要的计数或直接删掉。

可见追问回答110字符（含空格），三句，内容为箭头尖端确定方向、图中WEX→NUD、反向会读反。没有场50的调用语义猜测，也未重新评分或出题；这些窄语义改善不证明自然停顿、brief约束或多ASR/第二工具round整体已解决。

## 实际解释工具与第二个wire请求的范围

第三轮两条真实wire function-call请求：

- 868.288的study_explain：call ID `eb01f91b-b34a-4c42-a753-4bb0d09aa53e`。
- 876.903的study_explain：call ID `aa616331-6ca6-4626-a76f-1c920e8b6cd2`。

第一条有actual插件TRIGGER、09:47:51.412 HTTP200、trusted/current/native admission、captured/valid/reply binding，以及871.417发送的同call ID function_call_output。随后31段文本、一个可见回答、一个audio_done/system end。原report的DB counts也从第二轮interactions3增至4；QA/mastery/FSRS不增。这支持“首解释确实执行了Study教学工具”而非仅角色口头解释。

第二条位于首次audio/response终态之后，仅wire event存在。所含timing没有第二TRIGGER/HTTP结果，也没有对应第二function_call_output；没有第二可见回答或audio_done/system。其未执行/拒绝的**具体guard原因在本report证据中未知**；不将wire工具请求冒认为SDK执行，也不凭缺日志单独断言某一guard已命中。

## 正式反馈到Native的完整文本边界

grade_reply与实际bare relay_write均19字符/41 UTF8 bytes，SHA256完全相同：

`a6c6a81135c0ba278b5e4985c070791631e37b93c01d25162f1debac7a403add`

envelope为616 bytes、SHA `799d45c358edb972bb136a3c491f5d246b22964ce47e09f0c01de0ce05c9597b`，不能拿它与裸reply比较。

provider答案5个delta的最终 **stream_sha256** 为21字符/43 bytes：

`b3887dcc67b4e0b6e0f8033a5d5fba707fc05b9c83f2d5bf97a1c91cb4c9c4fe`

同SHA/长度出现在完整Omni callback、Core entry/queue/WS及Native拼接文本 `正确：WEX 出发的 箭头 指向 NUD。`。相比正式反馈仅多两个空格，去空白内容相等；没有本地截掉节点或反馈尾句。callback缺response ID，cumulative_available=False如实保留；这里比的是整段callback hash与provider最终stream hash，不把最后一chunk SHA当全文。

第三回复31个provider delta及31个Omni/Core各阶段的逐段hash序列相等；provider最终stream为110字符，SHA `78b762b2001909087bb21a4d25f98e16991b0fea7474b4441560d8a82670e8e6`，等于Native完整拼接文本。第二ASR改变scope后Core累计stream分组不同，不能仅拿末个Core scope分组hash代替整段；上述结论用实际逐段hash序列与Native全文独立核对。

## 权限、预算与最终边界

原forward PNG实读SHA `057d5bac5ae440dfa0d3269f5138f1188fa182bc0fce81435676c6a4caa65dcc`，与report prepared_picture相同；没有重制材料。actual capture receipt为output-only/installed/captureBlocked=True、八项API拒绝；report记录room_microphone=False、capture_devices=False、loopback_enabled=False、volume_changed=False。本Agent未操作这些设备。

原件before/after同round `bargein-autocheck-20261012`，DeepSeek810→831/2000、app76→78/null，tech预算0；本Agent只读取记录，未调用或更改账本。

本场可分别记：正式grade窄链通过、首Study解释执行/可见语义改善、完整Native收包/排程/source-ended且remainingSeconds=0；连续单ASR三轮仍PARTIAL，第二工具请求归属未知。**physical_output=UNVERIFIED_NO_LOOPBACK，human=PENDING**。本报告冻结，不改变原件、checker或先前49/50结论，不为此另开付费重试。
