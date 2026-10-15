# P1：源码教学角色指导一致

将启动器末尾“具体源码行用 study_code file”改为：行含义、假设改动、追问调用 `study_explain(material_source=project_code)`，小范围 file 请求或省略请求重读本课程上一源码；`study_code` 只作查询。保留实际语句行号与纠错要求。

先加实际 guidance 的离线测试：原代码出现预期失败；修改后 2 项通过，同时验证旧版自有指导会升级、用户自写指导保持原样。测试通过 AST 读取启动器，未导入或启动宿主。

确认 `neko_voice_host_patch.py` 没有这段角色文字/hunk，不修改任何宿主、arbiter、打断、传输。原启动器已在 raw/evidence/codex-r2-p1-before 保存。SourceGate PASS；补丁 `--check` 两棵宿主的所有目标均为 patched。

开工独立进程基线 105 模块：98 通过，7 个历史失败输出保存于 raw/evidence/codex-r2-baseline-20261016。新增 P1 测试不在开工时的模块快照中，单独运行通过；完整最终回归将包含它。

本项只证明指导内容与升级行为，语音模型是否遵循由 P2/P3 新场验证；未进行可听性或真人验收。本项外呼新增 0。
