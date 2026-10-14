# 阶段九：自然停顿的真实宿主接入（默认关闭）

现有 Goal active，完整 contract 与四接续约束保持。阶段八功能分支080d69a继续作为发布基线。此处是实际 Core/Omni接入与离线证据，不是模型、Native播放或真人自然停顿验收。

## 实际行为

`NEKO_EXPERIMENTAL_PHRASE_INPUT=1` 仅启用既有free-app/no-server-VAD/native16k正常单帧路线。Core共用会话绑定点安装真实权限和计数回调；权限含当前installed record/session、active/native/Core lease、input接受状态、ingress/activation、Core frontend websocket对象、实际provider websocket和物理connection generation。game getter不被借用为输入授权。

DSP/VAD/onset与普通打断先运行，之后收集尚未发送的PCM。最多20秒/640000原字节，保留0.3秒前滚；只有确认non-speech且逐sample为零的内部停顿压到0.1秒，非零微弱音频不删。正常句末quiet1.2秒才seal；实际单writer在8秒内按既有WS上限快速分块，semaphore前后/最终send_guard/每次await后复核。缓存帧为LOCAL_ACCEPTED，只有真实成功wire字节进入原Core计数；局部ID不是provider utterance ID。

输入收集中、写入中和等待真实owned response boundary时阻止本地2秒/4秒silence clear或hot-swap偷走输入。已有expected input sequence只作本地marker核对，不伪造server边界。新实际语音改变marker时，退休上一批等待超时，不让旧30秒deadline杀掉新合法输入。总buffer20秒、写入8秒、provider边界30秒都有限。

handoff pending/replay和legacy最多5帧合批沿用原始单次发送路径，整段输入bypass本实验，避免已上传prefix+未发suffix被称作完整未发送phrase。普通close首await前、physical attach和failed teardown退役旧buffer/writer。超限、部分写失败、route切换带未发缓存均明确失败，不重试原batch；失败关闭精确旧ws/generation，不关闭后来替换的winner，有界状态通知。已发送旧partial属于失败证据，不当作完整成功。

collector用arrival-derived chunk-end估计及局部sample cursor；原onset/VAD wall语义不改，watchdog只测现实上界，不以worker较晚clock提前seal。它不证明物理采集首sample时间。

## 实际离线证据

| 检查 | 结果与范围 |
| --- | --- |
| 新真实Core/Omni15项 | PASS：0.896秒内部pause期间无wire，完整非零prefix/suffix保留，success bytes计数、chunk上限、silence/handoff marker、permission/provider/frontend替换、legacy batch、旧deadline不杀新输入、close首await前退役、显式overflow/partial failure/route failure/no retry/default OFF |
| 受影响普通Native handoff12项 | 最终源码再核PASS；原回执、精确旧连接取消、前滚/长输入、权限更改、失败退役等旧断言不放宽。不借此冒称本阶段真人已过 |
| 新Git LF replay3项 | 四changed targets从原revision1d814cf真实Git源码重放，AST/二次幂等/两实际树逐bytes匹配；unknown/duplicate authority与transport helper拒绝并保持原bytes |
| source audio gate | 新四host指纹及两个运行时helper指纹PASS；没有启动host/audio/provider |
| 产品图片语言窄修 | Agent新2+原language4实际wrapper/entry/SQLite通过，Main已复制到daily plugin-code，26产品sha匹配。丢弃旧text后再解析语言，schema/本轮请求优先、课程prefs不改；无新版模型/设备证明 |

首轮手动pending负例未初始化原replay cursor得到UNKNOWN，测试改为调用实际prepare方法后原LOCAL_ACCEPTED断言通过，没有改产品绕过该保护。首轮重放发现overlapping hunk重复helper/admission，保留诊断；改用单一方法锚点、严格已知draft normalizer，并在normalization已满足完整canonical时停止旧重放，修后真正Git LF与两宿主一致。没有放宽sha或重复检测。

四host SHA256：transport894b37af60fa28a8b668094a21d351db1155cf46ce363bd03801811e4e0a692e；asr b44ccbf261283e6f20396c7ce0de5d9004159b3aa460faf6c5b3068c7c83ad9e；session_lifecycle47561debfef3aea5fbf8d5a8557043c7502eed5b1a591c6e97972667694670c2；audio1a00099aa9ab848ffe9f43a3573e36b91bef281f9d68225644b03a578d29eaef。helper指纹在host manifest。无关TTS原bytes保持，原工作树/.workbuddy/index保持。

## 剩余与下一步

只有SOURCE/OFFLINE通过，尚未启用在线。provider对burst是否仍分片、ASR/tool时序、1.2秒缓冲增加的延迟、尾部临时英文/noquiz约束、Native/device/human仍需必要定向证据。首次新连接长静默、密集“未”字、裸纠正材料选择与独立narration宿主保护仍待，局部问题不结束全Goal。

下一步先实际Core/SDK/Study constructor本地stub检查，再以既有单条中文长指令固定WAV做一场必要opt-in比较，不制作新测试材料，不采房间mic，不改音量；只有Main在线/音频/额度。当前实际账本581/2000、app56/null、tech0/0，同轮不重置；本阶段截至此报告所有新外部调用0、无运行服务/Native/录音。初始raw preimage、诊断和录音/DB均不发布。本阶段源码尚未发布。

## 用户要求暂停时的终态补记

本地SDK6量具exec97234已exit0：实际Core/ToolRegistry/SDK/Study/SQLite三工具闭环通过，3个本地stub请求、外部egress拒绝、ledger不变；新隔离store为neko-failure-material-sdk-20261014-phrase6。launcher48264已结束，48911/48916无listener。没有Native/音频/room mic，不把此场当phrase-enabled/provider证明。

用户明确要求在安全点暂停并汇报；原Goal应paused，不complete/blocked，后续只有用户恢复才继续。阶段九host四文件及helper gate当前PASS，26产品sha匹配；图片语言窄修也已本地部署、仍只有SOURCE/OFFLINE。阶段九尚未commit/push，managed功能工作树仍clean080d69a，原工作树index空/脏改保留，两Agent均停止。尚未做任何本轮在线音频。

恢复后的首个具体收口：flush的分块事件目前仍依赖send_event默认毫秒event_id，快速burst可能同毫秒；需要每块唯一wire event_id及定向负例（它不是provider utterance ID）。还需把seal/实际write完成时间纳入可读量具日志，再必要单场固定WAV验证。此处为源码推得的待处理风险，尚未断言Lanlan会按重复event_id去重，也未自行新增model重试。之后推进图像重查/细字、严格英文/术语、narration与整体验收。所有原A–F保留，不缩范围。
