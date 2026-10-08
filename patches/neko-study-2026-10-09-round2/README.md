# 2026-10-09 第二轮：教学上下文复用修复补丁

本目录是本轮（教学连续性 / 上下文复用修复）的源码交付物。尚未 commit、尚未 push。

## 文件

| 文件 | 内容 |
|---|---|
| `round2-teaching-context.patch` | 本轮 5 个文件的精确 diff（+280 / −12 行） |
| `_pre/<name>.py` | 每个文件本轮改动**之前**的镜像，供 review 与离线复算 |

## 覆盖的文件（均在 `plugin/plugins/study_companion/`）

1. `llm_prompts.py` — 会话记忆块构造、summarize 上下文投影、允许字段
2. `prompt_templates.py` — concept_explain 系统提示与 user 模板、出题/总结 requirements、summarize token 预算
3. `entry_tutor_context_support.py` — 材料接地标记、KG 检索 query 优先级、会话边界、诊断字段透出
4. `entry_tutor_explain_entries.py` — 讲解载荷的 `mode`/`active_mode`/`recent_context_chars`
5. `entry_tutor_question_entries.py` — 自适应出题的目标标签可观测性

## 与 `../neko-study-2026-10-08/study.patch` 的关系

`study.patch` 由 `scripts/neko_lab_prepare_patches.py` 生成，其文件清单覆盖 10-08 那一轮改动过的文件
（`__init__.py`、`entry_status_entries.py`、`entry_neko_commands.py`、`entry_ocr_entries.py`、`llm_prompts.py`、
`static/*`、`i18n/*`），且是对**原始打包版**的 diff。本轮已重新生成它，因此其中包含本轮的：
- `llm_prompts.py`（会话记忆块 / summarize 投影 / 允许字段）
- `entry_ocr_entries.py`（`active_window` 捕获模式、`_foreground_window_target`、路由与诊断字段）

本目录覆盖本轮改动的另外 5 个文件。这 5 个文件**从未**被 10-08 那一轮改动过，仓库里也不存在它们的原始备份，
因此无法对原始打包版做逐字节 diff。本目录用「反演本轮编辑」的方式重建改动前镜像（`_pre/`），再产出 diff——
这份 patch 是**本轮增量 diff**，不是对完整原始包的 diff。

**两份 patch 合起来才是当前工作树的完整状态。**

## 复算方法（离线，不触碰打包运行时）

```bash
TMP=$(mktemp -d); mkdir -p $TMP/plugin/plugins/study_companion
cp _pre/*.py $TMP/plugin/plugins/study_companion/
python -m py_compile $TMP/plugin/plugins/study_companion/*.py     # 改动前镜像语法有效
( cd $TMP && patch -p1 < round2-teaching-context.patch )          # 正向应用
diff -r $TMP/plugin/plugins/study_companion <部署目录>            # 应与 LIVE 部署逐字节一致
```

已验证：`_pre/` 5 个文件 `py_compile` 通过；`patch -p1` 正向应用成功；应用结果与 LIVE 部署 **5/5 逐字节一致**。

本目录不包含凭据、截图、用户数据库或打包产物。`_pre/` 只是源码镜像，可安全 review。

## 部署状态

LIVE（`benchmarks/raw/neko-app/resources/bin/plugin/plugins/study_companion/`）、
BRIDGE（`.../bin/plugins/study_companion/`）、回归测试源（`benchmarks/raw/goal-isolated/study_companion/`）
三个根的这 5 个文件在本轮结束后逐字节一致（脚本校验，全 OK）。

运行中的插件是通过插件服务的 `/plugin/study_companion/reload` 重载的——该入口只在此次实验中使用，
不属于常规部署流程。
