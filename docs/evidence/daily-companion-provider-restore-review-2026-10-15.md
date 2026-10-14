# 阶段22 临时 Core provider 恢复独立审查

范围：`neko_tutor_start.CoreProviderOverride`、daily start / voice probe 的 capture 与正常清理后 restore 调用，以及 `test_neko_core_provider_restore.py`。只读生产源，唯一写本报告；没有应用/服务/API、浏览器、音频、mic/capture/loopback、用户 DB 或账本操作。之前六个空 fixture 目录不再尝试删除。

## 初版具体 P2：最后检查与替换之间丢失并发设置

初版 `neko_tutor_start.py:293` 用第二次 `_read()[0] == raw` 判断配置未变，然后 `:295` 单独 `os.replace(temporary, self.path)`。用户/配置写者若在第二次 read 返回后、replace 之前修改文件，检查仍通过，替换将覆盖其最新非 provider 字段。这不是通过增加第三次 read 就能消除的窗口。

已向 Main 即时报告。纯临时配置复现：初始 free/retained7，运行时 deepseek/retained8；patch `os.replace` 在实际 replace 前将同一临时文件写为 deepseek/retained9/late_edit=true，然后执行真实 replace。结果 `provider_restored=true`，但 `late_edit_retained=false`、`retained_is_latest=false`。只用 synthetic temp 文件，没有用户配置/服务。

独立执行初版 `python -B scripts/test_neko_core_provider_restore.py`：5 PASS（0.037s），说明既有 normal switches、缺字段、新 store、foreign/malformed、第二次 read 前改变和 unchanged byte cases 成立；不能覆盖本次最后 read 之后的竞态。上述复现及测试均在 Main 要求停止旧版测试的消息到达前完成，此后不再执行旧版。

## 已确认的调用与保留范围

daily start 在 launcher 启动前保存旧字段；正常 finally 清理无 errors 且 launcher.poll 非空后才 restore。voice probe 同样在 host Popen 前 capture，正常关闭之后检查 cleanup_errors 与 process.poll，再 restore。路径/JSON/foreign provider 失败记录 cleanup error，没有重置整个配置；已有其它设置取最后 read snapshot；原本没有字段则移除临时字段，新 store 保留初始 defaults；provider 已与原值相同则不 rewrite。初版检查仅部分竞态成立，因此不能把“race 拒绝”作为无条件保证。

Main 已接受 P2，计划采用 Windows 拒绝 write/delete 分享的同一 owned handle 读取/比较/更新/flush，核 final path/reparse/hardlink。新版尚待独立窄审，不能借正在运行的 scene2116 追认该修复。正常退出恢复与进程崩溃/写入失败边界须区分；本场不声称 crash 自动恢复、durability 或物理设备验收通过。保留初版发现，后续若修复则追加关闭。

## 新版复核关闭（保留以上初版发现）

Main 后续源码已经移除 check→replace。`_locked_config` 在 Windows 使用 `CreateFileW` 的 GENERIC_READ|GENERIC_WRITE、FILE_SHARE_READ only、OPEN_EXISTING、FILE_FLAG_OPEN_REPARSE_POINT；同时要求 actual final handle path 对应原配置路径，并拒 st_nlink!=1 或 reparse 属性。MSVCRT fd 接管同一 handle 后，从该 handle 重新读 JSON、判断 provider/current fields、仅更新 provider 字段，然后同 handle seek/write/truncate/flush/fsync，直到 with 退出才关闭。前置 `_read` 不再作为实际写入快照；创建 handle 后的读取才参与恢复，因此不存在初版最后检查→rename 覆写窗口。foreign/malformed 在写入前拒绝，existing writer 冲突 failclosed，不重试或放宽分享。fd 接管前后异常均有对应 finally 关闭路径。

两处调用保持 host 启动前 capture、成功 cleanup 且 launcher 已停止后 restore；失败计入 cleanup_errors。newstore 默认不 restore，unchanged 配置不改 bytes，已有非 provider 修改来自锁内最新 JSON，原字段缺失则只移除临时字段。没有借恢复步骤启动 provider 或改账本。

独立再次执行 `python -B scripts/test_neko_core_provider_restore.py`：新版 7 PASS（0.050s），是真实 Windows temp 文件/句柄行为。覆盖已有读写句柄使恢复拒绝且 bytes 不变；flush/fsync 阶段另行 write 和 replace 均 PermissionError、handle 关闭后用户写入可用；hardlink 拒绝、双向 switch 保留其它修改、旧字段缺失/新store、foreign/malformed、unchanged bytes。当前限定范围没有发现新具体 P1/P2，初版并发覆盖 P2 CLOSED / SOURCE+OFFLINE。

限制仍明确：此 Windows in-place 更新不是 crash-atomic 文件替换；进程崩溃、断电或写/flush/fsync 中异常可能留下部分配置，不能声称自动恢复、全事务原子性或错误路径无损。已允许 FILE_SHARE_READ，另一个读取者也不由此获得读写事务隔离保证。非 Windows 拒绝恢复。Main 原入口 scene60427 的真实结果另行归 Main；本审没有运行 launcher/服务/浏览器/设备，不借旧场或 pending 场作为本分支 runtime/human PASS。本报告最终冻结。
