# R2：教师事实准确（评测集 + 核对器 + 后置检查；真实复跑未做）

**证据层级：离线（真实 wrapper/桥接 + SQLite + 假教师）；用已存盘的真实教师回复做了历史基线。没有新的真实模型调用。**

## 改了什么
- `scripts/teacher_eval_set.json`：13 题（行含义 2、非 200 3、配置 2、缓存/回退/算法 3、改动影响 1、跨文件 1、错误说法 2…），覆盖 weather_service.dart、server/routes/weather.js、server/src/weather.js、api_config.dart、sky_overlay_visibility.dart、sky_map_toolbar.dart。每题有人工写的 `expected_facts`、粗匹配 `must_match`、`forbidden`。**期望事实对照 Sky Scout 源码（只读）逐条写成**；`test_neko_teacher_eval_set` 会在项目存在时核对窗口落在真实文件内，并核对 22/23/26 行、400/502、缓存 TTL、淡出常量等关键事实仍成立。
- `payload/.../study_citation_check.py`（确定性、无模型）：
  1. **line**：回复里的“第N行/N–M行/file:N/line N”必须落在本次 `shown` 的行集合内（点名文件则必须是该文件）；认得口语化汉字数字（“第二十三行”，与 `_zh_number` 往返 1–399、1000、1005、1234、9999 一致）。
  2. **placement**：“第二十二行抛出异常”这类紧邻写法，若证据里该行没有 `throw/catch` 而它在别的行，则违规并报出正确行。守卫式写法（“第22行判断状态码，不是200就抛异常”）合法。
  3. **identifier**：回复里点名的代码形标识符（camelCase、snake_case、文件名）必须出现在证据或学习者问题里；普通英文词不算。
- `payload/.../study_code_teaching.py`：教师回复返回前过核对；有违规 → 带违规说明让教师**重试一次**；仍违规 → 删除越界/错位的行号引用、删掉含未见标识符的句子，其余保留；无内容可留则如实说“找不到依据，不下结论”。环境变量 `NEKO_CITATION_GATE=on|observe|off`（默认 on；observe 只记录不改动，用于量基线）。教师提示新增“行号只用证据印出的、取该语句旁边印的那个数字、不确定就点名语句”。
- `scripts/neko_source_scene_probe.py` 新增场景 `r3eval`；`scripts/teacher_eval_score.py` 对探针输出做确定性计分。

## 证据
| 项 | 结果 |
|---|---|
| 历史真实回复基线（`teacher_citation_baseline.py`） | `benchmarks/raw/evidence` 里 27 条不同的教师回复、36 处行号引用：**越界 0**（只含行窗口检查；证据全文未存盘） |
| 已记录的真实错误 | `codex-r2-final-proof.json`/`p5-native-a.json` 里教师说“第二十二行的 `throw` 不执行”（throw 实际在 23 行）：用当时的真实证据收据复核，**placement 违规被抓到、正确行为 23**；剥离后保留其余内容 |
| 假教师桥接测试 | 干净回复 1 次教师调用；越界/错位 → 重试 1 次且重试文本含真实窗口；二次违规 → 剥离；仅剩违规 → 不下结论；重试抛错 → 保留原回复剥离后；observe/off 不改动；degraded 不检查 |
| 回归 | 新模块 20+11+6 项；源码教学相邻 15 个模块全过；全量仅原 7 个历史失败 |

## 没有做到 / 如实说明
- **“评测集复跑 2 次、违规率降到 0、人工事实错误明显减少”没有做**：需要真实教师调用（额度未填）。可用 `NEKO_CITATION_GATE=observe` 先跑一遍量基线，再 `on` 跑一遍，再用 `teacher_eval_score.py` 对比；人工仍要逐条对照 `expected_facts`。
- 历史基线的 0 违规**只说明行号越界在已存盘回复里没出现**；真实错误是“在窗口内但错位一行”，由 placement 抓，而 placement 只管 throw/catch 紧邻写法。其他类型的行内错位（如把 `return` 说在别的行）、“map 文件”这类对象说错（重启后追问那次）**不会被抓到**。
- 重试代价：一次违规多一次教师调用（P8 日志里整个 study_explain 工具耗时 3–5 秒，教师调用是其中一部分，所以违规那一轮首声约再晚数秒）；首次回复已写进学习记录（interactions）的那一行仍是原始回复，只有返回给角色的内容被修正。
- 回退：`NEKO_CITATION_GATE=off` 或删除 `_verified_answer` 调用。
