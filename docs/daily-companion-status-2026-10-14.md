# 日常学习伙伴当前状态（2026-10-15，阶段32收尾）

完整原任务：[contract](daily-companion-contract-2026-10-14.md)，原169行/SHA256 `FD518311C0B3FAFBE038B2BBD83D8EB0DE8986212BCB4B86FCCAB22464084C33`，不以摘要替代、不修改。Goal `01a13531-0341-7611-afc2-5c472a7ccf50` active，不重建；完成须全部A–F实际交付及证据，不能因单项或时间标完成。

每次压缩/自动续跑先完整读contract、plan、status、blockers，再读最新阶段报告，从明确函数接续；用户后续明确指令优先并同步记录。局部阻塞记失败/尝试/恢复条件并换可行任务；限流停止无效重试/退避，不因局部阻塞全局结束。

当前音频边界：必要speaker仅用户已设约4%，不调音量；禁止房间/物理/虚拟mic、捕获设备初始化、回环。已结束human场授权不延续。文字child必须TASK_SILENT，SOURCE+text-only；固定WAV仅文件/内存/WS，必要发声另走已审output-only及8API捕获保护。不要求夜间朗读，下一集中human待核心可用及本人明确在场。这里的捕获设备禁用指音频输入；contract授权的指定学习窗口/受控页面截图仍可用，不采其他窗口内容。

账本沿用bargein-autocheck-20261012：DeepSeek **724/2000**、app **70/null**、tech **0/0**，不重置/换轮/其他付费商，不为耗额度测试；请求数非金额。只有Main调整共享额度与安排在线音频；超时/异常停止/退避避免无限重连。

授权必要本项目代码/隔离依赖/自有测试进程；保留Root脏树/.workbuddy/原学习历史，不删库/清空/reset/clean。仅审查allowlist commit/push codex/功能分支，不合master/强推/覆盖历史；排除密钥、DB、raw录音及无关改动。已有两Agent：screen_guidance窄审，learning_memory容量失败冻结，不换模型/新增。Sky Scout代码/索引/已有架构图只读，复用原两对比图；既有SQLite/CodeGraph，不另建系统。

源码/离线、真实模型/SQLite、Native接收与排程、实际可听、真人体验分开；任何未验收层不得冒PASS。当前用户不逐句配合，自动开发到核心可用后再集中10–20分钟human，旧体验80%等Main的组织FAIL保留。

## 当前交付和证明

- **32 SOURCE/OFFLINE PASS**：__init__在load_config后缓存原配置语言，选定课后复用effective；avatar fallback回配置默认，临时finally重新尊重当前持久语言。只两产品文件；Store原排language机制未改，污染假设被否定，不新建记忆。sharedfixture去language lambda及persist stub，实际保存/重载。
- 新9语言runtime Main/独立过；独立最终course8/temporary6/preferences6通过；Main最终材料14/graded_restart3/retry10/question_identity12过。并非所有语音/全并发通过。独立发现同课保存新语言被临时旧finally覆盖P2，source/offline关闭；完整startup缓存行源码顺序核、46实际首启动证明，同对象二次startup仍未单独实测。
- **32真实SDK/模型/SQLite窄链 PASS**：46不经avatar/setcourse/language预热直接grade，wrong0；feedback/step/misconception English并正确区分入边/出边。QA/mastery/正式grade7→8、所有interactions12→13，原7QA/mastery/interaction完整保持；FSRS4→4，同question binding/原English映射保持、current_question前后{}。SDK3656ms包含轮询，非语音延迟。
- raw46 SHA `05d1de88e8b92f9b20583dafdd942b9de8954638b50580c7adb4930691785bc9`，实际task29期望指纹（含protected HTML）匹配。exec66133 exit0、host主动终止1/无cleanup_error，launcher不存在，48911/48916/9234无listener。全静音无avatar/UI/声音/mic/capture/loopback，不是实际可听/human证明。
- **31窄链继承**：未来同题归属12离线+SDK45两grade跨restart/旧5QA保持，新增两记录同question scope/仅1新FSRS。原3topic不合，不冒跨题概念统一。45raw SHA b9f55c58bd357a8eef77afad4e80aef126e95d673c5ead01a0c0400b2ff65fa7，English映射保留但当时回复中文的原失败不回写。后补text-only仅源码；46实际执行该flag。

## 继承与未完成

阶段23正式wrong→correct与graded重启、19固定入口、22当前图DOM、26/28 Native正式成绩/原ASR/17正PCM及排程等证据继承，未改不从头重验；40短6.438s输入到PCM10.952s只测协议链，39原FAIL不覆。29实际41/42/43及30指导44、31/32具体证据均在原report/raw保存，44分步把邻边误说反向FAIL保留。31旧共享记录“formal10→11→12”是措辞错误：该数是全部interactions，正式grade5→6→7，本轮明确更正，不改原件。

当前priority：日常Native/角色连续追问/出题/正式评分和正确材料整合，daily AUTO_GRADE仍默认OFF；原用户human看不到图/等Main过多未冒通过。其他并发cfg、跨题概念、源码版本、屏幕指示和A–F余项按plan保留。下轮先四文件和32报告，再从已列Native grade模块接续，不反复付费跑本题。

## 发布与数据

31代码92ec265a3773a4cabf5c7e5c88925e4fbf633302/记录c2157e1901c589b6785f33bf46f7d6e89c84633a已发布。32两default代码oldSHAguard/独占phase32-before backup、29 manifest/默认期望SHA及SourceGate通过；本轮精确codex分支发布SHA见末段。Root脏树/空index/.workbuddy/原历史保留，未合master/强推，无DB/raw/录音/密钥入Git。

本次精简前全文按原bytes独占归档 [历史](evidence/daily-companion-status-history-through-phase31-and-phase32-start-2026-10-15.md)，SHA256 `d4ca2bb746ee92a7bafb334fc0880397de76c1b088a403438c46708eb69a2f71`；更早历史/失败/原报告沿归档链保留，contract原文未变。


阶段32发布确认：14精确allowlist文件（2产品source/1manifest、3隔离测试脚本、3当前记录、2证据、3原bytes历史档）已review/commit/push `f42386db3b5d63e9e9784f7e71b22b49414aa9a5` 到codex/daily-learning-companion，remote同SHA/candidate clean/master仍f1e8f3f5605659f0526e43bc3b85c60ae46c85fb。Root index空/脏树/.workbuddy/原历史保留，无DB/raw/录音/密钥提交，contract169行原SHA不变。源码/离线、默认部署、实际静音direct SDK46 English及旧7QA/正式成绩保持窄链已验，DS724/2000/app70/null/tech0/0原round。exec66133已terminal0/host主动终止1/无cleanup_error，无live场需轮询。本轮progress；Goal active/all A–F完整继续，下一先四文件再按plan Native grade/intent/acceptance日常整合，不为延长运行反复付费测同题。共享cfg其他并发/语音/设备/human不冒PASS。


阶段33启动：上一轮32源码/部署/真实46/push f42386d/记录3e4979e是progress，Goal active、ledger724/70/0不变，无live host/exec，Root index空/candidate clean。当前Main/独立实际source/offline发现日常启用三缺口：无题首输入永久poison挡同conn出题→回答；撤回/未确定/no-submit仍识别为answer；无可信localclaim的provider study_answer仍可写QA。调查报告daily-grade-readiness-review保留反例，40先备题不能证明这条连续链。

本阶段先修真实准入：显式健康空question状态须区别DB失败/身份不全，只有旧sealed输入ASR已归属、provider边界完成、同driver/delivery/epoch/authority及下一新正输入才允许无题slot重获新题；replay/overlap/owner/scope毒化不清、不在旧ASR上重读题。无owner provider不能绕local判定写grade，已有同claim join/正式UI/SDK保留。只在可信pending pin可用时接纳首人称中英答案/选择声明，撤回与未提交/不确定优先拒绝，完整原ASR不截短。先实际helper/Core/SDK/tempSQLite离线及独立审，再旧SHA部署和必要真实同连接出题→回答链；尚不盲启daily AUTO_GRADE。原图/源码/材料复用，mic/capture音频/loopback禁，必要speaker仅4%不调整，不反复跑31/32同题文字。


阶段33源码进展：4脚本已实现受限健康空题描述/同conn新输入重获题、无claim provider正式grade拒绝、可信pending自己的中英声明及withdraw/no-submit/uncertain优先拒绝。Main实际intent19（18过/1Windows symlink权限skip）和Native route36全过，含patch迁移幂等、完整Core/SDK/tempSQLite、旧sealed边界、新positive还不够/必须different实际sealed batch与递增seq、失败read/replay/overlap/scope不清poison；所有fake model/transport，只是SOURCE/OFFLINE，不是实时。空题SQL只投影bool，不读private问题整体。独立审进行中。

重要：真实host source仍旧，host manifest/helper指纹尚旧，勿启动host/在线；需独立审后oldSHAguard备份、实际patch及SourceGate同步。ledger724/70/0，无live进程。daily AUTO_GRADE仍OFF。独立SOURCE追踪已确认当前Core普通Omni经ASR pipeline/RNNoise概率或RMS计算bool，并显式传speech_active；此前把普通入口猜为None不成立。legacy/direct client的None仍保守拒绝，真实设备入口未运行，不冒全可用。三缺口初稿反例及旧40有限证明保留在readiness-review。


阶段33收口（SOURCE/OFFLINE/部署）：独立发现额外P2“不是最终答案/仅示例/尚未提交”已前置拒绝，最终Main+独立intent20项=19PASS/1Windows symlink权限1314 skip；Main最终Native36全PASS，独立36已PASS，含实际Core/SDK/tempSQLite但模型/外层transport double，空题fixture恢复不冒真实工具出题。独立report已冻结无剩余具体P1/P2；direct Study entry/SDK保留不等于Avatar typed/UI自然评分，后者active Native无ASRclaim仍拒绝，保留待接。

两个任务宿主benchmarks/raw/neko-product-host及candidates/N.E.K.O均oldSHA完整核对/独占phase33-before备份后，仅canonical patcher改transport+Core，复制纯intent；transport新SHA634ec3f9a681bf0a4fc1e63a554fcae6a87ca3b5dafd7e914ec234a36ffed853，Core fd5160b4d8c7836c9d1167c346163ef6aeed3076d9fa0326843c522c1f3cab86，intent829c2da3cc181b7f99505e09d5b600a346d87fabe2d594ff83639f953a01c7a2；patch重复apply already patched。hostmanifest两源/两helper指纹同步，Main完整verify_source_audio_gate PASS，不启动服务。原backup/raw不入Git。daily AUTO_GRADE仍OFF，账本原round DS724/2000/app70/null/tech0/0不变，无live host/exec，未用任何音频设备/捕获/loopback/在线。

下一实质目标：复用已有daily voice probe三WAV教学链，新增受控正式评分链模式，起步确认无pending，第一轮真实角色工具出题，下一不同sealed输入用自己的自然声明回答；核同conn/唯一正式grade/原ASR/旧历史/新token排程，再追问核不误grade。先probe preflight与观测判据离线审查，再必要唯一有界fixed-WAV output-only场，不用pre-generated题或SDK46冒连续Native；所有物理可听/human未验仍PENDING。阶段33源/部署非全Goal完成。
