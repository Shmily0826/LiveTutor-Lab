# Native 解释的课程/图片上下文：限定只读审查

日期：2026-10-14。仅读取product `study_avatar_tools.py`、`entry_tutor_explain_entries.py` 及已有 `scripts/test_neko_image_course_guard.py`。未修改生产文件、账本或进程，没有host/音频/外部调用，没有新Agent，也未重跑旧检查。以下是源码条件性缺口，不是实际事故报告；现有受控场景课/图一致不能验证切换竞态。

## [P1] Native wrapper未接入现有课程/session guard

`study_avatar_tools.py:816-837` 在解释入口读取cached image用于“缺视觉材料”预检，然后等待解释语言锁。`_study_explain_for_turn:839-869` 重新从live state读取OCR构造directive，最终仅调用 `study_explain_text(text=body)`；没有传captured image或 `_material_context`。

`entry_tutor_explain_entries.py:191-197` 的 `material_is_current` 在缺context时直接True。于是native链不会执行已有guard的课程/session语义，`:303` build也不使用请求绑定session。若课程或session在native解释等待语言锁、构建context或模型请求期间改变，而Realtime的scope/连接没有同步退休该call，wrapper/entry自身不能拒绝旧解释返回。已有old-session live-progress guard可以保护某部分新session状态，但不能代替这个解释请求的材料身份，更不能证明native结果未送回角色。

UI图片入口已做正确基础：`:142-164` 接受图片时锁内捕获course/session，传明确vision_image和private context；解释在entry开始、context构建后、模型返回后、finalize前及最终return检查。Native可以复用这些位置，无需另建guard系统。

## [P1] 现有context没有同课图片身份

UI提交的context目前只有course_id/session_id（`:152-153`）；current检查也只比较这两项。图片A模型运行中，学习者在同课同session提交B，最新state image/OCR会更新，但A的current检查仍为True。因此源码允许A旧结果进入 `_finalize_tutor_call`（`:443-462`）并最终返回（`:616-618`）。Native未传context的路径同样没有图片身份保护。

本审查能确认的是旧结果没有在这些检查处被拒绝、可到达history finalizer；没有在限定范围外检查实际DB事务实现，也没有用线上事故证明旧history已写入。已有image-course测试中的old-session record只拒绝session不同，不能覆盖相同session的图片替换。

## 最小修法与持久化边界

1. Native wrapper在排队等待解释语言锁之前捕获本次course/session与材料身份。已有活动session生命周期应先明确；捕获后不在锁获准时重认领新课。将image和OCR/source快照一起保存，避免“问题来自A、OCR或image已来自B”。
2. 沿用 `_material_context`，加入当前图片/OCR指纹或已有material revision。Native向entry传该context及captured `vision_image_base64`；UI submit也在现有锁内传同一身份。不要在trace/model参数中输出原base64，不重置学习历史。
3. Entry共用 `material_is_current` 同时比较course/session/material identity。保留build后的tutor_context course/session核对；显式vision snapshot使build不会悄悄改用新图。现有begin/build/model/finalize/return检查位置都可继承。
4. 如果验收要求“材料替换之后，不写旧结果history或live seed”，finalize前检查还不够：它释放锁后await持久化，图片可以在这段await里更换。应把expected identity传到实际写history/live seed的边界，在同一协调/事务时序中验证并提交；不跨网络模型请求长期持有plugin锁。最终return检查只能挡旧输出，不能撤销已持久化记录。已有旧课历史可以保留，不用删除或清空它来达成验收。
5. 发叙述事件同样位于异步finalize之后。材料已变时必须在事件发出前拒绝，不能先排播放再在最终return报stale。当前UI course check最终能拒绝返回，但需要单独覆盖finalize/event阶段的切换窗口。

hash只校验已提交图片时，同图但OCR/说明更新仍可能漏掉；若这些内容构成学习材料，应一起进入identity。原材料恢复/清除动作也要改变该identity，不能只在UI submit递增。

## 可继承的证据与新增最小检查

已有4项实际方法离线检查覆盖：submit预检后换课不保存；context构建期间course或session变更不调用模型；模型期间换课不finalize；旧session不污染新live progress。保留它们，不重做已通过真人/图片教学验收。

需新增的定向范围：真实native wrapper到真实entry传递context/image；解释语言锁排队时换课/换图不重绑定；相同course/session在build或model期间换图→拒绝且不finalize；finalize写history/event期间换图→不污染新材料并不播放旧结果；不变材料的正常解释仍返回。使用fake backend与现有SQLite即可先验证，无需在线费用。框架callback使用真实kwargs，避免旧测试stub只接 `text` 造成“wrapper增加context后测试误报”。

Realtime同scope exact-arguments singleflight可以减少重复调用，但它不包含material identity，也不封住UI同课换图或wrapper队列里的选课变化；不能把singleflight通过视为此竞态已修。

本限定审查完成。实施与上线由主Agent安排；本文件保留条件性缺口和实际事故之间的界限。

## 增量核对：Native guarded链与持久化保护已接入

后续仅只读核对4个生产文件：`study_materials.py`、`study_avatar_tools.py`、`entry_tutor_explain_entries.py`、`entry_tutor_context_support.py`，以及新 `test_neko_native_material_guard.py`。没有修改生产、执行线上或测试、操作账本/进程，也没有新Agent。

确认前述两个P1的主要保护已经接入：

- `study_materials.material_context` 复用course/session，增加image+OCR内容SHA256；只记录指纹而不把base64写到history metadata。`material_context_current` 共用当前身份核对。
- Native wrapper首次await前observe；ensure后锁内核对course/material并捕获image/OCR/context，排队等待语言锁后沿用这些快照，传给真实entry。Entry开始即检查，因此等待期间的课/图改变不会在language锁放行时重认领。显式source text仅绑course/session并明确关闭不相关saved-picture上下文。
- UI image提交也传同一material identity；entry保留begin/build/model/finalize/return检查，并在finalizer后、narration安排之前检查。
- Finalizer在已有 `_lock` 中校验identity并协调短SQL append，元数据保存原请求context。锁内没有模型/网络请求。record/live seed又检查身份；degraded旧错误也在更新last_error前拒绝。

主线报告新8项真实wrapper→entry/finalizer/现有SQLite检查通过；本审查读取其实现和断言，未重跑。覆盖正常identity持久化、language锁排队换图/OCR/课、ensure换课、同课build/model换图拒绝、明确source不带无关图、写history前stale不写、新材料不受旧degraded错误污染、SQL期间换图等待commit后不更新live seed/叙述/返回。原course4/language4/failure5/课程记忆6通过为主线证据。这些是**源码/离线通过**，没有新版模型、设备或真人材料替换验收。

## 剩余边界

1. SQL已提交的原请求history保留，不删除或回滚用户学习记录。新测试明确验证：commit先发生、材料再替换时，原identity history仍有1条，但新live seed/叙述和旧结果返回被挡。这与“新材料不被迟到结果覆盖”不同，不应表述为所有旧请求完全不留历史。
2. 原append cancellation helper在commit已经开始时最多等待5秒drain；超时会日志告警。异常慢SQL及取消交错的全部事务行为没有由这8项覆盖，不承诺已开始commit能任意撤销。不得为此跨模型/网络长期持state锁。
3. 保护native wrapper和UI submit下传context的路径；直接调用公开 `study_explain_text` 而不带private context仍沿用无context默认行为。不能把这次guard称为所有调用入口自动绑定原材料。
4. ensure后比较故意排除session_id以允许首次session初始化。若已经存在非空session，同课/同image的session重启恰好发生在observe→snapshot之间，源码仍可能采用新session；当前ensure测试只改course。应明确“允许空session初始化”与“已有session替换”的区别，若后者应拒绝，可仅对非空observed session追加核对。这里是较窄条件性范围，没有事故证据。
5. narration前检查不等于材料事件已关联所有播放取消：材料可以在event await、tool结果发送后或native音频已排队之后变化。当前内容身份没有驱动Realtime/provider音频owner或播放器cancel；最终return检查也不能撤销已排音频。旧native音频抑制须单独接材料事件并取得实际设备证据，不能由本离线guard冒称通过。
6. 内容identity允许完全相同image/OCR再次提交保持身份，它不是单调事件revision。当前保护正确内容；若以后要求每次替换事件即使内容相同也退休旧请求，需要另外明确该产品语义，不能擅自改成清空历史。

本增量审查完成，报告保留历史条件性发现及其修复证据。本子任务文件修改冻结，后续上线与必要真实验收由主Agent安排。

主线后续修正：ensure后仅允许observed空session初始化；observed非空session替换现在拒绝旧请求。新增真实session方法两种情形，9项Native材料守卫通过；上述剩余边界4已源码/离线解除，模型/设备边界未变。测试首次调用harness未暴露的end_session便利方法导致测试错误，改用已有end_session_locked后通过，未修改产品会话实现。
