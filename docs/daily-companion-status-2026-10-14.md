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
