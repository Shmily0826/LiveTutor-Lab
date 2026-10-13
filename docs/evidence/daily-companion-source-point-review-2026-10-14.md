# 当前源码指示：定向只读审查

日期：2026-10-14。仅审查 `scripts/neko_learning_surface.py:103-149`、product `study_avatar_tools.py:435-508` 及新 `scripts/test_neko_source_point.py`。没有修改生产文件，没有启动HTTP服务、宿主或音频，没有外部请求。已有7项测试由主线报告通过，本次未重跑旧批次。

## 主路径结论

原始行号解析与当前材料校验可以替代模型猜CSS：surface只在带文件header的代码fence内识别数字+tab前缀；point必须是正整数（拒绝bool、str）；只从当前被学习者选择的 `filtered_codegraph_evidence` 元数据选唯一目标。完整file路径或basename可以缩小候选；symbol是去空白、casefold的文字hint，并不是额外的CodeGraph符号身份。

HTTP snapshot取得当前material ID后，POST仍由surface锁内确认其存在且当前active相同。换材料/新版本替换旧material时会拒绝旧ID；command只采用解析出的selector和原file:line label，kwargs不能覆盖kind/material identity。这部分未发现跨材料指示绕过。正文HTML escape避免源码字符成为脚本；source证据长度有限、只展示本次上传内容，指示没有读取额外源码的能力。

已有测试覆盖唯一file/line/symbol、跨文件同line歧义、未展示行/符号、非法line、显式旧material ID、snapshot→换材料race和无identity的猜CSS。它们证明工具/服务元数据路径，不能证明实际页面已渲染指示，更不能证明模型完整理解原代码。

## 可行动发现

### [P2] 无来源header的后续代码fence继承上一文件

来源：`scripts/neko_learning_surface.py:112-125`。`in_source`在闭合fence时关闭，但 `source_file`仍保留。因此后续示例fence里的数字+tab行会被标成上一真实文件的原始行。

无socket的实际方法探针：用 `LearningSurface.__new__` 初始化内存字段并调用原 `show_code_evidence`。输入先是 `**lib/weather_service.dart**`（实际backtick格式）+源代码13行，闭合后加入“Example, not a source excerpt”及没有新file header的第二代码fence，其中包含 `999\tfetchWeather(exampleOnly);`。结果metadata为 `[('lib/weather_service.dart',13), ('lib/weather_service.dart',999)]`。999是示例行，不是该文件已返回的源码。

如果当前CodeGraph formatter保证每个数字tab fence都只包含原源码，这不会触发本场正常流程；但解析方法本身没有强制该来源契约。建议闭合source fence后清除file上下文/要求下一来源header，或显式区分由工具构造的source片段与说明markdown。增加这一个定向检查即可，不需要大范围重验。

### 省略material identity时，只承诺当前显示版本

来源：`study_avatar_tools.py:477-492`。便捷source mode允许省略material_id并自动使用当前active ID。这样可以对当前显示源码指点，但如果模型持有旧解释，而学习者切换到新版本、同文件同line同symbol仍存在，无法识别这次解释来源旧版本。已有旧版本测试只覆盖明确传旧material_id的情况。

这是当前方便入口的支持边界，不是snapshot→POST的race漏洞。应写清楚“解析当前显示证据”；若目标包括拒绝旧解释对新源码的指示，需要将study_code返回的material/version identity作为可校验hint，并在模型持有该hint时强制核对。不要把省略ID路径称为绑定原调用源码版本。

## 其他准确性边界与剩余工作

- 仅前80个target可定位；更后面的可见行会返回未展示/不唯一。这是有限元数据支持范围，不应说整份文件都可指示。
- symbol只匹配label前160字符的文字；长行后段的identifier可能无法定位，注释/字符串内同名文字也不证明函数身份。工具已把成功结果标成locator metadata，不应升级为源码关系事实。
- file hint规范化用户输入反斜杠，但surface header file值保留原文本。若真实formatter输出Windows反斜杠路径，需要同样规范化metadata后比较；当前forward-slash fixture不覆盖它。

主线计划中的同WAV受控角色point验证由主Agent安排；本审查不启动或追加在线场景。实际render、设备播放、真人体验仍分别验收。

## 增量核对：无归属示例fence已解决

主线已在closing source fence处清空source_file，新fence仅在已有来源header时进入source模式。源码核对 `scripts/neko_learning_surface.py:119-126` 确认上面999示例的继承条件已消除；主线新增该复现并报告8项实际callback/localHTTP通过。本审查未重跑整批。该P2标为**源码/离线已解决**。省略material identity指向当前显示版本的边界会由主线明确记录，仍不宣称绑定旧解释来源版本。
