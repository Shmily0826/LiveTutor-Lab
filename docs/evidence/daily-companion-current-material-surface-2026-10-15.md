# 阶段22：当前 Study 图片的受控可见入口

状态：SOURCE / OFFLINE / 合成 SQLite + 真实浏览器 DOM 通过。尚未由主启动器接入真实任务 store；不声称真实模型、设备声音或真人可见性验收通过。仅完成 A/E/F 的这个局部增量，整个 Goal 继续。

## 交付与接口

修改仅 `scripts/neko_learning_surface.py`、`scripts/neko_learning_surface.html`，新增 `scripts/test_neko_learning_surface_store.py` 和本报告。没有改 host、launcher、产品后台、manifest、共享四记录或账本。先读完整 contract、plan、status、blockers；应用 impeccable 窄范围完善流程，保留现有视觉、HTML/图片指示与滚动缩放机制。没有新素材、第三方依赖或新的数据库系统。

可选构造：`LearningSurface(materials, port, store=existing_task_store)`；旧两个参数调用保持可用。CLI 增加 `--store`。路径必须是项目 `benchmarks/raw` 内已经存在的任务目录，其中存在 `N.E.K.O/plugins/study_companion/data/study_companion.db`；解析后的 raw/store/DB 都检查包含关系，缺失或外部路径拒绝。主线可传当前 launcher 的 task store，或单独启动：

```powershell
python scripts/neko_learning_surface.py --store D:/CODE/project/LiveTutor-Lab/benchmarks/raw/<existing-task-store> --port 48918
```

这里的占位目录不得创建成空库。API 仍使用既有 loopback Host 围栏及 `X-Learning-Surface-Token`；token 由当前 surface 的根页面 bootstrap 提供，不在报告打印。端口勿占用主宿主 48911/48916。

启用 store 时默认“跟随当前 Study 图片”。读不到当前图片时进入明确空态/恢复提示，绝不回退默认 Sky 图。材料菜单中的静态材料标记“参考”，需学习者主动选择；参考模式标出 Study 当前课程，随后可选“跟随当前 Study 图片”返回。换课、替图、session 或材料文本身份变化，退休旧动态 material ID，清除旧指示。显式参考模式保留学习者选择，但材料上下文变化仍清指示。

`GET /api/state` 增加 `study`：`status` 为 `ready / empty / unavailable`，还有 `following`、`message`；有已保存合法课程时包含 `course_id/session_id`，有图时包含 `material_id/image_sha256/material_identity`。对应 `materials` 条目的 `source=study_store_snapshot`、`kind=image`，带相同 course/session/material identity。没有 image base64、OCR text、数据库路径或学习历史。

```json
{"material_id":"@study"}
```

以上作为 `POST /api/select` 恢复跟随模式。角色指示仍复用 `POST /api/guidance` 的当前 material ID 与 `{kind:"rect",x,y,width,height,label}`；坐标范围校验、由学习者切换材料的限制保持。state/select/guide/material GET 都先重读课程快照；旧 ID 指示拒绝，旧材料 URL 退休。前端已有 750ms 轮询，新增 revision 单调检查，较早网络回复不得覆盖较新的材料。图片点击只在加载完成后允许指示。

## 数据和权限边界

没有实例化 StudyStore（其构造可迁移/写库）。标准库 sqlite 使用 `mode=ro`、`query_only=ON`、显式 `BEGIN`，连接明确 close；没有 journal_mode 修改、CREATE、UPDATE、DELETE 或 DB 复制。不用 `immutable=1`，因此读取 active WAL 的已提交内容。

一个事务仅投影 kv/state 中 `study_course_id/study_session_id`，再读取该课程 `submitted_image:<sha256(course)>` 的 `course_id/image/text`；不查询 interactions、QA、topics、summary/history，也不拉取整个 state.value。图片记录 course 必须匹配当前课，读取字段有大小限制。仅支持现有 PNG/JPEG base64（原始 base64 或精确 data URI），严格 base64 及 MIME/字节头一致性检查；其它格式诚实提示不可读，不请求外部 URL。material identity 沿用 Study 的 `sha256(stored_image + "\0" + text)`，但不向页面提供 text。图像字节只暂存 surface 内存。

这是“已落库课程材料快照”，不是插件内存/boot 的权威握手。进程仍未持久化的课程变化，surface 不能先知；上限主要由后台持久化完成与 750ms 轮询决定，SQLite 锁等待 250ms 有界。不会把本地 material ID 当 Native provider、tool owner、取消回执或 utterance ID。主线角色 final admission、Native 看图/取消和主启动器选择同一 task store 仍须独立接入/验证。

## 证据

1. `python -B scripts/test_neko_learning_surface_store.py StudySurfaceTests`：最终 6 PASS（0.196s）。覆盖当前 A 图片不是静态 Sky、SQL 私有历史不读/不公开、DB bytes 未变；替图/换课/换 session/返回 A 的身份及指示退休；无图/坏图/读失败及恢复；显式参考与 reload 跟随；WAL + 未提交 dirty state 保持已提交快照且 DB/WAL bytes 未变；外部/缺失 store 拒绝与 no-store 模式保留。
2. `NEKO_SURFACE_STORE_BROWSER_CHECK=1 python -B scripts/test_neko_learning_surface_store.py`：7 tests PASS（包含上述 6 和真实 DOM）；global web inspector 桌面 1440×900、移动 390×844 各 13 PASS。初始 A、点击指示、同课换图、B 无图、坏图恢复、B 图片、返 A、迟到旧状态不能恢复旧图、参考必须显式选择、返回跟随、reload、当前图重新指示。各自 pageErrors/consoleErrors/failedRequests 为空，无横向溢出。复用原三 PNG，前后 SHA256 不变。没有重跑历史 E 几何批次。
3. `python -B scripts/test_neko_learning_surface.py LearningSurfaceTests PointingMetadataTest`：5 PASS，因修改共同服务类而回归原 no-store / HTTP / bounds / locator 分支；旧测试 HTTPError 对象关闭有 ResourceWarning，未改该冻结文件。
4. 真实浏览器结果 `benchmarks/raw/evidence/daily-phase22-surface-browser.json`；最终截图由 shared inspector 创建：`C:/Users/Shmily/AppData/Local/Temp/web-inspector-3MR8kr/desktop.png`、`C:/Users/Shmily/AppData/Local/Temp/web-inspector-j9RANI/mobile.png`。已观察同布局的首轮桌面/移动截图；第二轮仅增量加入坏图和晚状态负例，页面实现未改变。截图是受控页面，不是 Native 或用户桌面捕获。
5. impeccable detector 一次运行提示变量文字色被解析为白底低对比，以及 img 初始无 src。实际父 surface 深色背景/继承字色、图片仅 ready 时显示、空态隐藏 img，真实桌面/移动渲染已核；未把静态 detector 误报升级为产品改版理由。

最初 6 SQLite cases 的断言完成，但 teardown 因 `with sqlite3.connect(...)` 不自动 close 触发 WinError32，结果 ERROR，未隐藏。改为 `contextlib.closing` 后 6 通过，最终 fixture 正常删除。首轮留下六个空测试目录；各 DB 已逐文件删除。自动审批拒绝了批量目录删除，未绕过删除围栏，Main 已获通知。剩余空目录后缀：`2_sm6c4e / 27dcdt37 / 5nemb_s4 / 8whu4uky / mcgp45oj / v9w3b7tl`，均在 `benchmarks/raw/neko-surface-fixture-*`，不应发布。

临时 Surface 服务仅在测试进程内使用随机 64821/56607，两次已终态关闭，最终核无这两端口 listener；没有启动 N.E.K.O/Native/provider，未使用声音、麦克风、捕获或回环，未读用户 DB，未触碰账本。限额沿主记录，仅 Main 管理，本子任务外部请求为 0。

## 冻结与下一步

当前 SHA256：

- `neko_learning_surface.py`: `71ad53d005b117675fb53be1c7a7f1e25d137b1640e1ef174cfb0d72773593b9`
- `neko_learning_surface.html`: `1cffcd2d16330f0a5a1449d0540a284e5a0b71c91572c4ba5cbd276c73407a92`
- `test_neko_learning_surface_store.py`: `20044ecdb504ca7d863887eab8cc3f1cfafbfae0112fc0e4578d3eab2900b85d`

主线后续最小工作：启动器构造 surface 时显式传同一个 task store；开窗后核 state 中当前课程/图片 SHA 与实际 Study 提交一致；允许学习者明确切参考再返回跟随；把图片工具指示绑定当前 source/material_identity，不能把已落库快照替代 live tool admission。再做真实任务课程换图/换课可见验证与一次集中真人体验。本报告冻结；A/E 完整交付、模型理解密集小字、任意桌面定位和真人看见仍不由本场认领。

补充冻结确认：自动审批原始错误摘录为 `rejected: blocked by policy`，未提供更具体理由；被拒动作为上述六个本任务 fixture 的批量目录删除（首次已核 raw 包含关系、PowerShell `Remove-Item -Recurse -Force`；数据库精确逐文件删除后，非递归空目录尝试亦被拒）。不再重试、不换壳绕围栏，空目录不挡主线集成、不发布。四次 shared inspector CLI 均已 returncode=0，两次测试 session 均 terminal；global inspector 的既有 finally 会 `context.close()`、`browser.close()`。最终限定查询未发现命令行含本次测试脚本、两随机 URL 或四截图 task 目录的 node/python/chrome/edge 进程，surface 两端口无 listener。该核验结合本次退出与关闭路径，不按旧 PID 猜测或结束任何其他进程。
