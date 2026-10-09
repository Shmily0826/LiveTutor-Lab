# 2026-10-09 第三轮：真实模型 UI 闭环 —— 教学模式横幅 + 总结语言修复补丁

本目录是「浏览器真实教学闭环」这一轮的插件源码改动（3 个文件，+8/−1 行）。尚未 commit、尚未 push。
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

## 文件

| 文件 | 内容 |
|---|---|
| `ui-real-tutor.patch` | 3 个文件的精确 diff |
| `_pre/prompt_templates.py` | 原始快照镜像（与 v02 overlay 的 `payload/bridge` 逐字节一致） |
| `_pre/llm_prompts.py` | 原始快照镜像（与 v02 overlay 的 `payload/bridge` 逐字节一致） |
| `_pre/tutor_llm_agent_concept_explain.py` | 改动**之前**的镜像，由反演本轮编辑重建（310 行） |

## 落地位置（两份都要一致）

隔离夹具加载 `benchmarks/raw/neko-app/resources/bin/plugins/study_companion/`，分发包内另有同名副本
`benchmarks/raw/neko-app/resources/bin/plugin/plugins/study_companion/`。本轮三个文件两处已同步为
逐字节相同。patch 里路径沿用仓库既有的 `a/plugin/plugins/study_companion/…` 写法；应用到别的部署前
请先核对目标指纹。

## 诚实边界

- `prompt_templates.py`、`llm_prompts.py` 在 `../neko-study-2026-10-09-v02-overlay/manifest.json`
  里有快照，本轮改动前的字节与快照一致（校验过），所以这两个文件的 diff 是对**原始打包版**的 diff。
- `tutor_llm_agent_concept_explain.py` 不在该快照清单里，仓库也没有它的原始备份，因此 `_pre/` 是
  「反演本轮编辑」得到的改动前镜像（与 `../neko-study-2026-10-09-round2/README.md` 同类限制）。

## 如何重建运行源码（已实测）

仓库里存的补丁与 pre-image 都是 LF，而本机 `core.autocrlf=true` 会让 `git apply` 把输出写成 CRLF。
已验证的逐字节重建方式（在临时目录里做，先别动真实源码）：

```bash
mkdir -p rebuild/plugin/plugins/study_companion
for f in llm_prompts.py prompt_templates.py tutor_llm_agent_concept_explain.py; do
  git show "HEAD:patches/neko-study-2026-10-09-ui/_pre/$f" > "rebuild/plugin/plugins/study_companion/$f"
done
git show HEAD:patches/neko-study-2026-10-09-ui/ui-real-tutor.patch > ../ui.patch
git -c core.autocrlf=false apply ../ui.patch     # 必须关掉 autocrlf，否则结果只差行尾
```

本轮已用这条路径核对：三个文件重建后与
`benchmarks/raw/neko-app/resources/bin/plugins/study_companion/` 里的运行版本**逐字节相同**。
不带 `-c core.autocrlf=false` 时内容一致、仅行尾变成 CRLF。应用前请先按 v02 overlay 的方式
逐个核对目标指纹，不要直接覆盖别人的在制改动。

## 验证

- `node scripts/neko_study_ocr_ui_e2e.mjs --real-model` → `PASS_UNIFIED_OCR_STUDY_UI_REAL_MODEL_LOOP`
  + `PASS_REOPENED_TEMP_SQLITE`
- `node scripts/neko_study_ocr_ui_e2e.mjs` → `PASS_UNIFIED_OCR_STUDY_UI_LOOP`（Mock 回归，改后仍过）
- `scripts/neko_study_plugin_methods_fixture.py` → `PASS_PLUGIN_METHOD_LOOP`；
  `scripts/test_neko_study_context_fixture.py` → 5/5 OK
