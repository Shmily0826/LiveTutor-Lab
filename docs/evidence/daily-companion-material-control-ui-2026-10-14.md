# 材料控制提交状态：UI 增量

2026-10-14。仅修改canonical static `main.js`、必要的 `index.html`，新增定向Node检查及本报告。没有改producer四文件、manifest、host/probe或账本；没有浏览器、host、音频、网络或付费调用，也未重跑旧50项。

## 已交付行为

复用现有 `study-panel__paste-error` 样式，新增独立的polite status区域。`study_submit_image` 返回 `material_control_submission` 有unavailable/not_submitted/exception/submission_unknown（或未识别状态）时显示：

> 材料已更新，但尚未确认旧语音停止；必要时重新开始语音。

已有图片、解释正文及追问上下文继续保留；提示不会删除素材或重试教学模型。全部submitted仅显示“旧语音取消通知已提交，尚未确认旧语音停止。”，不把SDK提交当host消费或设备取消完成。明确空数组清提示；legacy无字段/SDK Err不把已有未知状态擅自判成功。

刷新先走原 `study_status`，随后通过SDK已注册的只读entry `__llm_tool__study_material` 读取相同 `material_control_submission` 字段。生产字段名已核对，无base64或OCR正文读取；没有增加提交图片或模型请求。只读状态读取失败不丢素材、不替换解释、不自动重试模型。

处理实际export Ok/Err包装、value/data及LLM ToolResult output对象或JSON字符串。错误包不显示“材料已更新”的新成功状态；未知包装不崩溃、不清掉已知未确认提示。

原course/material revision围栏继续使用，图片submit的结果与错误额外核当前Session；只读刷新又核status request revision、course、Session及material revision。选新图、课/Session切换清旧提示，迟到的旧返回不能把旧警告写入新上下文。状态提示独立于reply文本，不覆盖已接受解释。

## 离线证据与范围

```powershell
node scripts/test_neko_material_control_ui.js
```

**14项actual UI函数/minimal DOM/RPC stub检查通过**。覆盖4种未确认状态且只提交图片一次、全部submitted/混合状态/空/legacy/未知、实际run-export成功/错误包、只读刷新及读失败、4类迟到metadata围栏、3类迟到submit围栏，以及HTML status accessibility属性和完整JS parse。

这是canonical JS真实函数在Node VM和本地DOM stub中的离线证明，不是浏览器可视验收、host消费、声卡停止或真人体验。主线真实换图音频场独立进行，本子任务未使用相同ports/进程。producer/host的submitted与实际cancel完成界限保留；UI目前没有host取消完成ACK，故不会显示“旧语音已停止”。

交付文件：static/main.js、static/index.html、新scripts/test_neko_material_control_ui.js及本报告。文件完成后冻结，manifest刷新/部署/实际体验由主Agent执行。
