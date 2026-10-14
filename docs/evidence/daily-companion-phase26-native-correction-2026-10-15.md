# 阶段26：同题 Native 纠正与原错答保留

上一轮阶段25是progress：真实ASR正式wrong0/SQLite新增一QA、Native新token11PCM与播放调度，原量具FAIL保留并修后只读19checks通过，源码35abae0/记录39f98ba已推。没有physical听感或human PASS；AUTO_GRADE日常默认OFF。Goal active，全部A–F保持。

本轮复用同一个C32任务/已有forward图/场37错题，不生成新题、不提交新图、不写原daily DB。新增observer --grade-correction，必须--grade-current且禁止prepare-grade-quiz，启动前snapshot与首次pin严格相同、evaluated=true且last verdict wrong/partial。普通pending模式保留false要求，unknown/换qid/aid、correct不重评。实际main AST模式8项Main通过，包括原6case和两种baseline/禁替题。原产品Core/SQLite correction代码已存在，本轮尚无必要产品修改。

只读现任务QA3/last wrong/同原题及已评attempt已核。为本纠正场一次离线合成明确改答案WAV，直接exclusive文件流、不播放不捕获：SHA256 76127dc2a3318d8fd1024aed99a1a5272af6401cf61c6a5bf474a331ff4213d3，17.014s，意图分类correction。文本明确WEX→NUD，与已验证原图一致，后续是否识别/正确评分要看实际证据，不能按脚本文本冒称正确。

既有Agent只改grader_snapshot/acceptance和其tests，增加correction模式：同qid/题干、新aid/evaluated；恰+1QA、旧wrong全行hash不变；新formal/marker result aid绑定新题，输入markers仍原aid；原错答可能属于之前host session，不捏造correction_of持久字段。snapshot公开topic_id可验证原/新同topic，不能只是题干相似就说同概念。Native token/capture/terminal门禁继承原19checks，不放宽普通answer；需要用真实JSON题存储形态覆盖反例后才开实际单场。

当前尚未启动host/Native/线上请求，账本实际685/2000、app65/null、tech0/0，沿用bargein-autocheck-20261012不重置。Main独占在线与额度。speaker仅用户已设4%必要输出，不改音量，不启mic/虚拟mic/capture/loopback；所有固定输入内存/WS，8API保护仍需实际验。失败退避/no retry loop，局部阻塞转其他A–F。下一步量具/实际schema+权限窄审、必要一次本wrong题纠正，再做日常入口及其余工作，不为修量具重跑已过场。

## 场38最终结果（以上为启动前记录）

唯一exec46447已terminal/exit1/cleanup_errors=[]。实际Native ASR明确纠正WEX→NUD，经过原正式Study/DeepSeek入口：同qid新attempt，correct100，QA3→4和formal+1；原wrong0与其他QA完整rowSHA、旧formal公开投影均保持，原/新非空topic_id相同。输入markers仍旧attempt，grade_complete/relay_written.result_attempt_id为新attempt，未虚构持久correction_of。原题问从WEX出发箭头的起点/终点，与Main已核的同一submitted图WEX→NUD一致，材料前后没变。角色一句“对，起点WEX、终点NUD，完全正确。”与正式反馈一致。详细身份在status，任务隔离数据库不发布。

原量具22checks仅new_token_pcm_after_grade=False。实际Native共8个binary消息：7个正PCM合计378480bytes，以及一个空binary；每个都在正式grade后且属于受控新token。`neko_native_telemetry.py`计入所有binary，而实际host `static/app/app-audio-playback.js`先验证epoch/retired，再明确跳过byteLength0。因此空消息既不是PCM，也不是完成/ACK。修量具保留全部事件owner/时序、bytes非负整数（拒bool/NaN/inf/负/小数/string），另要求至少一个正PCM、schedule不早于首正PCM；fresh trace计数仍包括空消息，不删失败记录。Main及独立新增反例后21tests通过；原普通场37只读20checks仍全真。

只读重算场38为22/22 candidate，Main语义核查通过。原exit1/FAIL保留，未重新启动模型场修量具。原件SHA256 `c421dc05ef6fa71018ca1c00a3923a0b312ad005d1f3af20f4f4036b582161f8`；另建 `benchmarks/raw/evidence/daily-companion-20261015-native-correction38-rechecked.json`，SHA256 `1f2837ad9f9ffcd44b160f60fd5654d41b9ecafd532b8f30cd3568aa44571cec`。完整原件和学习DB/语音均仅ignored raw，不push。

真实accepted/grade_complete为conn1/scope2，relay为conn2/scope4；旧token cancel收到，fresh Native旧PCM0，全部新消息为新token。最终playback source_ended/activefalse/remainingSeconds0；这是Native接收/调度/播放终结证据，物理扬声器可听、真人体验仍未验。output-only readonly/8API captureBlocked已实际安装，fixed input capture_started=false，没有mic/捕获/回环/音量操作。

## 延迟、预算与边界

speech end→观察ASR10.602s；accepted→正式grade4.308s；grade→relay0.579s；relay→首正PCM2.225s；PCM→schedule0.527s；speech end→PCM17.707s。既有host phrase日志进一步拆：speech-end估计wall1791992478.724、封口2479.933、首写2479.942、完成2479.960，queue wait0ms、写入32ms；写完→accepted约9.290s。前一段有意保护1.2s自然停顿；后一段包含服务识别/返回与调度，不能把总10.602s全部归于静音阈值或单模型。下一步优先用现有日志补分段观测后再优化，不凭猜测削弱普通打断或停顿保护。

真实偏好公开preferences、cfg.language及材料前后相同；RPC整个对象含_seconds差异不等于偏好变更。任务coreApi恢复deepseek。总DS685→691(+6)、app65→67(+2初始/受控relay)，tech0；原round及额度不变，不把全部DS请求都说成评分调用。48911/48916/9234实查无listener，无running exec待轮询。

本轮仅observer/量具及测试/文档修改，产品Core、runtime部署未变，日常AUTO_GRADE继续默认OFF。Main+独立preflight8、acceptance21通过；只读derived及语义通过不追认原exit0。Goal实查active，不局部完成；自然短答/legacy/replay/日常启用范围、语言术语/历史实际取用/源码引用/受控指示及完整A–F继续，暂不占用本人再验。精简的plan/status/blockers之前完整bytes已独占归档并记SHA，contract未动。

发布：本阶段12 allowlist文件已review/commit/push `3016a30a8910f6e21efbf63c6b94725f276b87f4`；remote codex同SHA、candidate clean，remote master仍f1e8f3f5605659f0526e43bc3b85c60ae46c85fb。Root index未stage/原脏树保留，raw音频/DB/密钥未提交。下一轮先四文件，再补既有phrase日志的自动分段观测/定位延迟，随后完整A–F，不以本阶段结束整个Goal。
