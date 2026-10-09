# 2026-10-09 第三轮：真实模型 UI 闭环 —— 教学模式横幅 + 总结语言 + 总结范围修复补丁

本目录是「浏览器真实教学闭环」及后续学习状态修复的插件源码改动（4 个文件）。尚未 commit、尚未 push。
验收与测量见 `../../docs/neko-real-tutor-ui-2026-10-09.md`。

## 改动一：重复的模式横幅

`concept_explain()` 原来只要当前模式是 teaching，就在**每一次**讲解回复前面硬拼一句
`教学模式已开启。`（`build_transition_phrase(..., outcome="changed")`）。连续三轮追问的页面上
就会出现三条相同横幅，这是上一轮真实模型实测里量到的体验缺陷。

改成：只有**本轮真的发生了模式切换**才加前缀。切换事实由调用方已有字段提供
（`entry_tutor_explain_entries.py` 组装 `extra_context["mode_switch"] = bool(mode_switch["changed"])`，
`entry_tutor_context_support.py` 再 `context.update(extra)` 透传给 agent），因此不需要新增状态、
缓存或架构。纯切换请求（`pure_switch`）仍然只回一句过渡语，行为不变。

实测：真实浏览器闭环三轮讲解 `ui_ux_checks.mode_banner_replies == 0`。

## 改动二：结构化操作没有输出语言指令

`summarize_session`（以及 question / evaluate / knowledge_track 共用的
`_build_structured_messages`）只把 `language` 当成 `context_json` 里的一个数据字段，没有下达
“用这个语言作答”的指令；而 `concept_explain` 的模板是有这条的。结果就是：讲解是中文，
会话总结却是整段英文。

改法：给结构化 prompt 增加一行
`STUDY_STRUCTURED_LANGUAGE_TEMPLATE = "Write every natural-language field in {language}.\n\n{prompt}"`，
仅在 context 带 language 时生效，不改 JSON 结构契约。

注意：语言不一致的**另一半原因不在插件代码里**，而是隔离夹具没有把插件自带配置交给生命周期 ——
补上 `ctx.get_own_config`（见 `scripts/neko_study_plugin_methods_fixture.py` 的 `_own_plugin_config`）
之后，`plugin.toml` 的 `[study] language = "zh-CN"` 才真正进入 `StudyConfig`。两处一起才修好。

实测：`explanations_have_cjk` / `summaries_have_cjk` / `evaluation_feedback_has_cjk` 全为 true，
刷新后的第二次总结也是中文（`## 本次学习总结 …`）。

## 改动三：Session Summary 丢掉本会话最早的互动（含已评分答案）

`entry_tutor_context_support.py` 的 summarize 分支不用 store 已经按 `session_id` 过滤好的结果，
另外用内存事件环 `recent_learning_events`（上限 64 条）里最早的 `at` 当会话边界。互动行是**先落库
再记事件**，所以第一行的 `created_at` 必然早于它自己那条事件的 `at`，于是最早那条互动**每次都被切掉**；
环转起来之后还会切掉更多。真实浏览器那轮两次总结都说"未记录具体作答"，就是这个方向的问题
（答案本身是否入 prompt 需要宿主侧 prompt 正文才能定性，见验收文档的遗留项）。

改法：会话内直接按行自带的 `session_id` 取；只有在拿不到 session id（历史确实跨会话）时，
才退回原来的事件环边界。不改 schema、不动记忆系统、不加新状态。

回归：`scripts/test_neko_study_summary_scope.py`（离线，零模型调用）跑 explain→追问→出题→作答→
构造 summarize 上下文，断言 `session_history` 条数 == 本会话互动条数、参考答案与首条讲解都在
summarize prompt 里，并且显式断言"最早那条行的 created_at 早于事件环边界"，这样旧逻辑一旦被重新
引入这条用例会失败。实测：修复后 1/1 通过，原有 5 条 focused 用例仍全过。

## 文件

| 文件 | 内容 |
|---|---|
| `ui-real-tutor.patch` | 4 个文件的精确 diff |
| `_pre/entry_tutor_context_support.py` | 原始快照镜像（与 v02 overlay `payload/bridge` 逐字节一致） |
| `_pre/prompt_templates.py` | 原始快照镜像（与 v02 overlay `payload/bridge` 逐字节一致） |
| `_pre/llm_prompts.py` | 原始快照镜像（与 v02 overlay `payload/bridge` 逐字节一致） |
| `_pre/tutor_llm_agent_concept_explain.py` | 改动**之前**的镜像，由反演本轮编辑重建（310 行） |


## 落地位置（两份都要一致）

隔离夹具加载 `benchmarks/raw/neko-app/resources/bin/plugins/study_companion/`，分发包内另有同名副本
`benchmarks/raw/neko-app/resources/bin/plugin/plugins/study_companion/`。本轮三个文件两处已同步为
逐字节相同。patch 里路径沿用仓库既有的 `a/plugin/plugins/study_companion/…` 写法；应用到别的部署前
请先核对目标指纹。

## 诚实边界

- `prompt_templates.py`、`llm_prompts.py`、`entry_tutor_context_support.py` 在
  `../neko-study-2026-10-09-v02-overlay/manifest.json` 里有快照，本轮改动前的字节与快照一致
  （校验过），所以这三个文件的 diff 是对**原始打包版**的 diff。
- `tutor_llm_agent_concept_explain.py` 不在该快照清单里，仓库也没有它的原始备份，因此它的 `_pre/` 是
  「反演本轮编辑」得到的改动前镜像（与 `../neko-study-2026-10-09-round2/README.md` 同类限制）。
- 本 README 顶部所述"4 个文件"包含上面三段改动。
- **最终复核更正**：原先写的「`round2-teaching-context.patch` 里 `entry_tutor_context_support.py`
  那份 diff 无法重建当前快照（差 64 行）」并不成立 —— 按 v02 快照 → `goal-context.patch` →
  本目录 `ui-real-tutor.patch` 的顺序可以逐字节重建运行源码。复核命令：
  `python -I -S -B scripts/neko_plugin_source_coverage_check.py` → `PASS_SOURCE_COVERAGE`。

## 如何重建运行源码（已实测）

仓库里存的补丁与 pre-image 都是 LF，而本机 `core.autocrlf=true` 会让 `git apply` 把输出写成 CRLF。
已验证的逐字节重建方式（在临时目录里做，先别动真实源码）：

```bash
mkdir -p rebuild/plugin/plugins/study_companion
for f in llm_prompts.py prompt_templates.py tutor_llm_agent_concept_explain.py entry_tutor_context_support.py; do
  git show "HEAD:patches/neko-study-2026-10-09-ui/_pre/$f" > "rebuild/plugin/plugins/study_companion/$f"
done
git show HEAD:patches/neko-study-2026-10-09-ui/ui-real-tutor.patch > ../ui.patch
git -c core.autocrlf=false apply ../ui.patch     # 必须关掉 autocrlf，否则结果只差行尾
```

本轮已用这条路径核对：三个文件重建后与
`benchmarks/raw/neko-app/resources/bin/plugins/study_companion/` 里的运行版本**逐字节相同**。
不带 `-c core.autocrlf=false` 时内容一致、仅行尾变成 CRLF。应用前请先按 v02 overlay 的方式
逐个核对目标指纹，不要直接覆盖别人的在制改动。

## 附带收：宿主平面模块（此前完全不在版本控制里）

`benchmarks/raw/neko-app/resources/bin/plugins/lab_study_plane.py` 与 `lab_study_runtime.py` 被 LIVE 入口
`lab_bootstrap_plane` import，属于运行路径的一部分，但既不在 v02 overlay 清单里、也没有任何补丁副本
——即"测试通过但关键代码没进 Git"。本轮按快照方式收进 `host_plane/`（未修改内容，逐字节一致）：

| 文件 | SHA-256（前 16） |
|---|---|
| `host_plane/lab_study_plane.py` | `876e00824894fbaa` |
| `host_plane/lab_study_runtime.py` | `d4768dbd2cf7818b` |

两者的定位与限制见 `../../docs/neko-desktop-tutor-2026-10-09.md`：它们是对冻结宿主的兼容性 hook
（补 message plane 与 asyncio runner），后续应改由源码构建侧的 `host-loop.patch` 承担。

## 验证

- `node scripts/neko_study_ocr_ui_e2e.mjs --real-model` → `PASS_UNIFIED_OCR_STUDY_UI_REAL_MODEL_LOOP`
  + `PASS_REOPENED_TEMP_SQLITE`
- `node scripts/neko_study_ocr_ui_e2e.mjs` → `PASS_UNIFIED_OCR_STUDY_UI_LOOP`（Mock 回归，改后仍过）
- `scripts/neko_study_plugin_methods_fixture.py` → `PASS_PLUGIN_METHOD_LOOP`；
  `scripts/test_neko_study_context_fixture.py` → 5/5 OK；
  `scripts/test_neko_study_summary_scope.py` → 1/1 OK（离线，无模型调用）
