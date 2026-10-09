# Flutter 真实教学独立审查

审查状态：15 轮主场景、跨 Session/换课/返课、构造函数及简短表达复验全部完成。评价依据是本轮真实 Study UI transcript、授权 Flutter 项目源码、官方参考、实际 Widget 测试及只读隔离数据库，没有向 Tutor 注入标准回复。

原始记录：[JSON](evidence/flutter-product-transcript.json) / [可读 Transcript](evidence/flutter-product-transcript.md)。课程：`lessons/flutter_provider/lib/main.dart`。审计：[主场景 30 次](evidence/neko-product-api-20261009T120000Z.jsonl)、[记忆与课程 8 次](evidence/neko-product-api-20261009T123518Z.jsonl)、[表达复验 4 次](evidence/neko-product-api-20261009T124909Z.jsonl)。

## 主要结论

已经证明真实模型可以解释 Provider、接续追问、换类比、切换 Dart 基础问题再回到计数器、出题、对错误答案纠错、评分并保存当前 Session 总结。不能把整场标成技术全 PASS：早期出现明确 Dart 语法错误与错误辩护；后续修复中也发现丢选择题选项、手动题没有 attempt 身份、长上下文丢当前出题要求等真实产品缺口。

最终两次评分公平：错误的“watch 会持续监视字段”解释得到 WRONG / 0；正确区分内部 count=1 与无重建时屏幕 Count:0 的答案得到 CORRECT / 100。总结准确报告最后 Session 两题一错一对，保留薄弱点。Mastery 0.62 是系统估计，不能等同长期掌握证明。

最终技术纠正已闭环：构造函数复验明确撤回早期补括号建议，第二次简短复验用两句正文准确说明无需修改。真实 Session B 能找回两错一对，离散数学课没有混入 Flutter 历史，返回 Flutter 后记录仍可找到。仍有实际缺口：同考点的自动 topic 标签分散了 Mastery/FSRS；严格三句记忆回答还额外附小检查及上游状态注记。

## 逐轮审查

| 轮 | 场景 | 评价 | 关键证据与限制 |
|---|---|---|---|
| 1 | OCR 逐行解释 | PARTIAL | 主体概念与类比有用，但错误要求在类声明和构造函数之间加 `}`。OCR 的漏括号被过度解释为源码事实。 |
| 2 | 学生质疑错误括号建议 | FAIL | 最后展示正确代码，却编造“类内部的 constructor 不会被识别为 constructor”的解释，为错误辩护。 |
| 3 | 听不懂 read/watch，要求短解释 | PARTIAL | 区分订阅与取对象基本正确；错误声称 onPressed 改 watch 仍能跑；超出指定长度。 |
| 4 | callback watch 反例 | PARTIAL | 正确指出 debug 断言，又错误声称即便 increment 执行，已有 build watch 也不能更新。 |
| 5 | 追问错误更新推断 | PARTIAL | 明确承认并修正已有订阅能更新；仍套四节长解题格式，且 UI 显示无关“拓扑排序”知识图谱。 |
| 6 | 临时询问 final/const | PASS 核心 | 两个 Dart 示例有效；“里面的东西不能变”说法略混乱，后文正确限定 final List 与 const List。无关“基础排序算法”图谱是整合问题。 |
| 7 | 返回 StatelessWidget 与 Consumer | PASS 核心 | 能回到原计数器；Consumer 与 child 示例可用，解释页面级与局部依赖。rebuild 不应被理解为整个 App 重画。 |
| 8 | read 是不是拷贝 | PASS | 准确说返回同一对象引用、字段仍会变化，且遵守三句要求。 |
| 9 | 不 notify 是否自动发现变化 | PASS | 正确否定自动轮询；结论适用于没有额外重建的场景。 |
| 10 | 四选一 | FAIL → PASS | 初次只有题干不能作答；局部修复后完整 A–D，原复验 C 为唯一正确项，未泄露答案。 |
| 11 | 错误选项及理由 | BLOCKED → PASS | 初次 UI 拒绝：手动题无 attempt identity，未调用评分 API；修复并重出后，错误 C 被准确纠错。UI 该行未采样分数，最终只读 DB 的 QA1 已确认 wrong / 0。 |
| 12 | 用电话/短信类比纠错 | PASS 技术 / PARTIAL 长度 | 类比准确区分引用与订阅，针对刚才错误；仍加前言、总结、小检查，超过三句要求。此时图谱匹配已学习的 Provider 主题，相关。 |
| 13 | 删除 notify 的程序行为选择题 | FAIL → PASS | 初次长提示丢当前四选一要求，生成旧式简答题；修复后四个选项完整，并明确“没有其他重建”。C 唯一正确。 |
| 14 | 错误后纠正，再评分 | PASS | WRONG / 0 → 同主题新题 → CORRECT / 100，反馈与实际代码机制一致。 |
| 15 | 当前 Session 总结 | PASS | 正确总结最后 Session 两题一错一对、错误认知和下一步；没有虚构已完全掌握。 |

构造函数必须位于类体内，R1/R2 的语法说法与 [Dart 官方构造函数文档](https://dart.dev/language/constructors)相悖。按钮回调中的 watch 使用限制与断言见 [watch API](https://pub.dev/documentation/provider/latest/provider/WatchContext/watch.html)及 [Provider.of 实现](https://pub.dev/documentation/provider/latest/provider/Provider/of.html)；回调中的 read 示例见 [read API](https://pub.dev/documentation/provider/latest/provider/ReadContext/read.html)。StatelessWidget 依赖 InheritedWidget 时仍可 rebuild，见 [Flutter StatelessWidget API](https://api.flutter.dev/flutter/widgets/StatelessWidget-class.html)。

## 已独立跑过的实际编程验证

命令：`D:\Dev-Setup\flutter\bin\flutter.bat test`，在 `lessons/flutter_provider` 执行，退出码 0，两项全部通过。锁定并实际使用 Provider 6.1.5+1。

- 原 `counter_test.dart`：实际 main.dart 的 read 按钮将 Count:0 更新为 Count:1。
- 新 `watch_in_button_callback_test.dart`：实际 Counter 与 Provider；build 内先 watch，按钮回调错误调用 watch，确实出现 AssertionError，increment 未执行。随后直接 increment，原已有 build 订阅仍更新为 Count:1。测试没有绕过断言，直接否证 R4 的附加错误机制。

另有 4 项离线 Store/Tracker/提示序列化回归通过：临时库关闭重开与课程隔离、最新历史顺序、15 条总结及末尾真实评分字段保留、长/短出题材料保留与超预算拒绝。这些是源码和持久化层证据，不代替真实 UI 重启验收。

## 额外真实复验及实际记忆

| 场景 | 结果 | 独立结论 |
|---|---|---|
| Session B 重启找回 | PASS 核心 | 正确找回三次作答、两处错误及最后一次进步；没有编造未保存章节/时长。把四选一称“判断题”不够精确。 |
| 离散数学换课 | PASS | A={1,2}、B={2,3} 的交集准确为 {2}，明确本课无历史错题/薄弱点，没有引用 Flutter 的学习事实。 |
| 返回 Flutter | PASS 记忆 / PARTIAL 表达 | 两错一对仍一致，准确区分已有正确证据与尚未用答题证明纠正的 read 漏洞；初次暴露内部字段和等级。 |
| 构造函数重新核对 | PASS 技术 / 初次 PARTIAL 长度 | 明确撤回错误，保持正确代码；初次仍强制四节格式，提示调整后复验正文为两句话，无错误辩护。 |
| 学生语言记忆复验 | PASS 内容 / PARTIAL 严格长度 | 三句正文正确总结错误、进步、下一步，无 mastery/confidence 字段；仍另附一个小检查和状态注记。 |

只读 `benchmarks/raw/neko-product-data/N.E.K.O/plugins/study_companion/data/study_companion.db`，连接采用 SQLite `mode=ro`。独立快照：[topic 标签与量化追踪](evidence/neko-product-topic-label-review.json)，主流程补充：[真实记忆运行快照](evidence/flutter-product-memory-runtime.json) / [最终记忆快照](evidence/flutter-product-memory-final.json)。

| QA ID | 同课程 topic 标签 | 实际评分 | 最新 Mastery | 该标签答题次数 | FSRS |
|---:|---|---|---:|---:|---|
| 1 | Provider read/watch/notifyListeners 机制 | wrong / 0 | 0.0000 | 1 | learning，rating 1 |
| 2 | Provider notifyListeners 与重建 | wrong / 0 | 0.0000 | 1 | learning，rating 1 |
| 3 | Provider read/watch 与 notifyListeners | correct / 100 | 0.6189 | 1 | review，rating 4 |

三条记录均属于 flutter-provider，但各用一个不同 topic ID、一个 Mastery 历史和一张 FSRS 卡。QA2 与 QA3 的实际题目考查同一“删除 notify 后内部 1、屏幕 0”行为，纠正却落入新标签，未更新原错误主题的数值状态。因此原始记录、跨 Session 回忆与课程隔离 PASS，概念级进步归并 PARTIAL。没有改库或建立归并框架。另确认当前课程已保存一条 summarize_session interaction。

## 延迟与调用边界

三个审计文件合计 started=42、completed=42，没有 failed；输入 token 合计 101,433，输出 14,002。组成：16 次语义路由、16 次讲解、6 次出题、3 次评分、1 次总结；预算按 30 + 8 + 4 个受控请求执行。API call 编号在 reload 后重复，因此按事件数量与时间统计，不能仅按 call 去重。汇总见 [API 时间证据](evidence/product-api-timing-summary.json)。

模型链路按每轮首个 semantic-route started 至对应 concept completed 计算；其他操作按该操作 started 至 completed 计算：

| 操作 | 样本 | 中位数 | 范围 |
|---|---:|---:|---:|
| 讲解（含前置语义路由） | 16 | 4.265 s | 2.815–8.887 s |
| 出题（含失败/复验） | 6 | 3.077 s | 2.644–3.601 s |
| 评分 | 3 | 2.414 s | 2.099–2.473 s |
| 总结 | 1 | 2.480 s | 单次 |

这不是浏览器端到端延迟，也没有 TTFT。Transcript 的 ui_observed_ms 包括主 Agent 读页面、跨工具确认和保存等待，只能作为观察上界。

额外场景准确模型链路：Session B 5.066 s、数学 3.509 s、返课 6.204 s、首次构造函数 4.193 s、简短构造函数复验 3.527 s、学生语言记忆复验 3.182 s。

## UI 与记忆边界

已独立查看最终导出的 [原生窗口 Ready 图](evidence/tutor-desktop-ready.png) 与 [授权窗口读取图](evidence/tutor-desktop-authorized-capture.png)：可以看到原生 Study Companion 窗口、Ready / Teaching、College、flutter-provider 课程、明确授权标题和内容标记；读取图显示“窗口读取成功”及已读取的授权标题。主流程还保存了 [原始捕获文字](evidence/tutor-desktop-capture.txt)。这些图片证明入口和授权读取的可见状态，不能代替对所有教学轮的像素检查。旧误命名截图没有导出，也不用于总结或错误评分的像素结论。

15 轮主场景跨过数次安全修复 reload，因此属于同课程跨多个 Session 的连续教学；最后总结仅覆盖最后 Session，范围正确。原插件未发现独立的通用教学偏好字段/提取链路；模式与配置可保存，同课历史可保留“初学者、类比”等请求，但不能声称跨课程教学偏好已完整验证。

当前剩余质量缺口：同概念自动 topic 标签尚未稳定归并；有些短回复仍额外加小检查及状态注记；多个真实 Session 的完整课程总结与当前 Session 总结应在说明中区分。构造函数技术错误已经 post-fix 真实复验纠正。
