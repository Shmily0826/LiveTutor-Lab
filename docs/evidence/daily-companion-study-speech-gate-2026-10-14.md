# Study 语音工具准入：候选及真实部分失败

本阶段先完整读取contract/plan/status/blockers；承接465da5b，不重建Goal，不重复旧图片quiz、MANUAL支持或过滤/索引批次。所有语音使用原固定中文WAV，假静音native设备，系统输出回环；room mic=false、volume_changed=false。

## 源码/离线

新增 `neko_study_speech_gate_patch.py`，由原late-ASR补丁构造规范helper及精确旧v2迁移。`NEKO_STUDY_SPEECH_GATE=1`才启用；当前日常默认**关闭**。只处理精确free app/no先行server-VAD的三个付费教学工具及point，保留原PCM/onset/cancel。未覆盖speech不因call迟到2秒绕过；quiet>=1.2秒、ASR received wall覆盖最后speech、当前scope callback ready才执行。最多20秒quiet等待，缺ASR/foreign scope/connection/session/handoff/fatal/queuefull拒绝；原no-continuation release释放call，固定effective owner不二次晋升。

同response、同scope/connection的已知pending siblings同步进入原执行路径，避免快point/read-only先seal。仅处理已知同response，未alias未知future或terminal。独立审查先后复现late2秒绕过、快慢siblings两批、mixed siblings两批、call在handoff期间到达仍执行，均补相应实际方法检查；最终10项过。原ordering6项、部署后工具生命周期/完整字节重放5项过；当前turn的19项原打断guard过，transport/onset源码未变。首次5项重放在candidate尚未部署时因runtime仍v2而失败，部署后同项通过；不把第一次红改称通过。

两份runtime_tools.py已通过原patch应用器精确迁移，新的fingerprint gate匹配；最新payload/static23/23。候选只离线与下述单场验证，不能说长句处理完成。

## 实际单场

`benchmarks/raw/evidence/daily-companion-20261014-role-point-gated5.json`。同WAV SHA9d91a87b76074e6a45bff25dbd4fee626b4812e172d9b7864c9a5ea33777574c，源证据仍7aae20f/已过滤当前file第13行fetchWeather。

- speech end wall1791905030.620195；唯一accepted pointer1791905032.016437。真实role参数kind=source、source_line13、symbolfetchWeather；当前DOM声明/可见高亮/材料identity三项通过。
- prefix ASR1791905023.027，tool随后1791905023.081。fresh last_loud大于receipt使候选误等下一ASR；约.4秒后`transcript_not_ready`释放前片call，provider仍自行续答，首audio.delta1791905025.103，早于整句末尾约5.52秒；不能以本地没response.create证明proxy不说话。普通native handoff随后创建第二CONNECT。
- 末片call1791905031.918，末ASR1791905031.935；scope5 gate ready quiet1.332s、asr_after_loud1.328s，point实际执行；工具输出后仅response.done，没有最终native确认文本。WASAPI仅1响声分桶来自早期输出，不能作为末尾确认播放证明。

因此 overall及speech-gate验收均 `FAIL_OR_PARTIAL`：仅“整句末尾后一次指示”成立，完整教学/确认与无提前语音未过。不会为已有pointer结果再重复无修改场景。

额度350→352 DeepSeek、40→42 app、tech0，同round不重置；所有本场owned host/native/surface/meter结束。保留原JSON/音频/截图本地，不发布录音或用户学习DB。真人仍待准备好了。

## 下一步及局部边界

先离线复现“call紧随已ready ASR但新speech frame更晚”被误当未来ASR的具体顺序。候选应固定当前已ready owner并持续等quiet；未来ASR替换时只丢弃，不使旧call晋升。call真早于下一ASR时仍需原单次expected推进；无input item ID的邻接兼容性必须承认限制。缺ASR时不能在.4秒早释放、触发proxy提前音频，应在整体有界输入等待后保守处理。还需确认discard在新ASR之后的自动续答/结果播放隔离，不能单靠collector计数。

这一候选暂不成为日常默认。后续只有与原因相符的实现/离线验证后，才安排一场受影响场景；否则继续D文字结构→行含义→改动影响和F连续学习，不把B单项变全局阻塞。付费教学最终参数完整问题/末尾限制尚未实际验证，不能以point成功替代。

## all-Study opt-in 只读审查

本次只读审查 `neko_study_speech_gate_patch.py`、对应检查及 `neko_daily_voice_probe.py` 的prepare-picture增量，未改生产、账本或进程，未运行音频/线上/付费测试，也未重跑旧批次；主线报告13项实际方法、ordering6及部署生命周期5通过。最新候选名称范围是exactfree/no-VAD下所有 `study_` 调用，默认off，包含只读查询、语言、session和preferences；符合当前语音准入条件的这些调用经过原receipt/ready/quiet及connection/scope边界，已完成旧voice仍可按既有规则直接执行，handoff/fatal入口拒绝也覆盖该前缀，未发现单纯扩名称使控制工具直接提前执行。但gate只决定准入，不验证“是否明确要求长期保存”：缺input item ID时，已ready ASR后超过.2秒才到达且suffix loud更新的call仍可能等待并接受下一次scope+1，原前片arguments不会自动随末尾纠正更新；对remember=True/换课/语言等副作用应继续检查最终参数，不能以等待成功宣称临时要求不会错误持久化。`prepare-picture`明确提交已有图片、course guard并在准备失败后不连接语音；其remember=True保存的是store级全局偏好，fresh course本身不隔离这些偏好。默认acceptance store满足隔离意图，但CLI允许任意 `--store`，只有确认实际使用隔离store时，才能说未改正常日常课程/偏好。该准备动作也不是role语音gate的独立通过证据。只读与控制工具等待最长20秒、缺ASR时拒绝属于当前实验支持范围；first弃片后的proxy自发unannounced音频、完整末尾约束和实际播放仍由主线受控场景分别验证。
# Study 语音工具准入：阶段三实际结果

### adjacent6：单条指示通过，范围有限

`role-point-adjacent6.json` 使用同一9d91a87b固定WAV。唯一point在speech end1791906537.497之后1791906538.902执行，provider first audio1791906540.655；真实当前第13行→DOM三项→简短“已请求高亮当前源码第13行。”→11回环响声过。只有一CONNECT，376/43/0。prefix这次没有tool，不能据此称200ms邻接分支已实际过；此成功也不验证paid解释、临时英文或真人听感。

### gated7：旧prefix参数被升格，保留失败

新的单条复合中文固定WAV，0.900秒句内停顿，末尾“两句英文、不出题、不保存英文”；SHA6b6182d69b2a0ea0e12cb8bae72be5edee5629abe65f600c2201e16242eeb93d，时长16.978秒。复用既有Sky深色图，新隔离store `neko-daily-speech-acceptance-20261014`，先保存明确测试中文/brief/no-proactive偏好、提交原图；不制作新图、不改用户日常课，不采房间mic。

gated7从395/43到416/44。实际五次ASR；三个prefix explain被scope替换拒绝，没有提前provider audio，但在末scope6同时执行了旧prefix“两句英文”参数和最终含“不保存/不出题”的参数，之后又重复两次，四次paid explain。最终文本只有不完整英文片段、native PCM0/loopback0。局部host日志同时显示重复tool result和proxy响应ID混杂导致arbiter拒绝部分输出；不能将 provider audio存在当实际播放。此场PARTIAL，不能打开日常开关。

### neighbor8：相邻接续改善，但教学整体仍未过

最新gated call只有在先于预期ASR至多200ms时才可升格一次；几秒旧prefix携旧参数不得升格。14实际方法、原ordering6和deployed lifecycle/byte replay5过，PCM/onset/cancel未改。注意该时间窗仍是兼容启发式，没有稳定input item ID，不等于普遍endpointing或参数语义保证。

修改后仅一次neighbor8，复用gated7同课/图/WAV，用verify-picture-state读取前后，不再次paid提交图片或保存偏好。416/44→432/45，tech0，同账本不重置。五次ASR；scope3 material及scope4/5旧explain拒绝，整句结束后最终scope6 explain参数包含two sentences/no quiz/no save English。仍三次实际explain，不满足一次完整教学；其中question并未明确“answer in English”，course中文正确地占优。实际native中文两句、28PCM/72响声；English检查未过，不能冒称英文音频通过。

末非静音→最后ASR约1.276秒→首provider音频约7.977秒→首native PCM约7.992秒→chunk scheduled约8.064秒→首次回环响声约8.513秒（0.25秒分桶）。主要等待仍在ASR后多次工具/模型与proxy续答，不能为了降延迟修改已验普通onset/cancel。两场current picture/course一致、长期zh-CN保持、checkpoint为空、history只有concept_explain；支持这两场没有造题/临时语言未持久，不是所有control语义的保证。原完整JSON、录音/截图留raw，不发布。

### 根据失败修复语言参数，尚未在线补证

实际旧检测漏了“用两句英文”，且角色改写question可能仅提“English as a preference”丢失当前输出语言。study_explain新增可选language=zh-CN/en-US，明确只对这次解释生效，非法值在模型前拒绝；兼容counted中文语言请求，并跳过相邻否定表达。角色guidance要求一次切换显式传该字段、保留完整question末尾限制，原course偏好仍优先于仅使用何种语言提问。

用现有SQLite+真实wrapper的四项离线检查过：显式临时参数进入模型cfg/prompt、保存偏好不变，counted/否定/仅语言名词区别，失败finally恢复/非法值不调用，两个重叠解释的临时cfg串行恢复后下一次回中文。新explaining lock只隔离解释之间的临时语言，不宣称解决所有不同工具并发。五项既有teaching failure guard过（旧图片量具缺course/session字段先失败，补量具与context断言后过），reply-shape过；这些是离线，最新语言参数未新模型/设备/真人验收。

全部本场owned host/native/surface/meter结束，432/45/0，日常gate仍off。后续先离线处理同一最终ASR的重复工具/多个response结果与音频owner，再基于真实失败安排必要单场；不重复MANUAL或图片quiz闭环，不用余量安排无意义测试。D窗口读取/纠正与F日常整合可独立继续。Goal仍active。

## 最新解释语言增量的最终只读审查

仅审查 `study_avatar_tools.py` 的可选language schema、counted/negation检测、`_study_explanation_language_lock` / `_study_explain_for_turn` 和对应4项真实wrapper/现有SQLite检查源码，没有重跑测试、上线、音频或账本操作。显式language仅允许zh-CN/en-US，非法值在backend前拒绝；显式参数优先于问题内检测和临时偏好，不写course/Store。解释间lock在任何await前创建，串行保护一次cfg覆盖，try/finally在成功、异常及取消时恢复原值；空reply也经过finally。该lock只保证同实例explain与explain之间的恢复顺序，**不保证quiz/answer/language/preferences/session等其他不同工具的并发隔离**，因为这些路径仍共享cfg。自然文本fallback仍有明确范围：计数词与相邻否定已有离线例子，但全字符串COURSE_LEVEL_REQUEST关键词检测会把“这次用两句英文，不要长期保存”中的“长期”当成课程级请求，显式language能绕过此剩余歧义；不能把当前检测描述为任意自然语义保证。主线4项language、5项failure guard及shape属于离线通过；neighbor8整体PARTIAL（三次explain、中文及实际播放，无提前audio）不能证明这个最新英文参数已通过真实模型/设备/真人。候选默认off，原始单场失败与层次边界保留。此限定审查已完成，本子任务文件修改冻结，后续发布由主Agent执行。
