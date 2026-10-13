# 材料替换阶段五：独立限定变更审查

2026-10-14。只读canonical `study_avatar_tools.py`、`scripts/neko_material_audio_patch.py`、`scripts/neko_daily_voice_probe.py`、`scripts/neko_material_replacement_review.py`，以及literal guard测试的精确新增片段。仅新增本报告，不修改生产/测试/manifest/账本，不启动宿主、在线、音频、进程或子Agent。

当前结论：限定范围未发现P1，三项P2已源码/主线离线修复，见末节最终复核。可信role路由和旧owner取消复用未见新的正常路径绕过。下列保留发现与修复过程，不将量具缺口或局部项扩称整个Goal阻塞。

## P2 图片意图覆盖literal source：已源码/离线修复

最初current_picture采用image子串加“这/this”提示，会把“解释这段代码里的imageUrl”“Explain this imagePath variable in the supplied code”误当看图请求；即使有学习者literal text也清空，转去旧图片或visual_context_missing。明确拒绝当前图片的代码请求同样误判。

主线修正后，英文visual nouns有word boundary，literal source intent在非明确current-picture focus时优先，explicit rejected_picture保留代码。限定读取确认以下四个原例得到保留text路径：

- 解释这段代码里的imageUrl；this imagePath variable in supplied code。
- 不要看当前图片，只解释下面代码；Do not use the current image; explain this source line。

“这段SVG代码里的箭头markerEnd”也因明确literal代码且无explicit current-picture reference而走source。相反，“核对当前Study图片”仍清掉模型塞入的旧summary/arrows text，并保留vision/hash绑定。这一对比解决已找到的P2，不保证所有自然语言意图都能由regex准确分类；模糊请求不能用规则匹配冒充真人确认。

主线报告Native guard13项离线通过，本审查没有运行测试或安排在线重验。schema继续要求literal code/notes才放text，当前图应省略text；只靠text非空不能放行旧图摘要，该限制保留正确。

## P2 host-only binding剥除范围：发现时待修，最终复核已解决

`_bind_study_material_tool_result`在captured=None或result.is_error时先return；随后只有解析出valid record才删 `_study_material_binding`。但最新可信current study_explain的_ctx路由已经独立于Native capture：TTS/非Native/其他capture拒绝下，成功插件结果仍可能带binding，直接继续进入provider prompt。invalid record也不会剥除。

因此“host-only provenance不进provider”只在captured+valid部分成立。内容是课程/session/hash等控制元数据，不是已证实的密钥泄漏，本审查不升级为P1；它不该被模型当作教学内容或来源事实。

最小建议：在已核可信study_explain来源的结果路径先剥私有binding字段，独立于capture/record validity，再决定是否绑定到Native owner；保持原reply/业务字段及其他工具的业务output不变。补captured=None但可信成功binding、malformed private record两个定向离线负例即可。不得通过放松capture owner/type/token守卫来“修”字段泄漏。本审查未实现。

## P2 完整WAV reviewer缺收尾 / terminal门槛：发现时待修，最终复核已解决

`neko_material_replacement_review.py`以`not failure and not turn_timeout`标session_normal，没有要求report已完成finally或末轮有真实terminal。probe在过程中反复保存report；某份中途产物只要已出现cancel/queueStop、quiet窗口和新token帧，且尚未写失败，就可能被判PASS_THIS_FIXED_DEVICE_SCENE_REQUIRES_FACT_REVIEW。缺failure不是正常结束证明。

最小建议：probe明确保存finalized/正常末轮terminal事实，并由reviewer强制检查；至少须有final阶段独有字段与完整两轮记录，再匹配实际followup完成证据。手动end_session与宿主清理本身不能代替角色回复terminal；first answer被material retirement主动取消也应继续独立标retired，不冒充完成答案。用“同一已通过形状去掉finalized/terminal”的离线负例即可，不必重跑设备。

`followup_uses_new_token`当前只核非空且!=old。建议再核native_connection_前缀，避免未来把TTS/theater的其他correlation ID误标新Native连接；当前主线第14场确为新Native token，不据这一建议否定已记录22PCM。

## owner/cancel与shortcut：本轮确认的正确边界

- Core_ctx只在可信注册的study_explain、invoking_session仍当前时取真实manager角色，覆盖模型_ctx；不改原arguments/inflight key，不改变原call_id。capture另核OmniRealtimeClient/free/TTS/takeover/token，优先实际batch entry.owner保留unannounced fence。
- binding仍核成功reply/record、当前session/socket/工具owner/activation。control按boot/seq/context及原input route/lease、physical connection、user epoch校验，旧控制不能借新binding取消新owner。
- swap是独立shielded task，工具scope退休不取消swap；pre-frame阶段只装专属output hold，不阻输入或TTS。frame锁内准确取消旧physical token；每个后续await都有相应owner/connection复核，normal connect只接受original+1，异常不收作更高generation新owner。
- 之前发现的“cancel已提交后，仅同旧physical连接新input”已有failed_owner_current分支：精确旧connection仍被拥有时有界关闭并明确提示重新开始，避免永久token已retired却残留无解释静音；新physical connection不在这条fallback内。没有PCM replay、无限connect或改普通onset架构。
- `material_retirement_observed`要求submission阶段已完成、旧播放active、exact old token的cancel、native_connection_cancel inactive以及当前snapshot playback inactive。它没有把SDK submitted当queueStop；不同token的stop不能通过。
- shortcut只让**首轮故意被替换的答案**停止等待，标`material_retired_not_complete_answer`；之后发送新的固定WAV，不借旧reply假装第二轮。新场能避免上一场新连接20秒无输入超时，但不等于无缝保存更换期间所有语音输入。

本轮未发现上述正常复用路径新的误取消新owner P1/P2。scope仅study_explain Native路线；未覆盖全部quiz/answer/queued narration/任意桌面材料声音。

## WAV、真实场与验收层

完整WAV reviewer读取保存的全部int16多声道样本，int32求abs避免-32768溢出；每250ms按峰值，允许cancel后500ms endpoint/bin宽限，检查其后三秒窗口中至少10个quiet bin（peak<=.02）。不是meter JSON前60桶截断；threshold/宽限是当前量具定义，不等于人耳“立即停止”。system loopback也可能含其他系统声音，输出scope已明确不能证明语义或真人听感。

真人字段始终PENDING，自动result也保留REQUIRES_FACT_REVIEW，正确。完整WAV只回答信号时间窗，模型方向、简短/语言、实际新材料与回复的对应仍须另核，不能从响声推导。

主线交接的实际场边界：第13场exact old cancel、Native inactive、WASAPI静音通过，但新连接无输入20秒close，整体PARTIAL；最初第14场仍在运行时不能提前认领。后续主线通知第14场已terminal、failure=null，新token22PCM且fresh reply为REZ→NUD→WEX，**本审查未读取该场完整raw/WAV，仍只把它作为主线新交接事实，完整WAV review由主线执行**。不将第13局部成功、14中途帧或SDK提交扩大为真人通过。

报告冻结。本次外部请求/音频为0，没有触碰生产、学习材料、原数据、预算或运行进程。待修两项可用定向离线检查推进，不需要为量具再开付费会话。

## 最终复核与冻结

主线修订三文件后，本审查限定重读相应代码，确认以下修复：

| 修复 | 当前源码结论 / 证据层 |
| --- | --- |
| host-only binding统一剥除 | _EXECUTE在可信study_explain结果路径删除私有字段，独立于captured、is_error、record有效性；可解析JSONstring也处理，不清其他工具的业务output。_bind决定owner，不能绑定的结果仍经统一strip。**P2源码解决**；主线提供28方法离线通过，本审查未运行 |
| finalized与terminal | reviewer强制非空after dict+proof；要求followup observation_end、无turn_timeout、实际system turn end位于followup input之后及最终playback inactive。中途report缺final阶段字段不能PASS；首轮retired保持独立含义。**P2源码解决** |
| Native token范围 | reviewer及probe followup检查均要求native_connection_前缀且!=old，其他correlation不能冒充新Native token。**源码已补** |
| literal source范围 | canonical四个原例及明确拒绝图片由literal优先保护，主线Native guard13离线通过。**源码/离线通过**，没有为这一分支单独在线 |

未发现本轮剩余必须修的P1/P2；本结论仅限列出的文件与条件，不等于全仓稳定性或所有自然语言都可靠。

主线通知 `actual14-final-review` 全部checks通过，维持human=PENDING：第14场是此前已部署的current-picture路线，正确reverse回复/newNative22PCM、exact old取消、完整WAV判据由主线取得并复核；**本审查未自行运行或读取整场音频，不称独立设备验收**。新增noncapture stripping、literal source负例只拿各自源码/离线证明，不借第14场声称这些分支也有设备通过。第13场整体PARTIAL保留，不能由后场覆盖其20秒无input失败。

最终报告冻结；本阶段仅新增这一文档，外部请求/音频/宿主/测试运行均为0。
