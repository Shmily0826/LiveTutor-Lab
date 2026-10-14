# 原日常文字入口、学习数据保留与语音本地诊断

2026-10-14，阶段十九。完整契约及后续明确权限继续生效；现有 Goal ACTIVE。主 Agent 负责两次有界离线场、账本、源码修复与发布；既有两 Agent 独立审查各自窄范围，不启动线上服务。完整报告不替代 contract。

## 实际原入口的范围和结果

两场均实际执行原 `Start-Daily-Tutor.cmd --minutes 5 --offline-egress --cdp-port 9234`，使用原 `neko-daily-companion` store、原 `bargein-autocheck-20261012` round、`--text-only --study-ui --learning-surface --code-root keep` 默认参数。没有换新库、复制C33、造待答题、出题、讲解、评分或总结。正常启动部署代码并产生允许的session/checkpoint生命周期写入。不是全store字节只读，也不是全OS网络隔离。

第一次：actual Native Root文字flag=true、composer存在、isRecording=false、8 API capture guard installed；真实Study SDK public状态就绪，点击刷新后课程/session/public题状态相同，浏览器page_errors=[]。原选课、Study保存config、语言偏好和protected kv保持，21条interactions及其他原学习表逐row hash保持、无新增学习记录。**820条topics原行hash全部变化，数量仍820**，整项保留检查exit1，保留原FAIL/PARTIAL。启动时seed upsert无条件更新`updated_at`是源码可证行为；第一次只有行hash快照，不能证明实际只改了时间戳，不回写旧报告、不恢复/清空数据。

修复：新增canonical `store_topics.py` overlay，其base SHA256为 `0069f0cae4dea26b654415e5883744576877dbe3a9163414099428bbad9af2fd`。唯一实质差异为upsert的SQL WHERE：incoming seed的19个持久内容列（含source）完全相同则不UPDATE；SQLite `IS NOT`使比较NULL-safe。seed真实改变仍更新，非seed仍走原UPDATE与seed权限/空字段补充规则。未更改题目、掌握度、复习身份或另建数据库。四项实际方法/临时SQLite检查覆盖重复seed无写入、真实seed变更、非seed权限与补充、真实loader重复加载。独立SOURCE审查未发现阻断。

代码改变后第二次必要实跑：**PASS_ORIGINAL_DAILY_TEXT_ENTRY_AND_EXISTING_DATA_PRESERVATION**。真实Native相同文字保护/输入框，Study真实SDK Ready/public状态/手动刷新均通过，page_errors=[]。所有原非kv/sessions表逐row完整hash相同、行数量相同，包括820条topics；原21条interactions、QA/错题/复习/掌握度等均保持。原课程、Study config、语言偏好、protected既有kv以及宿主Core config完整JSON值相同，Core changed_keys=[]。唯一既有kv值变化是允许的state；session生命周期独立记录。原daily没有pending题，因此**本场不证明原pending恢复**，不把布尔条件的空对象通过当续题验收；继承C33独立同题返课/重启真实证据。

实际部署逐项核29个canonical文件：28个原字节hash匹配；index.html正常经捕获保护封装，实际字节与`protected_html(canonical index, pinned capture policy, text_only=True)`经真实Windows `write_text`换行转换的完整生成结果相同。manifest保留index原raw `deployed_matches=false`，另记protected比较及其SHA，避免假称raw HTML相同。数据目录未作为部署来源/目标复制。

两场正常按Enter结束，launcher_exit_code=0，最终`stopped=true, cleanup_errors=[]`；Main确认48911/48916/9234无listener。原round账本完整bytes保持：DS610/2000、app59/null、tech0/0。实际relay allowed=[]、direct=[]、denied仅community.project-neko.cn。没有外部模型场或模型语义验收，没有声音/扬声器播放、mic/设备初始化、fake input、WAV或回环；用户约4%扬声器许可保留，未调系统音量。Native窗口存在不是用户已看到/已体验证明；检查结束不留下持续运行的avatar。

## B本地观察推进及证据边界

`neko_native_delivery_diagnostics.py`默认OFF，固定阶段计数和8项bool/unknown状态投影，有限键空间/饱和计数/至少2秒日志间隔。不记录PCM、文字、路径、身份token或keys，不改变原调用次数、参数、返回、异常/取消。Main复核11项pure-class透明性测试通过。此helper尚未接入生产启动hook/host manifest，不冒称当前真实宿主已有计数。

新增4项实际方法离线检查：Core `_process_microphone_stream_data`、`_route_microphone_audio`、`_route_microphone_audio_unfiltered`取当前runtime AST，实际Omni/NativePhraseUplink/transport到本地QueueSocket。正向46帧到对应阶段、1次flush、本地audio.append及mic计数；required missing factory、noise contract mismatch、inactive after DSP三个真实分支继续阻止下游，不绕安全guard。配置依赖在import前指向临时目录，测试清理该目录，不读原用户配置/学习数据。

**边界：**DSP/RNNoise、preview、Core lifecycle/token/registry/queue等是明确seams/doubles；直接调用process，不证明整条前端→enqueue准入。required-missing真实enqueue也可能更早丢弃。QueueSocket local append不是provider ACK。诊断不证明voice34根因、不证明真实识别、语言、自然停顿、首段音频或设备播放；guard返回true只表示方法消费，并不必然是发送成功。不同实际阶段必须关联观察，不能凭一个return统计就猜原因。

## 发布、接续与未验收

阶段十九发布只纳入源码/manifest/测试与证据文档，提交SHA和检查结果由发布完成后的状态记录给出；不发布private snapshot/console/raw、用户DB/history、密钥/配置、录音或local policy。Root原脏树及.workbuddy保留，不merge/force。

下一步先接入受控默认OFF诊断并核SourceGate/精确replay，收窄实际DSP后的drop位置；voice34失败仍在，未因本地正向append恢复线上重试。再根据明确原因决定必要固定WAV/output-only扬声器场，不开mic、不换供应商。继续更宽graded跨课、多材料角色教学、源码/受控表面指示及集中10–20分钟体验；人工未验仍pending，整个Goal不能因阶段十九完成而complete。

私有证据：`daily-phase19-daily-entry.json`（第一次保留失败）、`daily-phase19-daily-entry-seed-fix.json`（修复后实际保留通过）、各console、`daily-phase19-deployment-check.json`、Study E2E `20261014T100600Z`/`20261014T101512Z`。这些仅在项目ignored raw目录，不作公开payload。独立审查见原daily-entry-review及fixed-input-scope-review追加；新失败证据不覆盖历史。
