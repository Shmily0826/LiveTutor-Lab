# 本轮源码补丁说明

这些补丁来自 2026-10-08 本机 Study/awareness 验证，尚未提交或推送。真实结果、限制和回滚见 `docs/neko-handoff-2026-10-08-goal-wip.md`。

- `study.patch`：从**原始打包 Study 0.1.0** 的 source-deployment/UI 原始备份导出，包含设置和 runtime 指标、后台超时/降级、watcher 订阅、评分必要上下文保护、显式追问上下文、截图模式及 UI/i18n 修改。候选源码 checkout 没有该 marketplace 插件，不能假设直接对其套用成功。
- `host-loop.patch`：针对候选源码 `1d814cf32fba8c02b5727d2890710e4e7b8ece24` 的宿主进程生命周期循环修改。仅作为正式源码集成候选；没有编译进本机冻结后台。

本机实际后台为 Nuitka/Python 3.11 冻结 exe，SHA256 `BE32BD8555EFE6450F01191DB4FAB41D4C25B6C14C8C52C44B1F645086AF6288`。当前测试部署通过显式 Study 源码入口、两个 import 根和 `scripts/neko_lab_runtime_loop.py`/`neko_lab_runtime_plane.py` 完成。后者补启动冻结父进程缺失的消息平面和桥接组件；不在这两个 diff 中，应和 handoff、脚本一起 review。

补丁不包含原始安装包、凭据、用户数据库或截图；本机完整原始备份都在 ignored `benchmarks/raw/evidence/goal-backups/`。新机器应用前核对版本与上下文并执行 `git apply --check` 或等价检查，不把这些 diff 视为跨版本通用安装器。

**2026-10-09 更新**：本 patch 已重新生成（971 行），包含 10-09 第二轮对 `llm_prompts.py`（会话记忆注入、summarize 上下文投影）与 `entry_ocr_entries.py`（`active_window` 捕获模式）的改动。第二轮还改动了 `prompt_templates.py`、`entry_tutor_context_support.py`、`entry_tutor_explain_entries.py`、`entry_tutor_question_entries.py`——这四个文件不在本 patch 的文件清单里（10-08 那一轮未改动它们，本地无原始备份可比对），其增量 diff 见 `../neko-study-2026-10-09-round2/`。**两份 patch 合起来才是完整的当前工作树状态。**

本轮 Python 21 项（含新增 6 项）与两个前端逻辑脚本通过，实际 Study UI 和冷启动有指定样本通过；区域截图、真实 awareness 角色投递、真实语音仍未验收。切换回原冻结入口需后台重启，不可用初始整个数据库覆盖当前学习记录。
