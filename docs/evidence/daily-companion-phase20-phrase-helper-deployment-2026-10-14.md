# 阶段20：phrase运行辅助模块部署修复

voice34的实际宿主日志反复出现 `No module named neko_phrase_input_transport`。两个helper在scripts存在，但实际launcher cwd不能import；以scripts作为路径的本地测试掩盖了缺失部署。保留原voice34 FAIL_NO_ASR_OR_REPLY，原raw exit0不是语音通过。

`neko_runtime_helpers.py`只部署manifest中的两个exact stdlib helper到已有两个项目host根。部署前核两源文件hash/AST、两目标路径和已有bytes；不覆盖未知文件，exclusive创建，对并发已存在只接受相同regular bytes。源/host resolve必须在项目内。启动前SourceGate核source及deployed指纹，再用实际Source Python、launcher cwd执行 `-E -B` 子进程import，核实际模块文件路径；不注入scripts路径、不import应用或设备。缺失/漂移/import失败在启动前拒绝。

Main此前9项temp/stdlib检查通过，独立最终审9项通过，当前两host的两helper指纹与canonical/manifest一致，无具体新P1/P2。复现：`python -B scripts/test_neko_runtime_helpers.py`。独立报告：docs/evidence/daily-companion-runtime-helper-review-2026-10-14.md。

这是源码/离线部署及实际cwd import证明。尚未修后在线phrase试验，没有新增provider ACK、声音或真人验收。普通真人场未开启实验phrase模式，不能替代该验收。预算原round bargein-autocheck-20261012，DS668/2000、app62/null、tech0/0；本阶段离线不花额度。禁止mic/capture/loopback，必要输出专用speaker约4%不调音量。

发布只包含经过审查的部署代码、测试、manifest和证据；不带raw、DB、history、测试录音、keys或本地policy。不merge主分支/forcepush。最终发布SHA和候选/实际SourceGate验证由发布完成记录补充。

2026-10-15恢复后的Main实际SourceGate和两个真实host cwd import再次PASS，执行仅标准库检查，没有app/device/provider启动。发布前Source venv的原测试负例bare import可能借到venv父host已部署模块，Root和候选首次9项各8PASS/1FAIL；保存这个测量失败范围。生产preflight已有exact `__file__`检查，未放宽。负例修成同一真实child的origin检查，Root9重新PASS，独立增量审闭合。候选9及最终发布状态在提交前核。
