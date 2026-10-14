# 阶段37：正式反馈到 Native 文本的边界调查

2026-10-15，独立只读/纯离线。范围：`neko_native_grade_patch._relay_study_grade_once`、canonical avatar `_teaching`/`study_answer_tool`、实际 host Omni输出转写与Core文本发送。仅新增本报告；未改实现、共享记录、原raw、DB或账本，未启动应用/服务/模型/音频/捕获设备。

## 结论

**当前根因 UNKNOWN，未找到该句的确定性本地截断反例。** 本地实际纯处理段离线传入完整反馈时能够完整发到假WS。场49确实证明正式反馈22字符，而Native仅收到7字符；它没有保存provider原始转写长度/内容/hash，因此不能凭“只有1条delta”断言provider原始转写就是短句。

调查不改变场49整体PARTIAL，也不削弱owner、hold或late输出拒绝。Main正独立修改观测3文件；本报告不干预其实现。

## 已核源码路径

1. canonical `study_avatar_tools.py:1120–1191`：`study_answer_tool`把正式entry payload经 `_first_text(feedback, reply, summary, explanation)`选出feedback，再将它作为 `_teaching(reply=feedback, ...)` 的reply，附relay说明和身份，绑定结果返回。没有在WEX、空格、冒号处切句。
2. `_teaching`（141行）只对说话字段调用 `_speakable`；其regex去除fence/backtick markup并保留段落。此句不含对应markup。`_relay_for`只改变如何朗读的指令，不截reply。
3. `neko_native_grade_patch.py:220起`：controlled relay在原owner/精确新conn/token/scope守卫成立后，把 `verdict, score, reply, relay` 整个字段值json.dumps，前置authoritative指令，通过user input_text的conversation.item.create交给既有arbiter；无substring或句长限制。send_guard/precommit均是整体准入。只证明本地构造不截，`ticket.sent`不证明provider实际接收或照读。
4. 实际 `_transport.py:4181–4199`：音频转写delta读取 `event.get('delta','')`，按print标志缓冲或交 `on_output_transcript(delta, ...)`；本段没有长度截取。done与response terminal也有buffer flush路径。跳过/静音/旧owner可整体丢弃某些callback，不能据静态代码排除本场发生这些guard变化。
5. actual `Core.turn.handle_output_transcript`（2335行）先检查takeover、grade hold、proactive owner，再把原text交 `send_lanlan_response`；TTS关闭路径不再切文本。后者（2414行）唯一此处文本转换为 `self.emotion_pattern.sub('', text)`；实际 `manager.py:166` pattern为 `<(.*?)>`，不匹配本句。清洗后同text入sync queue、缓存和WS gemini_response。
6. telemetry当时每个incoming text事件仅slice(0,12000)，22字符不会触及该界限；第二轮172events未触500上限。因而本场短文本不是已知ring淘汰或12000截取造成。

## 实际源码纯离线重放

使用已有Source Python，stdin脚本仅AST抽取上述函数/赋值，不import app/Core/audio模块、不启服务、不写生产文件。输入：

`答对了：WEX 是起点，箭头终点是 NUD。`

字符数22，UTF8 SHA256 `24feede4e4a5e7c6c44017340fdce973c9967a3a9917f188461c411ec101e8e8`。

独立断言均通过：

- actual `_first_text`→`_teaching`/`_speakable`，reply与输入精确相等。
- 从actual `_relay_study_grade_once` AST抽取实际text赋值表达式，用上一payload构造JSON，解回reply与输入相等。这是构造表达式重放，没有重新测试整个reconnect/arbiter。
- actual `handle_output_transcript`→`send_lanlan_response`，用真实emotion regex、无takeover/hold、use_tts=False、假socket/queue及focus/echo seams，最后WS message.text精确相等。
- actual Omni `_take_pending_output_transcript`→`_emit_pending_output_transcript`→`_flush_pending_output_transcript`，给完整buffer、audio_delta_count=6并接上述Core callback，最后WS message.text精确相等。

证明范围是上述健康条件下纯文本转换的透明性；没有复刻49每个guard变化、provider/session事件驱动全过程、SDK评分或实际声音。不得将这些断言称完整runtime E2E，亦不能据其排除条件性本地丢失后续chunk。

## 场49留下的明确事实与空白

原件SHA `60988217eff6581fa038736e6d6cde71283ca4fb778f808894455c03da3e1148`（前一报告已独立核）：正式grade.feedback为上面22字符；Native唯一gemini_response为 **“答对了：WEX”**（7字符），不是完整反馈。

wire该response记录audio_transcript.delta计数1、audio.delta计数6、response.done completed，但wire没有该delta的文本/长度/hash，也没保存relay投影reply在实际发送边界的hash。**单delta可以含22字符，也可以含7字符；事件数量无法裁定。** response.completed也只代表协议终态，不证明内容完整照读。

另已独立确认答案PCM在source_ended后30秒才speech_cancel；该late cleanup不能直接解释此前Native文本前缀。无loopback/human，不能用169320 PCM bytes估算并宣称实际读完22字符。第三轮ring淘汰是另一个量具问题，不能借它解释第二轮文本。

## 最小下一证据（不盲重跑）

先从现有49日志查是否已有精确len记录；没有就保持UNKNOWN，原raw不能补造。若Main以后因实际修复需要单场验证，以下是足以定位的最小同response计数/hash链，避免记录题全文/PCM：

| 边界 | 应采窄数据 | 能区分的缺口 |
|---|---|---|
| 正式tool结果→relay投影reply | chars、UTF8 SHA256、已有claim conn/scope及stage | SDK结果到relay构造是否改变 |
| conversation.item.create实际本地write | 投影reply同hash、完整event bytes/hash及written结果 | 构造与wirewrite是否不同；不冒ACK |
| provider audio_transcript接收、任何guard前 | 该response增量index/字符数/hash及有序累计chars/hash | provider原始文本短，还是本地后续guard丢失 |
| Omni callback调用前 | 相同文本计数/hash、分支/是否bufferflush、guard/drop安全bool | transport到Core边界 |
| Core entry与清洗后最终queue/WS | 原/clean chars/hash、是否published、已有conn/turn对应 | emotion过滤、owner退休或发送失败 |
| Native接收 | 对应累计chars/hash、完整本轮semantic事件 | server send与renderer观测差异 |

完整JSON event hash与reply hash必须分开；采用同UTF8定义，不拿包含relay指令的JSON hash去比裸反馈。多个delta按实际有序接收累计，不自行拼ASR或虚造provider utterance ID。仅存在同profile/response/物理connection对应的证据才比较；缺任何关键边界应继续未知。hash/长度是诊断，不是授权、ACK、听见或新评分判据。

## 本次源指纹

| 文件 | SHA256 |
|---|---|
| scripts/neko_native_grade_patch.py | `0e9a8054860690ec3675b567507453d07c2c93fb150fde492db94cc987afec99` |
| canonical study_avatar_tools.py | `45e6bed56a136d067f832ceb9952aa941331be7507b81eb093df6e8280743f50` |
| actual host Omni _transport.py | `634ec3f9a681bf0a4fc1e63a554fcae6a87ca3b5dafd7e914ec234a36ffed853` |
| actual host Core turn.py | `4513a0a76f94e39097a2fce7e0be5b66aaf3d59baecbc8e4e907f2e221b93f1e` |

报告冻结。没有新线上请求或设备动作；没有把source/offline结论升级成provider/physical/human PASS。
