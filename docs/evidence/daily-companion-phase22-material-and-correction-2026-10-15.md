# 阶段22：当前材料、同题更正与日常设置保留

2026-10-15。原Goal已核为active；完整contract未改变，SHA256 `fd518311c0b3fafbe038b2bbd83d8eb0de8986212bcb4b86fccab22464084c33`。本阶段没有模型请求、音频、捕获设备、回环或音量操作。文字子进程开启 `NEKO_TASK_SILENT=1`，Native八项捕获API保护installed、isRecording=false。原round账本字节不变：DeepSeek675/2000，Lanlan.app63/无固定累计上限，Lanlan.tech0/0。

## 交付与证据层

- **源码/离线、本地实际SDK**：`study_answer`私有四身份pin防止旧回答被新题采用；4项测试，独立4项通过。仅调用方可传私有pin，不在模型schema公开。实际SDK entry/kwargs/callback/serializer通过，不代表HTTP/Core voice owner或provider选工具。
- **源码/离线、实际SQLite**：错答或部分答对后，显式更正保留原question_id/题干/错误记录，以新attempt再评分。原kv state与course progress同事务，无新表；10项通过，包括返课重启、SQL失败回滚、并发、取消后commit排空。公开 `correction_of` 要求原双ID，Main与独立3项通过。普通answer兼容。retry已提交后被换课/取消时可以保留新pending attempt，需要status回读；不会宣称未提交。
- **源码/离线、真实浏览器DOM**：学习材料窗口默认跟随现有Study SQLite保存的当前课图片，按course/session/image/text更新身份；旧指示退役。无图或读取失败明确显示，不回落到Sky图。参考图及源码是学习者显式选择。8项SQLite用例通过；已有浏览器场景检查桌面和移动端。Main晚绑定与选中旧源码版本替换的2项独立通过。
- **实际原入口、本地宿主与浏览器**：运行原 `Start-Daily-Tutor.cmd`，原 `neko-daily-companion`，offline-egress、原round。Native文字入口、Study Ready/refresh、当前图片surface检查通过；shared web-inspector截图Main已查看，当前图片与原保存图片hash一致，页面无console/page错误、失败请求或横向溢出。原27 interaction、820 topic、QA0及全部既有学习表行hash/数量不变，原pending双ID/题干保留，课程/Study配置/偏好/protected kv保留。仅允许生命周期state变化。这里没有评分原真人题，也没有把QA0当wrong纠正证明。
- **日常provider设置**：第一次原入口检查发现退出后仅coreApi由free变deepseek，原场保持非PASS。按本次宿主精确pre-launch白名单receipt恢复这一个字段，其它配置不动。恢复初版正常退出通过，但独立审复现check→replace会覆盖并发编辑的P2，保留发现并修复。最终Windows deny-write/delete同一owned handle读、核、修改、flush/fsync；拒外部provider/坏文件/链接，保留其它字段及新store默认。7项Main及独立真实Windows临时文件测试通过。原入口最终场采用锁定版本，core配置对象完全一致、退出0、预算字节不变。

原入口最终私有报告 `benchmarks/raw/evidence/daily-phase22-provider-locked.json` SHA256 `252ed679303c143b313edaffa19d0aa8fd84ea9b0b9ed84031cb9f9a8f419546`；第一次失败、初版恢复场及console原件保留，不上传用户材料或数据。最后scene60427已terminal，task ports48911/48916/9234/55804无listener；临时测试进程另核退出，不按旧PID清理。

Main相关launcher11与text-entry9通过。独立窄审见answer-context-pin-review、answer-correction-attempt、native-answer-correction-review、current-material-surface、surface-integration-review、provider-restore-review同日文件。

## 尚未证明与继续方向

**Native零工具调用的自由口头评分缺陷尚未修复。** 本阶段交付正式评分入口与同题更正，不能把直接SDK调用当角色自动选择工具已过。下一步固定真实ASR owner及权威原pending身份，正式结果前抑制本轮自由评分，复用原entry；不可构造provider未发出的function_call_output，也不可取消新轮或借用退休owner。随后用固定输入连续验证wrong→更正→返课重启、材料替换、语言/停顿、源码引用及响应时延。完整A–F与最终集中真人验收仍保留；此阶段不构成整个Goal完成。

provider恢复只在自有host清理成功后执行；同句柄写入不是崩溃原子替换，崩溃/写入异常可能部分更新，不声明异常退出设置完全保留。真实模型更正、实际设备可听及真人体验均待验。本轮current-image截图是自动浏览器DOM，不声明用户已经看见。

六个空fixture目录的可选清理被自动审批拒绝（仅返回blocked by policy）；保留目录、不绕过、不构成全局阻塞。另一次配置检索误命中并回显私有密钥字段，已改为精确字段投影；密钥未写入本报告或发布清单，不能声称历史工具回显被删除。
