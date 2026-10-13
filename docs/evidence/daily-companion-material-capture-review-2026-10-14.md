# 材料输出capture与调用映射：限定只读审查

2026-10-14。限定读取 `scripts/neko_material_audio_patch.py`、现有Core/tool registry/raw/Gemini执行路径、两份指定raw产物及当前wrapper的材料上下文选择行。仅新增本报告；没有改生产、测试、manifest、账本，没有启动宿主、在线模型、音频或子Agent。主线正在进行Core registry/remote_dispatch→SDK本地桩，本审查不干扰该进程、不把其尚未交接的结果认领。

结论：**未发现正常raw/Gemini路径存在系统性call_id或task映射差异。replacement12的空producer submission不能证明空target或capture失败；第二轮固定text绕过当前图片已有直接证据，首轮同样传旧summary尚无参数证据。** 最新角色_ctx路由独立于Native capture，可消除以前两者耦合造成的诊断混淆，但当前真实device取消闭环不能由此自动升级。

## 已确认的实际证据

- `daily-companion-20261014-picture-replacement12.json` timing_log两次binding admission：trusted=True、current=True、class=OmniRealtimeClient、free=True、tts=False、route=native、lease=core。该日志版本没有native_class/takeover/token_present等新增字段，也没有当前result admission/present/valid或output bound字段；**class名字相同不等于日志已证明isinstance成立**，不能据此锁定某个隐藏拒绝条件。
- replacement12第二轮scope3实际arguments为当前图片问题，但text是`WEX -> NUD -> REZ`。两个turns.native_reply都讲forward；真实替换API解释讲reverse `REZ → NUD → WEX`。因此“新角色已经用正确新方向”不成立，不能引用Study API的正确回答代替角色回复。
- 两次material_control_submission均为[]，cancel_received_wall/native_stop_receipt_wall为null。本场没有证明材料取消发生；这里[]是producer业务返回，不是Native捕获状态或通知传输ACK。
- `daily-companion-20261014-material-sdk1.json`为PASS_SDK_LOCAL_STUB_ONLY；checks证明explicit role经过SDK、native wrapper binding保留、SDK接受控制。实际study_explain binding仅有course/session；study_material列出对MaterialSDKTestRole的submitted通知。这证明显式_ctx与binding可通过真实插件SDK，**不证明replacement12的模型参数、Core角色路由或设备取消**。

## immutable text是独立的实际解释

当前 `study_avatar_tools.py` 在observe和_lock内以`include_material=not text.strip()`构造context；只有has_image_context且text为空才取保存的image。因此非空text请求绑定course/session，不绑定图片hash，使用指定文本解释；同课只换图片后after仍满足该context，按设计不取消固定文本输出。

这项机制能解释第二轮的问题：角色把旧图关系作为text传入，工具即使有正确role、有效capture、成功reply，仍可只依赖旧文本；图片变化既不使其context失效，也不必产生控制通知。它与_ctx是否为空是两个不同问题。主线已在修“当前图片语义优先已有vision”；本审查未修改该逻辑或重复SDK审查。

首轮wire_trace中study_explain的function_call_arguments.done只保存name/call_id/item_id/response_id，没有arguments；timing_log仅第二轮有speech-gate arguments行。首轮forward与当时旧图方向相符，**不能由回复反推它传了旧summary作为text**。首轮summary-as-text仍UNVERIFIED，需要已有更完整回执或下一必要受影响场景的参数记录，不以猜测补齐。

## task / call_id / owner逐层映射

| 路径 | 当前源码事实 | 审查结论 |
| --- | --- | --- |
| raw批次 | `_start_raw_tool_call_now`创建每call任务，并把原call与owner存 `_tool_batch_entry_by_task[task]`；_run→_execute_raw_study_call→_execute_tool_call直接await | 注册发生在新任务实际执行前，无常规“尚未登记”窗口 |
| unannounced response | 与_current_response_id不一致时构造turn_pair_fence_applies=False的owner，随后同样存entry | capture必须用entry.owner；重采live pair会丢特殊fence，最新代码保留它 |
| speech gate等待 | dispatch任务只等待/释放；真正执行时另建raw工具任务并登记其entry。已abandoned的waiting call不进入Core执行 | waiter与execution task不同是有意设计，不是call ID错配；capture位于真正执行任务 |
| Gemini批次 | `_start_gemini_tool_batch`每call创建_execute任务，并用同一call/owner登记；随后直接await_execute_tool_call | 常规Gemini路径也能按current_task取得entry |
| inflight sharing | 首个解释执行真实callback；重复调用等待共享future后复制ToolResult，不重新Core执行 | duplicate没有自己的第二次capture/bind属于去重机制，不能因此推断首个mapping失败 |
| Core闭包 | `_make_tool_call_handler(session)`→_on_tool_call(invoking_session=session)，_execute_tool_call直接await这个callback | 没有另起任务改变current_task；当前session身份围栏有实际意义 |
| 参数增补 | _EXECUTE在capture之前/之后仍使用原call，dispatch用dataclasses.replace或浅copy只改arguments/_ctx | dataclass保留call_id及provider_meta；capture对原call的ID比较不因_ctx增补变错 |
| registry/remote | ToolRegistry.execute远程直接await_remote_dispatch；tool_router发送原call.name/arguments/call_id，HTTP req_id是另一个RPC身份 | SDK日志req_id与provider call_id不同是正常层次，不应拿req_id做capture比较。未见ID系统性重命名 |
| task退出 | _track_tool_task完成回调移除entry；abandoned由既有retirement路径标记 | callback尚在同执行task内时正常entry仍在；若确被退休，拒绝符合owner合同 |

涉及文件：`main_logic/omni_realtime_client/_tools.py`、`main_logic/core/tool_calling.py`、`main_logic/tool_calling.py`、`main_routers/tool_router.py`，均只读现有运行树源码；未全仓搜索或CodeGraph重查。

## 最新capture的具体拒绝条件

最新 `_capture_study_material_tool_owner`仍会在以下情况下返回None，当前结构日志可逐项缩窄：

1. call.name不是study_explain、definition不存在或registry source不是plugin:study_companion。
2. invoking_session不是当前session，或并非所导入的OmniRealtimeClient类实例；光有type名字不够。
3. 非free proxy、use_tts=True、takeover_active=True，或native_output_connection_token无native_connection_前缀。
4. 当前task查到entry但entry.abandoned=True，或entry.call.call_id与原call.call_id不同。新增binding rejected日志区分这两项；没有entry则fallback捕获owner，本身不是立即拒绝。

当前capture不再把_has_server_vad、route必须native、lease必须core作为前置硬拒绝；它保存input_route/input_lease，由control应用时确认没有换路。旧版本可能曾在上述条件拒绝，但replacement12缺少完整字段，**未确认它当时命中哪项**。

即便capture成功，result仍可能不绑定：is_error、非dict/不可解析JSON、缺或非法record、degraded/ok=false/无字符串reply、callback等待期间session/socket/owner/activation已变化。owner-current又包含connection、scope、provider session及适用的turnpair围栏。正常生成/返回与换课、barge-in、连接替换竞争时，这是预期拒绝；需要result admission和binding present/valid/owner阶段记录才能区别参数/SDK/退休原因。

最新可信current study_explain角色_ctx注入独立于material_owner是否存在：只核注册来源和invoking_session身份，取manager真实lanlan_name并覆盖模型_ctx，保留原arguments用于inflight key。故“capture=None→必无target”这个旧耦合推论已不适用于当前代码。若真实manager role_length为0仍会无有效target，但replacement12现有日志没有该字段，不能断言。

## 最小接续与证明边界

主线正在做的真实Core registry/remote_dispatch→SDK本地桩即可验证：实际handler task是否有entry、原call ID匹配、role_length、result binding是否valid及material owner是否current。复用现有结构日志；需要时只补entry_present/拒绝reason/owner-current布尔，不记录整段图片/OCR或额外读取仓库。该验证不需要新付费模型或语音。

语义优先修复后，下一次必要图片场景必须记录工具实际question/text、binding context是否包含图片identity、producer控制提交及真实cancel回执。不能只看SDK200、submitted数组、旧音频自然播完，不能把API新图reverse借给Native forward回答。当前27项离线与SDK桩结果仅各自层面；本审查没有新增实际模型、设备播放或真人通过。

本报告冻结。仅此新增文档；其他源码、测试、manifest、学习数据、预算和运行进程均未触碰。
