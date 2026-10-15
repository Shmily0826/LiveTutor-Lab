# W1：尚未实测改动的真实验证

日期 2026-10-15。证据层级：真实文字模型（DeepSeek）+ output-only Native 固定 WAV。没有麦克风、采集设备、回环、真人；可听性待用户。账本 `bargein-autocheck-20261012`，W1 共用 DeepSeek +70（968→1038）、Lanlan.app +4（90→94），未重置、未提额。

## A. 文字 SDK 场：索引同步与文件清单缓存（`claude-w1-text-1`）

新量具 `scripts/neko_source_scene_probe.py`（场景是数据，W2 复用）。新建任务 store `neko-daily-code-contrast-20261015-w1`，只复制已授权的 Sky Scout 授权文件，并复制 m5 store 的 `code_sync_state.json`（模拟用户真实安装"早已同步过"；指纹仍与现有目录比对，目录变了就会同步）。DeepSeek 968→974，恰好 6 次。

| 轮 | 请求 | 结果 | 回调 | 关键分段 |
|---|---|---|---|---|
| 1 | `mode=explore` + 一句中文自然语言查询 | `index_sync=unchanged`；**没有** `source_retry_query`（空结果时 `source_retry_sync` 仅 28.5 ms，因 unchanged 不重查） | 4172 ms | index_sync 142.7 ms（算指纹），source_query 2464 ms |
| 2 | `mode=file`，裸文件名 `weather_service.dart` | 正确（13–28 行：拼 URL、10 秒超时、非 200 抛出） | 2765 ms | **file_inventory 558.3 ms**（首次，读清单） |
| 3 | `mode=file`，裸文件名 `api_config.dart` | 正确（1–2 行 import，`baseUrl` 取环境变量再按平台兜底） | 2672 ms | **file_inventory 29.4 ms**（缓存命中；剩余是目录指纹） |

- 结论：`unchanged` 跳过同步、空结果不再强制重查、清单缓存三项在真实 SDK 场都被观测到。
- **新发现（未解决，记入已知限制）**：第 1 轮 explore 用中文整句查询，CodeGraph 返回的是无编号源码的关系摘要（`shown: []`），教师如实回答"现有证据里没有源码行"。同一索引下用英文标识符（`WeatherService fetchWeather`）explore 能拿到带行号源码。所以 explore 对中文句子不可靠；角色按工具说明对"具名文件"用 `mode=file` 时不受影响（第 2、3 轮、M1、M5 都是这条路径）。不做硬编码修补。

## B. 场 51 三段 WAV 连续场 + 停顿暂扣

三段固定 WAV 与原场 51 相同（quiz47 / answer47 / followup47，SHA 与 51 一致），output-only，扬声器沿用用户预设 4%，`NEKO_PAUSE_HOLD=1`。三次真实 Native 场（同一失败只重试一次的约束下做成 A/B，各用新 store）：

| 场 | 配置 | 第三段识别条数 | 其余 |
|---|---|---|---|
| `claude-w1-voice-51rerun` | 停顿暂扣=1 + 原场 51 的实验开关（phrase-input、speech-gate、auto-grade） | **1 条**，内容完整（"为什么这道题要看箭头尖端，简短解释，不要重新评分，也不要出新题"） | 第二段没有走自动评分：宿主在识别完成后没有触发 `study_answer`，角色自己答"不对。WEX指向的是DATA"，数据库没有 QA 记录 → 严格检查 FAIL |
| `claude-w1-voice-51nohold` | 同上，但 `NEKO_PAUSE_HOLD=0` | **2 条**（复现原场 51 的拆分） | 自动评分链正常：答对、QA 1 条 |
| `claude-w1-voice-product-hold` | 停顿暂扣=1，**不带**任何实验开关（与日常入口一致） | **每段各 1 条**，包括第三段 | 角色用工具出题、`study_answer` 评分（QA 1、错题 1）、追问不重新评分 |

- 第三段只出现一条识别：**通过**（停顿暂扣把历史上必拆的输入变成一条）。
- 第三场的图是 Sky Scout 架构图（非评分链模式用默认材料），答题 WAV 说"WEX 指向 NUD"与题目不符，所以被判错并记入错题是**正确行为**，不是缺陷。
- **待 Opus 复核（宿主层，未动手）**：停顿暂扣与实验性的 phrase-input/auto-grade 链同时开启时（仅此一次观测，n=1），宿主没有在第二段识别完成后触发自动评分；对照组（暂扣关）同一时刻有 `study_answer` 触发。日常入口默认两者都不启用（`Start-Daily-Tutor-Voice.cmd` 只设 `NEKO_PAUSE_HOLD=1`），产品路径（第三场）评分正常，所以不影响验收；但如果之后要把自动评分链并进日常入口，需要先查这个交互。证据见 `benchmarks/raw/evidence/claude-w1-voice-51rerun.json`（不提交 raw）。
- 物理输出 `UNVERIFIED_NO_LOOPBACK`；听感与真人待用户。
