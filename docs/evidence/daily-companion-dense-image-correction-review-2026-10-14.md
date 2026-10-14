# 密集图纠正追问：只读审查

完整承接 contract、plan、status、blockers：阶段八已发布080d69a，长期Goal active；581/2000、app56/null、tech0/0，未重置。Main独占phrase Core/transport/部署等，本轮只读范围为 canonical explain entry/avatar wrapper/OCR pipeline，加它们直接使用的材料/上下文/图像小helper必要片段。没有SDK/model/host/audio/外部调用/账本/进程/新Agent。

continuity10把“天气未命中”误读成“天气命中”是继承的实际失败。本轮未重跑该场，也未读取或假定其原Native tool args；下列条件性缺口不能冒称已经证明该历史失败的唯一原因。

## 现有正确路径

`study_avatar_tools.py:823–840`识别明确当前图请求时，丢弃模型传入的旧text；841–864保留当前已提交图片、full材料身份，缺图片时诚实 visual_context_missing。语言锁前快照固定，队列后不重新认领新课/新图；`entry_tutor_explain_entries.py:199–206,303–331,453–499`继承入口/context/model/finalizer/narration前材料保护。成功后Native再绑定该请求context。换图/换课guard属于此前已验证路径，不从头重做。

明确图片追问且text空，每次 entry 都调用 concept_explain。直接使用的基础 `tutor_llm_agent_concept_explain.py:240–262`将当前图片附到本次user消息，再调 `_call_model_result`；所读路径未发现复用旧老师回答而跳过此次模型的结果缓存分支。没有核查provider内部缓存，不能声称整条供应商链无缓存。重新发相同图不是重新捕获或局部放大。

## 两个具体条件性缺口

**P2：省略“当前图”指称的纠正可能被旧model text带入纯文本线路。** `study_avatar_tools.py:823–838`以question里的图片/当前指称决定丢text；问题“你读错了，不是天气命中，是天气未命中，请重新检查”本身未命中该判定。如果Native同时传入先前解释text，852/857采用course/session subset、863不附图；`entry_tutor_explain_entries.py:306–309`会明确关闭saved vision。原body仍包含学习者纠正，但模型无法查像素，可能只在两个文本说法间选择。相同裸追问如果text为空，仍附当前图片，因此不是所有裸追问都失效。

最小修复点是wrapper的材料来源选择与绑定，不是加泛化提示词或将所有“纠正”强行附上任意保存图。可复用已有明确图输出绑定/当前材料身份，提供可审查的 current-material/recheck 来源选择，固定请求图片再进既有guard；明确literal代码/笔记继续独立，无法确定纠正对象时诚实追问对象。首轮需实际wrapper负例覆盖旧text、literal源码、无图、材料替换；是否由角色可靠选择这个来源仍需后续真实场证明。本报告不擅写该功能。

**P2：被丢弃旧text中的语言仍能影响本次图片纠正。** `study_avatar_tools.py:822`先调用 `_turn_language_request(question,text)`，随后838才丢掉旧text。明确当前图片纠正、question无语言要求、旧text为 `Old response: Teach this in English.` 时，本次最终image正确/text已空，requested仍en-US，覆盖当前课程语言；schema显式language本就最高优先，不是问题。

最小修是完成来源解析/丢旧text后，再解析非schema的本轮语言；保留schema语言最高优先和课程默认，不持久化本轮要求。无需改长期偏好或重置对话。这项获Main授权后可单独窄修，裸纠正材料来源仍保留待办。

只读离线内存probe使用原AST中语言/来源赋值及原image选择表达式，未启动完整wrapper/entry/模型，不验证真实PNG视觉：

| 实际表达式输入 | text保留 | image附带 | 语言 |
| --- | --- | --- | --- |
| 明确当前图片纠正＋旧文字 | 否 | 是 | 课程/default |
| 裸纠正＋旧文字 | 是 | 否 | 课程/default |
| 裸纠正＋空text | 否 | 是 | 课程/default |
| 明确当前图片纠正＋旧English指令 | 否 | 是 | en-US（泄漏） |

这是源码路由复现，不是新模型/设备事故。

## 密集字、历史文本和语言的剩余边界

UI `study_submit_image`保存接受的原PNG/JPEG；直接 `_normalize_submitted_image_payload`只校验/标准化data URL（最大10MB），不重新缩放。这条当前提交图路径不使用OCR pipeline的thumbnail/phash结果当新图，不能把默认768压缩套到已提交图或continuity10原始输入。

窗口OCR路径不同：`study_ocr_pipeline.py:537–589`将图最长边缩到配置llm_vision_max_image_px（未设置时768），JPEG质量72；594–613仅返回30秒内snapshot。lightweight路径还会先缩到1280长宽/压缩，phash阈值5只是内容变化检测。图像相同或少一个“未”不能靠phash认定语义相同；这些阈值不直接阻止已提交图片重新调用Study。所读纠正线路没有ROI/局部放大、逐字证据、或在纠正时重新抓指定窗口的专门动作；不能称它已提高密集否定字可靠性。

直接context helper优先state已提交图片，再用未过TTL的pipeline图；explicit图参数会覆盖fallback。`llm_prompts.build_concept_recent_context`仍把最近老师输出/本课之前输出以及last_ocr_text放入bounded recent_context，后者标签是last_captured_material。Native wrapper的captured_text只用于代码标识符消歧，不会把整段OCR替换为source_text；但context的旧文字仍可对模型形成偏向。没有逻辑权重证明文字必定盖过像素，也没有像素/OCR冲突校验。已有“纠正时重看证据、OCR有损”规则，不应靠再加相同泛prompt宣称已修细字。

后续必要补证应复用同张既有材料，围绕争议字串逐字核对，再解释条件；如果原图确实不足可使用绑定同image身份的受控局部图，或对已授权精确窗口重新capture，不能扩成任意屏幕抓取。原HTML/源码可作为另一路真实证据，但必须明确来源，不能冒称从PNG像素看到。图像detail目前基础 `_attach_vision_image`默认auto；若考虑high/ROI，应先核现有vision接口的实际支持和成本，不盲换provider或做无效重试。

明确单次language参数与当前question语言要求继承锁内cfg override/finally恢复，课程语言优先长期default；它们不会因正常history直接改持久偏好。上述旧text语言泄漏是独立的来源解析顺序问题，不代表图片教学已整体英文可靠。Main后续实际质量/设备/真人验收继续，Goal不因本报告或两局部问题结束。

## 审查后授权的窄修复

Main在本报告形成后单独授权修第二项语言泄漏；原wrapper/finalizer/SQLite负例先复现两个语言方向失败，随后仅移动语言提取到丢弃text后。新增2项＋原语言4项离线通过，详见 `daily-companion-picture-language-correction-2026-10-14.md`。这是SOURCE/OFFLINE，尚未部署/模型/device/human；第一裸纠正来源和密集字可靠性仍按上文待办，不能说continuity10已整体修复。
