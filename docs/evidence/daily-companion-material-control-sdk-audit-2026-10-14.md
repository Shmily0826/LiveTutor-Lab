# 材料控制空目标：真实 SDK 调用链离线审查

2026-10-14。只读当前host runtime SDK/调用链与canonical producer；只新增本报告及 `scripts/neko_material_control_sdk_audit.py`。没有修改producer、host、已有test、manifest、账本或进程，没有host/audio/网络/付费调用，没有新Agent。

主线报告replacement11/12新图方向正确，但submission=[]、0cancel、同token，Core capture诊断trusted/current/native/free正确而target空；两场结束累计501/49/0。本审查没有重跑这两场或读取/改写账本。它们证明取消没有发生，不单独证明SDK丢参数。

## 已离线复现与未复现

**已复现：**真实 `plugin.sdk.shared.core.context.SdkContext` 没有 `_current_lanlan`，也没有public `current_lanlan`。legacy `PluginContext.current_lanlan` 在真实ContextVar scope内是正确角色，但SDK facade不转发这两个访问器。producer `material_output_target(host,{})` 读取facade私有属性时返回空。缺 `_ctx` 的真实native wrapper仍可返回 `_study_material_binding`，但不会注册任何output target；随后UI setter没有target可通知，submission=[]符合该条件。

**没有复现：**给调用链明确非空 `_ctx={lanlan_name:ExactRole}` 后，真实动态入口/prepare_kwargs没有丢它，实际producer注册ExactRole；boot/context binding被host序列化及callback返回层保留。不能将空target场次归因于已证实的“SDK wrapper必定丢_ctx”或“返回序列化必定过滤binding”。

## 精确源码链

- Core `_on_tool_call` 的material owner分支复制arguments并写可信 `_ctx`；关键前提是该分支实际执行且self.lanlan_name非空。capture诊断对象可信，不自动证明这个前提或实际dispatch参数。
- `plugin/sdk/plugin/base.py:517-548` `_register_llm_tool_internal` 将原bound handler交给实际 `register_dynamic_entry:338-378`；`collect_entries` 将动态handler直接包成EventHandler。input_schema不是params model，动态meta.params为None。
- `plugin/sdk/shared/core/entry_runtime.py:52-89,172-204` 在无params model时只删除handler不支持的host `_ctx`。actual `study_explain_tool(...,**_)` 有VAR_KEYWORD，所以它明确支持并保留该参数。
- `plugin/core/host.py:1660-1691` 从arguments读取lanlan_name、设置legacy私有值并进入 `_lanlan_scope`，调用prepare后原handler。`:1694-1705` 返回data直接是result或SDK Ok.value，没有按llm_result_fields删除binding。
- `plugin/server/routes/llm_tools.py:150-218` 向trigger原样交arguments，再把普通producer dict放进output。实际普通返回的 `_study_material_binding` 是output内字段，JSON往返保留。
- `plugin/core/context.py:622-634` 的public current_lanlan是ContextVar；legacy `_current_lanlan` 是主循环逐请求改写的普通字段。不要为修空目标改为读取“上一个调用”的可变私有字段，那会产生跨角色误取消。实际SDK facade见 `plugin/sdk/shared/core/context.py:108-247`，未暴露recipient accessor。

## 离线量具

```powershell
& benchmarks/raw/neko-product-host/.venv/Scripts/python.exe -I -B scripts/neko_material_control_sdk_audit.py
```

成功输出确认：

```text
registered_entry=__llm_tool__study_explain
ctx_retained_through_actual_callback_prepare={lanlan_name:ExactRole}
binding_survives_actual_host_and_callback_serialization=True
real_sdk_context_type=plugin.sdk.shared.core.context.SdkContext
legacy_contextvar_role_visible=True
sdk_private_recipient_visible=False
sdk_public_recipient_visible=False
producer_no_ctx_target=''
no_ctx_still_returns_binding_but_registers_no_target=True
external_calls=0
```

量具使用真实NekoPluginBase registry方法、真实EventMeta、真实prepare_entry_kwargs和SdkContext；canonical producer真实wrapper/entry/finalizer与fresh SQLite；只fake模型backend和本地trigger运输。callback执行真实AST函数（不导入服务startup），host结果处理执行真实AST serialization分支。legacy context使用实际dataclass字段及原ContextVar方法AST，避免整个legacy core import带入provider/config初始化；没有用SimpleNamespace当SDK ctx来证明角色可见。

最初完整legacy context import带入配置/voice-provider注册表读取，产生Windows stdout编码日志；没有打开设备/host或外部服务。第一版AST选择错了serialization所在try块而失败。随后限定AST字段/recipient方法并从实际分支树定位，以上结果才通过。不把早期导入/量具失败伪称通过。

## 最小接续建议与边界

1. 主线先在actual registry.execute之前、remote dispatch arguments、prepare之后各记录has_ctx/role长度（无需保存原问题/图片），确认Core injection是否发生、role是否非空。如果入口收到正确ctx，本审查证明无需修改SDK prepare/动态注册来保留它。
2. 如果role只能从SDK context取得，优先让facade公开task-local recipient，或使用已验证的调用级 `_ctx`。不能把facade无私有属性“补救”为全局/上次角色，也不能广播取消。
3. binding缺失与target缺失分别诊断：缺ctx仍可以有binding；成功返回中field位置是callback.output内，宿主应按真实ToolResult shape读取。host own current/scope/connection绑定与消费逻辑由主线独立审查。
4. 这不是新版取消成功证据。修复后仍需由主线受控设备场验证准确旧token取消、旧声停止、新图及新语音方向。保留submitted仅SDK接手的定义，不以一次字段出现当实际播放停止。

本限定审查完成，脚本/报告冻结。生产修法与下一次有意义的真实验证由主Agent安排。
