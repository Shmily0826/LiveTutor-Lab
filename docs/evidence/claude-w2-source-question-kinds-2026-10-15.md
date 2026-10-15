# W2：源码教学题型覆盖

日期 2026-10-15。证据层级：离线 + 真实文字模型（DeepSeek，静音 text-only）。无 Native、麦克风、真人。Sky Scout 只读（7aae20f）。账本 DeepSeek +22（1038→1060），Lanlan.app +0。

## 先写的离线测试（真实改动前）

`scripts/test_neko_source_question_kinds.py`：五类题型各一个用例，走真实 `study_explain` → `explain_project_code`，CodeGraph 与讲解模型用假实现：项目结构（只给 `mode=structure`，无 query）、跨文件流程（两个文件窗口按顺序读、各自保留引用）、某一行含义（窄窗口）、改动影响（改动点 + 消费方）、错误说法重新查证（省略 `code_requests` 复用上一轮窗口）。加上 `test_neko_structure_fold`（4 个）和对 `test_neko_code_structure_request` 的两条新断言。

## 真实场与对照源码的判断

量具 `scripts/neko_source_scene_probe.py`（新建任务 store，复制授权文件；`claude-w2-kinds-1/2`、`claude-w2-structure-3`）。我逐条对照 Sky Scout 源码判断：

| 题型 | 第 1 次（修复前） | 判断 | 修复后 |
|---|---|---|---|
| 项目结构 | 把 `server` 说成 `app_sky_scout/server`（错嵌套） | **错** | 四块都对；不再断言模块间调用，改成"想看哪两个模块之间怎么衔接？" |
| 跨文件调用流程 | 客户端拼 `/api/weather?lat&lon` → 服务端 `router.get("/")` 校验坐标、调 `fetchWeather`、`res.json` 返回 | 对 | 对（并补上 `jsonDecode` → `Weather`） |
| 某一行含义 | 第 22 行判断状态码是否 200，下一行抛异常 | 对 | 对 |
| 改动影响 | 400 改 404 客户端行为不变（都 `!= 200` 抛异常）；"其他调用方可能受影响"标为推断 | 对 | 对 |
| 错误说法重新查证 | "无法核对服务端"——没读到 `weather.js`（**错过了上一轮读过的文件**） | 部分对（诚实但没答到点） | 对：服务端 catch 返回 502 + 错误 JSON，不是 200 空数据；客户端第 22 行非 200 直接抛 |

## 两个真实缺陷与修复（payload 层，已部署，不涉及宿主）

1. **项目结构错嵌套。** `_structure_lines` 把目录平铺成按字母排序的前 40 行，`sky_scout/server` 排在 42 个文件夹中靠后的位置，模型看到的全是 `app_sky_scout/...` 就自己编了层级。现在：先给一行"项目顶层条目（互为兄弟）"，超过 40 个文件夹时丢最深的而不是字母序最后的，并说明有多少深层文件夹未列出；文件树提示词加一条"树只显示目录不显示调用，模块之间谁调谁只能当作一起去读的线索"。位置：`study_code_tools.py`。
2. **追问只复用最近一个窗口。** 一次讲解最多读 3 个窗口，每个窗口写一行 `code_question`，而 `last_source_requests` 只取最新一行，所以"按刚才的源码核对"丢了前面读的文件。现在 `code_question` 行带本次调用的 id（`study_call_trace.current_call_id`），追问取同一次调用的全部窗口（按读取顺序、同一项目、最多 3 个）；没有 id 的旧行保持原行为。位置：`study_call_trace.py`、`study_code_tools.py`、`study_code_teaching.py`。不改旧记录，只在新行的 metadata 多一个字段。

## 已知限制（诚实记录）

- `mode=explore` 对中文整句查询不可靠（W1 观测）；已读 `mode=file`/`structure` 路径不受影响。没有做硬编码修补。
- 五类题都是我指定 `code_requests`（模拟角色按工具说明发出的请求）；角色自己会不会选对请求形状，需要 Native 场或真人验证（W5/验收）。
- 回答里的 `server` 是"后端接口"这类概括来自目录名，仅此一层推断。

## 离线回归

受影响的 29 个测试模块**逐个独立进程**运行，全部通过（`claude-w2-offline-1.log` 先发现 `test_neko_code_history_revision` 的旧夹具要提供 `current_call_id`，已补并加断言）。注意：把整套 `test_neko_*.py` 放进同一进程跑会因为隔离守卫串扰出 58 个错误，单独跑通过；`test_neko_tool_result_lifecycle`（宿主 `_tools.py` 替换唯一性）和 `test_neko_autocheck_readiness`（预算 None）单独跑也失败，与本次改动无关（M1 报告之外的既有问题，未处理）。部署前后 SHA 与 SourceGate 见状态文件。
