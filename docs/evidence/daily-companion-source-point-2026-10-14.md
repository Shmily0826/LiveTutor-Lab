# 源码指示与语音事件顺序：定向增量

本阶段承接已发布 `codex/daily-learning-companion` / `3c2bc065925f4e539ba8c18b2027a1908727001f`。不重跑旧图片quiz闭环，Sky Scout只读、原图不变、沿用共享ledger，不采房间麦克风。下列阶段尚未发布。

## 实际失败及修复

同一固定中文单条指令包含0.900秒句内停顿。WAV SHA `9d91a87b76074e6a45bff25dbd4fee626b4812e172d9b7864c9a5ea33777574c`，离线Huihui生成、固定输入→RNNoise，native使用假静音采集设备，系统音量未改。

- `role-point-single.json`：两个ASR片段，tool早于completed55/33ms，本地scope退休取消当前tool；0pointer/0audio，另有409。准确原因不等于所有失败只由scope引起。
- `role-point-ordering2.json`：有界派发顺序修复后真实工具拒绝被角色播放，7binary/12回环响声；role猜`.code-line:nth-child(13) .function-name`且漏材料ID，409，指示未过。
- `role-point-source3.json`：source便利入口后仍没有pointer，角色误说没有fetchWeather声明。实际CodeGraph标题是文件名后带“—符号说明”，第一次解析仅接受裸标题，造成缺source metadata。没有覆盖这项真实格式的旧synthetic tests不能替代当前证据；此失败保留。344 DeepSeek/38 app/0 tech，第二CONNECT来自实际native输入中旧回复触发普通handoff，非无限重连。

已修真实标题格式并在闭合源码块后清来源，防止后续无来源示例继承原file。九项实际method/callback、本机HTTP守卫通过；重放source3里已有过滤CodeGraph返回，提取37个源码target，唯一真实fetchWeather声明为原file第13行、显示selector `[data-line="evidence-56"]`。不重新读取仓库、不扩大授权。

## 当前定位边界

source mode从当前已选择filtered CodeGraph证据的file/line/symbol选唯一目标。不存在/歧义/非法line/非源码材料拒绝；显式旧ID及GET→POST换材料拒绝。没有额外读取能力，HTML正文转义，仅有限前80个target。symbol是字符串hint，不是CodeGraph符号身份。省略材料ID只承诺当前显示版本，不能认证模型旧解释的版本。

有界late-ASR兼容修复只用于free app无先行server-VAD且近期未转录speech；原connection/session/foreign scope固定，一次expected ASR推进可让当前未执行call继续；慢host callback另等最多2秒。六项候选、工具生命周期五项、打断十九项离线回归通过。实际工具返回/播放已有部分证据，完整输入和自主定位仍单独验。

当前_tools.py和_transport.py均加入/更新startup fingerprint gate，双运行树hash相同。Function/terminal response ID不一致在已有unannounced fallback不导致挂起，没有新增singleton alias。缺稳定input item身份仍是时间邻接兼容性启发式，不能冒称完整语音endpointing或普通真人打断重新通过。

下一场 `role-point-header4.json` 在确认真实metadata存在后才允许音频连接，只验证上述格式修复受影响路径；设备结果结束后补录。新量具显式给pointer/DOM/native文本/回环/正常结束分项acceptance，failure=null不再被当成成功。真人体验待用户“准备好了”。

## header4 实际结果

实际role两次POST均使用当前同一material `code-7e262c521a62587b304ea944`、selector `[data-line="evidence-56"]`、原file第13行label。shared web-inspector三项实际检查通过：声明文本确为13+fetchWeather、学习者滚动后高亮可见、command当前material一致，无page error。角色确认文本“已将光标移至第13行。”，native播放及WASAPI9响声片段；故仅pointer/render/device路线 `PASS_FIXED_INPUT_DEVICE_ROUTE`，不等于全部语音目标。

第一accepted指示wall1791903737.417在speech end1791903743.109之前；第二accepted1791903745.197，随后末片ASR1791903745.256；末片首audio.delta1791903746.769。仍有提前指示/两片ASR，native普通handoff引出第二CONNECT；额度344→350、app38→40、tech0，同轮未重置。该场结束本任务host/native/surface/meter均关闭。

确认措辞把highlight说成“光标”不准确；实际只提交高亮，没有编辑器光标操作。已去掉工具描述里的具体13/fetchWeather示例（避免不完整前片从样例猜目标），增加只确认高亮请求、不声称移动cursor/scroll/edit/render的relay，以及定位失败不代表函数不存在的next说明。九项callback/localHTTP在这一增量后再通过；最新措辞仅源码/离线检查，未为文案再开付费连接，真人/下一次必要语音场景核验。

剩余B准入方案见spoken-turn-analysis：仅quiet等待不足，还需最后ASR接收时刻覆盖最后speech与callback ready，owner固定，下一scope丢弃首候选。point同样出现提前动作，需要纳入相同受控准入评估。尚未实现，不借定位成功宣称完整长句通过。
