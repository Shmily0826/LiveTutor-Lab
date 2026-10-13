# 材料替换：Native退役与新材料语音阶段证据

完整contract继续约束现有active Goal。以下是固定输入/真实模型/实际设备路线，真人未验，不是全部A–F完成。

## 实际场景与失败保留

- replacement11：Sky→已有forward，API及角色forward正确，submission空/无cancel/同旧token；terminal479/48/0，失败保留。
- replacement12：已有forward→reverse，API reverse正确，但两轮角色仍forward；scope3实际把旧WEX→NUD→REZ放进text关闭vision/图identity，空submission不能反推空target或SDK过滤。首轮args未采，原因未知。terminal501/49/0，失败保留。
- 实际SDK审查/两个本地桩：非空_ctx/binding在real register/prepare/callback/serialization保留；v2 facade缺recipient fallback。Core/actual registry/remote→SDK local stub正确owner/剥离/原args/target提交，fake Native owner，不是设备。各2local requests，shared ledger不变。
- replacement13：已有reverse→forward，submitted YUI、actual binding、exact旧token cancel/native stop、WASAPI cancel后500ms宽容起3秒静音；connection1→2一次重建。新conn无input约20秒unexpected close，未追问，整体partial；terminal516/51/0。不将重建日志当连续恢复。

## replacement14：本场固定输入设备路线通过

原课/store/已有forward→reverse，复用b71bd0a6a7d164f93682d75a862aeb8938c23bd1da14cdfcc76e96db446fa2f3固定WAV首问和fresh追问。没有paid图预置、重画、房间mic、系统音量改动、供应商切换或旧PCM replay。首轮旧回答播放已确认后提交已有reverse；SDK submitted、current输出binding、精确旧Native token cancel与inactive回执、完整WASAPI静音成立；一次正常重建使用新physical token。

首轮9PCM后被材料更新主动退役，没有完整文本，标`material_retired_not_complete_answer`，不能称完整答复。追问在新connection输入，全新响应22PCM，实际角色：

> 这张图是一条自右向左的单向链：REZ → NUD → WEX。箭头从 REZ 指向 NUD，NUD 再指向 WEX，没有分支或反向箭头。

与已有reverse图事实一致，两句中文，无额外题。保存完整195秒WASAPI WAV51响声bins，cancel后500ms宽容起3秒静音；后续新回复实际系统输出存在。raw `picture-replacement14-final-review.json` 全部checks true，要求report finally after/proof、末轮observation_end/真实turn end/inactive、新token Native前缀；途中report/SDK提交alone不能PASS。rawJSON/WAV/截图只本地、不发布。

exec87197 terminal，native40944不在，48911/48916无listener。最终shared round bargein-autocheck-20261012：DeepSeek537/2000，Lanlan.app53/null，tech0/0；不重置，请求不是金额。本场+21DS/+2CONNECT（initial+one replacement）。

## 源码/离线加固及边界

当前canonical图请求优先最新Study图，忽略模型旧摘要text；无图诚实degraded，literal代码独立。审查发现imageUrl/imagePath/“不要看当前图，只解释代码”的误判，已词边界/literal优先/明确否定修复；Native13真实wrapper/entry/finalizer/SQLite检查过。Host28检查包含可信current角色路由独立捕获、捕获None/failed/string仍剥离host-only binding；这些新增负例只有offline，不借14冒称branch device通过。14发生在最后两项负例加固之前，其当前图正例及cancel算法未改；fresh replay/两runtime部署/AST/idempotence再次匹配。

producer11/UI14/相关language4/course6/image4/failure5过，探针retirement3 guards过。测量只给故意material-retire首轮短观察；普通连续场55秒约束不变，未伪造turn complete。reviewer全WAV而非meter初60bins，末轮terminal与Native token约束已加。可信控制模型不能自行构造，其他role/new input/provider/activation/socket/connection被围栏保护。

仍待：长quiet恢复（13真实失败不可被14短间隔盖掉）、quiz/answer/summary/generic/solution narration输出provenance、密集小字纠正、纯英文/自然长停顿/术语/真人新能力。SDK submitted提醒只能说通知已提交尚未确认，UI14离线和初始browser200不等于实际warning显示。Goal保持active，继续其他A–F。
