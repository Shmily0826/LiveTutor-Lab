# 阶段五：Study 材料控制生产端

2026-10-14。承接冻结的material-audio-cancel接口审查，只改四个产品文件与新检查/本报告。没有启动host、音频、外部请求、进程或其他Agent，没有操作账本、manifest、用户学习数据或Sky Scout。

## 已交付接口

成功且非degraded的Native `study_explain` 在材料仍current时返回：

```text
_study_material_binding = {v:1, boot_id, change_seq, context:请求材料上下文}
```

binding在原 `_lock` 内生成；boot_id为每plugin实例不变的随机32位hex，sequence在接受真正身份变化时递增。完整图片上下文包含course_id/session_id/material_identity；显式不可变source text保留course/session子集，不伪称看过保存图片。临时target map只记录此实例成功输出的精确角色和binding，不写SQLite、学习历史或长期偏好。

target在native第一次await前从 `_ctx.lanlan_name` 或 `ctx._current_lanlan` 捕获。显式缺失/无效 `_ctx` 不改用另一个角色；精确target未知时仍可返回identity，但不注册target、不广播取消。

image/session/course setter在原状态锁内捕获完整before/after并生成：

```text
metadata.study_material_control =
  {v:1, boot_id, change_seq, before:完整context, after:完整context, reason}
```

锁外使用现有SDK `push_message`，固定非空 `[study-material-control:v1]` text、visibility=[]、ai_behavior=blind、精确target_lanlan；独立于communication开关、StudyEventBus和cooldown。SDK源码确认是authenticated local queue提交；不持state锁调用SDK，没有模型/网络工作占用该锁。source由真实SDK/plugin通道认证，host仍应验证 `plugin:study_companion`，不能信任模型自填metadata。

只有当前boot已经绑定过输出的target，其expected字段在after中不再匹配时才通知。图片变化不取消仍满足course/session的不可变source输出；course/session变化会通知它。没有target、invalid image、expected_course拒绝、存储失败及完全同内容提交不发送。图片先成功写既有Store，再更新live字段/生成控制，因此store拒绝不会把未接受图片变成live材料。

`_end_study_session_locked` 先生成非空session→空的独立事件；start再生成空→新session的独立序号。重启不会把end和start合并而漏掉旧输出。

初版只通知before与旧binding匹配的target，主线指出A→B提交丢失后B→C无法再通知仍在播A。已修为同boot旧bound target只要after不满足其expected就可发送新的sequence；before仍如实是B，after如实是C。不是广播或循环重试。host需按最新协议允许missed intermediate的纠正，且新C输出binding必须拒绝晚A/B控制。

## 提交状态与限制

UI图片成功返回及 `study_material` / `study_session` 的可用结果提供 `material_control_submission`；运行中保存最近提交状态。submitted只在SDK明确submitted=True且未拒绝时报告；submitted=False/ok=False为not_submitted；仅ok或空回执为submission_unknown；异常只记录error_type，不记录原图片/OCR/密钥。取消/超时可能已由SDK接手，因此诚实标unknown，不伪称未发送或已停止播放。

提交失败不会回滚已经接受的图片，也不删除原history；会日志提示材料已接受但取消提交未确认。相同材料再次提交不自动重试；后续真正材料变更可向仍bound旧输出的精确target发纠正事件。角色重新成功解释会覆盖该角色旧binding，迟到控制由host current owner/boot/sequence/context围栏判断。

这只交付生产端通知和结果绑定。没有证明host消费、旧buffer退役、实际声卡停止、连接重建或新材料语音恢复；这些由主线host generator/消费者实现与独立证据验收。窗口/OCR其他非本次setter路径、已排communication narration和CodeGraph受控surface切换不自动宣称全覆盖。

## 离线证据

```powershell
& benchmarks/raw/neko-product-host/.venv/Scripts/python.exe -I -B scripts/test_neko_material_control.py
```

**11/11通过，0.945秒**：真实native wrapper→真实entry/finalizer+fresh SQLite，实际session lifecycle，actual submit方法及local SDK push stub。覆盖精确target/boot/schema/marker/blind、state锁外提交、source子集、invalid/same/wrong course、end/start独立sequence、无target不广播、SDK拒绝/异常/unknown、accepted image/history保留、store拒绝不更新、取消时unknown、degraded/stale不绑定，以及丢失A→B后B→C仍定向纠正。最早新脚本 `-I` 未加入自身scripts路径导致import失败，随后修fixture；新增missed-change检查还发现fixture复用同一dict回执，改为每次独立返回。保留这些初始失败，不当作生产失败或原本通过。

四个产品源码AST parse通过，限定diff whitespace检查通过（Git提示原CRLF规范化，不改运行语义）。没有为延长运行重复旧音频/模型验收。原材料guard/finalizer保持；已有AST fixture需由主线绑定新增 material_context/material_changes/submit_material_changes imports。

## 文件与交接

- `study_materials.py`：运行时boot/sequence/target bindings、control记录、SDK提交和状态。
- `study_avatar_tools.py`：精确target捕获、仅成功/current输出binding、状态可读。
- `entry_tutor_explain_entries.py`：accepted image前后记录，先store后live更新，锁外提交。
- `__init__.py`：实例初始化及start/end/session/course setter通知。
- 新 `scripts/test_neko_material_control.py` 与本报告。

本阶段新外部调用0、额度调整0、创建宿主/音频进程0，未改manifest或部署。生产端文件完成后冻结；主线可接入host及必要在线验证，不将这11项写成设备取消通过。
