# 当前图片纠正：丢弃旧text后再解析语言

承接 `daily-companion-dense-image-correction-review-2026-10-14.md` 的第二个条件性P2。Main授权本轮只窄修 canonical study_avatar_tools.py 的wrapper语言提取顺序、补 existing test_neko_native_material_guard.py 实际方法回归及本报告；不修改entry/OCR、材料来源选择、prompt/manifest/部署、host/Core/transport、账本或进程，不创建Agent。

## 修复与证明

旧 wrapper 先由 question+text 提取语言，再判断当前图片并丢弃旧text。明确当前图纠正的实际question没有语言要求、模型同时传入旧“Teach this in English.”时，图片正确保留但requested仍为en-US；课程为中文仍被切英文。旧中文text也可反过来覆盖英文课程。

本轮先新增实际 wrapper→真实 explain entry/finalizer/SQLite 配合本地异步模型桩的负例。修改生产前，这一个test的中英文两个subcase均FAIL：zh-CN被en-US覆盖，en-US被zh-CN覆盖。不是新真实模型或设备事故。

生产改动仅将requested提取移动到来源解析/当前图片旧text丢弃之后，并加一行原因注释。显式schema language仍最高优先，其次保留的当前question/text的语言要求与临时偏好，未明确请求时维持课程语言/default。没有改语言锁、cfg临时覆盖/finally恢复、长期偏好保存、材料绑定或换课/换图guard。

## 必要定向离线检查

使用existing `benchmarks/raw/neko-product-host/.venv/Scripts/python.exe -I -B`，仅执行下列受影响wrapper检查，不重跑旧大批教学/音频/SDK/model。

| 检查 | 结果 | 证明范围 |
| --- | --- | --- |
| Native material guard新增2个实际方法test | 2 PASS | 当前图+旧English text不覆盖中文课程；英文课程不被旧中文text覆盖；当前question明确English仍生效；schema en-US覆盖question中文；当前图片仍附带，旧text仍省去；fresh SQLite长期偏好/course map不改、cfg结束回课程语言 |
| 原 ExplanationLanguage套件 | 4 PASS | explicit one-turn、句数/否定语言识别、失败/非法参数、解释间并发串行与恢复原断言保持，不放宽断言 |
| targeted diff check | PASS | 产品/测试任务文件无空白错误；实际AST导入覆盖源码语法 |

测试检查的是模型入口所用cfg语言、实际source directive/context和持久偏好，不将本地桩返回文字当作实际模型语言质量。原guard其他历史断言未改，只增两项；未重复普通真人打断、材料竞态整批或旧在线场。

## 剩余与交接

SOURCE/OFFLINE通过，未部署、未刷新manifest、未真实模型/Native/设备/真人验证。根报告里的第一个P2“裸纠正+旧text可能落入纯文本”仍未修；不会为修语言而对所有纠正强附任意保存图。密集“未”字的像素可靠性/局部核对也未由本次顺序修复证明，需Main在后续必要图/语言场自然补证，不另为此重复旧付费验收。

本轮外部调用0，沿用四接续文件/Main已核581/2000、app56/null、tech0/0；未重读或调整账本，无宿主或音频进程。原DB/历史和其他脏工作保持。独占产品/测试/本报告已冻结，可由Main检查manifest后整合；长期Goal继续其余A–F。
