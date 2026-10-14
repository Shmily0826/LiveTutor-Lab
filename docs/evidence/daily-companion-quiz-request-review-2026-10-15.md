# 出题单轮request透传：窄审

2026-10-15。范围仅canonical study_avatar_tools.py新增request及其三条出题branch、entry_tutor_question_entries.py的targeted source prepend、prompt_templates.py题型/范围规则、新test_neko_quiz_request.py及所复用fixture。只新增本报告，未改源码/shared records/manifest/账本。使用ponytail最小修复原则；没有应用、SDK服务、provider、麦克风、捕获、回环或音频设备操作，没有读取原用户库。

## 结论

三条主要路线透传闭合，新三项实际wrapper→entry→prompt/临时SQLite检查独立PASS；未发现新答案字段公开、长期偏好写入或选定主题身份变化。**有一项SOURCE P2空材料缺口需要收口**：纯题型/篇幅request在无材料且target_weak=False时被当成非空source，绕过原MISSING_TEXT。此新分支不在三项测试中，不能由其PASS外推。

目前只有源码/离线证明，没有新模型、部署、Native设备或human题型遵循验收。上一轮真人出题范围未遵循的失败仍保留。

## P2：request包装让无材料输入绕过缺材料拒绝

caller canonical `study_avatar_tools.py:1043–1066`。参数：topic=''、target_weak=False、request='Only direction, two options.'；当前无保存图片且last_ocr_text=''。

1. picture_quiz为false，snapshot包含当前course/session及空材料。
2. `requested_text`在request非空时返回`[Learner question request]... [Study material]`标签和指令，即使source本身为空（1055–1057）。
3. 第二branch把该字符串交给study_generate_question（1061–1064）。entry `882,893–905`以source_text是否为空决定OCR fallback/MISSING_TEXT；包装字符串非空，所以不再拒绝，可进入question_generate及持久出题。

这会允许仅“方向/两个选项”等格式要求被当学习材料，既没有图也没有题干，却调用模型生成并可能持有新题。旧同参数request为空时text为空，entry会拒MISSING_TEXT。vision关闭、只有saved图片且OCR空时亦相同：此branch没有传pixels，实际可用source仍空。

这是源码条件可直接复现的回归路径，本报告未追加测试/请求模型，不声明已有真实幻觉事故。最小修法：在这个无topic、非targeted branch区分真实snapshot source和单轮request；真实source为空且不会传图片时沿原entry的MISSING_TEXT拒绝，而不是让request标签充source。不能改为随意弱项出题或保留旧题但说已出新题。若request本身可描述完整新材料，应另明确其入口语义；本轮schema定义的是题型/范围/长度要求，不足以自动判它拥有材料证据。

建议仅补两个定向负例：无图片/OCR纯格式request不await模型、不替题、不append；vision关闭且saved图片有值/OCR空也拒绝。无需重跑已通过的全部旧quiz。

## 三路线与继承边界

| 路线 | caller/透传 | 审查结果 |
| --- | --- | --- |
| 当前Study图片 | 1049–1060：空topic且vision开启、有当前image；request前置，snapshot OCR在Study material段，原image和full _material_context下传。 | 没有从request重建image/hash。entry原begin/build/model/finalizer材料guard继承；最终wrapper还核qid/attempt及current材料后绑定。 |
| 显式topic | 1061–1064：request前置到原topic语言/篇幅directive，topic仍独立参数；snapshot为course/session subset。 | 不借保存图充不同主题；request没有改topic ID或概念命名。 |
| 自适应弱项 | 1065–1066：request单独传study_generate_targeted_question；entry779增加默认空request，825–826前置于已选topic/reason/guidance。 | 原选择context/scope revision检查、no_data拒绝、生成guard和topic身份沿用。请求未写长期偏好。 |

无topic且target_weak=False的额外OCR路线在1051捕获full材料context，避免先获取OCR再丢identity；request为空的原行为保留。上面的P2仅涉及真实source为空，不能借补丁说明把它当已过路线。

targeted entry外层decorator参数schema未新增request；Native public工具request由Python内部调用传给targeted，因此本次Native路线不依赖SDK public targeted schema接收新字段。不得把这个内部透传证明扩大成新SDK公开targeted API已验。

## 题型、答案和偏好

prompt_templates.py `135–139`现在要求遵守本题格式/范围/选项数/长度，方向题不能附带节点列表或整条路径；指令只适用于当前题。`147–152`保持multiple_choice题干中全部标签选项，A/B/C/D仅是四选项请求的例子，未硬编码所有题为四项；answer/reference_answer/accepted_answers仍是私有正确答案字段。

公开wrapper返回question/hint/topic/qid/attempt，没有新增answer字段；原entry把答案/rubric存私有held payload的边界未被request绕过。三项测试中故意返回等于答案的hint，原sanitizer仍输出空hint。这个离线结果不能证明真实模型不会把答案直接写进question；新prompt有禁止，但stem语义是否泄答案仍待真实模型遵循证据。

request只strip并组合本轮文本，不调用update_preferences、set_language或修改课程偏好；可以作为原question_generate interaction输入保存，**保存一次请求记录不等于长期偏好**。后续若模型把旧request当永久约束，需要独立具体证据，不能仅因DB有输入记录称已泄漏。现有summary角色投影省去question_generate input的行为不由本次补丁改变。

## 本Agent离线检查及限制

执行：

```powershell
& benchmarks/raw/neko-product-host/.venv/Scripts/python.exe -X utf8 -B scripts/test_neko_quiz_request.py
```

3 tests、0.480秒、exit0：当前图片request进入真实prompt且identity正确/偏好不变/public无reference_answer；topic与targeted两个subcase保持主题且无保存图；旧图片snapshot拒绝且不调用模型/不append。没有重复旧quiz guards12或memory8，Main其先前结果独立继承，不当本Agent新执行。

fixture实际抽取wrapper和entry，使用现有Store及临时SQLite；model是本地AsyncMock，targeted selection是fixture给定的selected topic，图片验证是原fixture stub。它不证明provider题型遵循、合法PNG验证、真实CodeGraph/弱项选择策略。stale-picture测试初始held为空，证明无新增/无替代当前空题，不能仅靠这个新方法名称声称有真实pending题被保留；原guard已有证据需按其原范围继承。

本轮未发现P1。P2收口前建议不要把“所有request分支保材料证据”作为发布结论；主要三branch与临时偏好/隐藏答案边界已有指定SOURCE/OFFLINE证明。唯一新文件本报告，完成后冻结。

## 同轮收口复审：空材料P2已修

Main新增canonical wrapper `1055–1056`，在request非空、topic空、target_weak=False、非picture路线且snapshot.text为空时直接返回ok=false/code=MISSING_TEXT，发生在request包装和question entry/model调用之前。不影响有像素的picture branch、有topic或已有targeted选择；request为空仍沿原entry缺材料行为。因此上面识别的纯格式request冒充source路径已闭合，旧发现保留其当时事实。

新第四测试`test_format_request_cannot_replace_missing_source_material`覆盖vision关闭且无图、vision关闭但保存图/OCR空两种subcase，真实wrapper必须MISSING_TEXT、模型未await、held为空且无interaction新增；没有放宽原三项断言。Main报告当前4 tests PASS；本Agent只读确认第四测试及源码，没有再次执行四项，也不把Main结果冒称独立运行。独立运行的先前三项0.480秒证明仍按原范围保留。

最新读到avatar SHA256 `b43ae7e28d5ccf533652b364438a16cbe4ba5e08e34fae5ba0923822f63ca2f1`、新test SHA256 `f888cfa282324ffd0a5b5dd2f28a0e8bc526a430300eb4851bb2e50ca34be924`。本项未见残余具体P1/P2阻断；模型遵守题型/长度和题干不泄正确答案依然待真实验证，未部署/设备/human外推。本报告再次冻结。
