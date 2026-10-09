# LiveTutor v0.2 产品适配

这份 overlay 继续使用已保存的 Study Companion 发布树，配合官方 pinned N.E.K.O 源码宿主。它不是完整插件发行包，也不声称所有发布树修改均来自官方。

- 宿主基线：`1d814cf32fba8c02b5727d2890710e4e7b8ece24`，位于本项目 `benchmarks/raw/neko-product-host`。
- 插件基线：`benchmarks/raw/neko-app/resources/bin/plugins/study_companion`，保留已有 overlay 的发布树；未复制其学习数据库。
- 产品代码：`payload/study_companion` 与 `static`；启动器每次按基线 → 本 overlay 部署到 `neko-product-data/plugin-code/study_companion`。
- 数据目录：`neko-product-data/N.E.K.O/plugins/study_companion/data`，不在代码部署目录中。
- `manifest.json` 保存本次 17 个产品源文件的 SHA-256，最终实际部署逐文件一致。音频宿主适配另存于相邻 `neko-study-2026-10-10-host`，启动前核对其指纹。

局部修复覆盖明确授权窗口读取、课程 ID 与同课历史、原生题目身份及评分、出题材料保留、Session 总结、跨重载调用预算、主题路由，以及追问的纠错/简短要求。没有另建聊天 UI、记忆数据库框架或音频编排。

从项目根目录双击 `Start-Tutor.cmd`。本机运行时及虚拟环境已安装在 ignored 的 `benchmarks/raw`；本提交保留源码与证据，不包含依赖、凭据、浏览器 profile 或学习数据库，单独克隆 Git 并不恢复这些本机运行文件。

验收与使用说明见 [明早交接](../../docs/neko-v02-morning-handoff-2026-10-10.md)，完整真实回复见 [Transcript](../../docs/evidence/flutter-product-transcript.md)。离线回归和真实 UI/模型证据分开记录；自动题目主题标签的概念归并仍有缺口，详见独立审查。
