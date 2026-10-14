# 阶段22 Surface 主线接入增量独立审查

结论：限定增量没有发现需要阻断发布的具体 P1/P2。两项新增实际方法/临时 SQLite 离线测试独立 PASS；没有启动应用、provider、浏览器或音频，没有读取用户 DB、改代码/manifest/共享记录/账本或清理之前六个空目录。

范围仅 `neko_learning_surface.py` 的 late binding 与 selected-old-code 替换、`neko_tutor_start.py` / `neko_daily_voice_probe.py` Ready 后 attach 调用、`test_neko_learning_surface_store.py` 两个新增 case。沿用本轮已读 contract/plan/status/blockers，当前实际 Goal active 以 Main 的 get_goal 为准，记录中的历史 paused 不覆盖本轮授权。之前完整 Surface 源码、合成 SQLite 和真实 DOM 证据见 `daily-companion-current-material-surface-2026-10-15.md`，本次不重复旧批次。

## 核对结果

- `neko_learning_surface.py:197` `attach_study_store` 先在 lock 外构造 `StudyPictureSnapshot(store)`，保留 existing/raw containment/file 门禁；路径不合法时不修改既有 reader。然后在既有 RLock 内设置 reader、follow=True、study=None 并调用 refresh。None 使同身份也重建动态条目；refresh 完成当前 image/empty/unavailable 状态、旧动态材料退休、command 清除与 revision 增加。读失败不回退静态 Sky。没有实例化写入型 StudyStore，没有新增 HTTP attach 权限入口。
- `neko_tutor_start.py:661` 在 `plugin_server_ready` 为真后 attach，并在 Native launch / task browser 打开前执行；此前 surface 仅建立本地服务，允许 fresh launch 尚未创建 DB。attach 的路径异常会穿过既有 finally 清理；readonly 内容失败则显示诚实 unavailable。这里 Ready 不等于课程已经有图片，empty 仍是正常状态。
- `neko_daily_voice_probe.py:207` 在隔离 host ready 后 attach 该 probe 的 `store_path`，在 optional 课程/图片提交及 Native launch 之前。随后提交图片由 surface 每次 state/guide/material GET 的只读刷新跟踪，未新增供应商连接、捕获或音量动作。未运行该量具；不把此调用位置当 voice/provider/设备证明。
- `neko_learning_surface.py:260` 新 CodeGraph 证据替换旧 `filtered_codegraph_evidence` 条目时，如果 active 恰为旧代码 ID，则 active 改为新代码 ID 并 clear command；如果当前显示 Study 图片或其它参考材料，则保持选择，仅添加可选择的新代码。旧代码 ID 从字典退休，后续 guide 与 URL lookup 不能复用。代码更换不会偷开 `follow_study`，学习者已选择代码时仍在参考模式；新证据 HTML 仍按原 escape/行范围生成，不写学习材料。

## 独立执行

```powershell
python -B scripts/test_neko_learning_surface_store.py StudySurfaceTests.test_replaced_selected_code_evidence_stays_on_new_code_version StudySurfaceTests.test_existing_store_attaches_after_fresh_launcher_database_creation
```

2 PASS，0.053s。第一项验证选择旧代码后换新证据，active 为新代码、旧条目退休、command=None、follow=False；第二项验证 no-store Surface 可在已有任务 DB 出现后 attach，并得到课程 A 的当前图片 SHA/active/follow=True。使用临时 synthetic SQLite 和既有 PNG，surface 只实例化端口0，不 serve；finally server_close 和 fixture cleanup 完成。该 case 名称中的“fresh launcher database creation”是合成已有 DB 场景，测试没有启动真实 launcher；新代码替换也没有在浏览器里重新做 DOM/真人验收。

Main 报告原真实入口已看到 current picture 并经 desktop inspector，但 coreApi 字段变化使整场仍非 PASS。本次未读该场完整 raw，也不追认整场或定位其 coreApi 根因。只读 persisted snapshot 的 live/boot authority 边界仍然存在，不能由 late binding 推出 Native 当前 owner/取消回执。原六个被拒批量清理的空目录保持原样，不再重试。此报告冻结供 Main 集成/发布判断。
