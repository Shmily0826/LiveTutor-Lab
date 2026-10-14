# Voice probe完成与默认偏好判据窄审

日期：2026-10-15。仅只读 `neko_daily_voice_probe.py` 本轮progress/default增量及新纯AST completion test；只新增本报告。不启动服务/provider/API/设备，不读用户DB或修改账本、共享源码、旧raw。最新授权仍禁止mic/capture/loopback，必要speaker约4%不调，本轮无声音。

Main提供voice35实测：已有ASR、study_explain及24 Native PCM/两句English，sourceEnded queue0；观察量具受pong/周期playback影响timeout，偏好判据强求显式已存zh-CN又产生false。**原raw35 FAIL/PARTIAL保留，不修改或追认PASS**；本 Agent未读取/重跑该私有场，不据源码修复认领声音/human。

## 已确认增量与原停止约束

native_response_progress排除pong、native_speech_playback_state和speech_playback_state，保留semantic events最后type/wall及binaryFrames；late text/transcript/audio/system/failure仍能推进签名。默认偏好改比较before/after实际preferences及effective config language，允许课程继承语言而非强制prefs必须显式存language，不修改真实学习偏好。

observe_native仍单独检查fixed票撤销、session_failed/session_ended_by_server及control rejected/resync/input delivery failed并置failed/ended；completion仍要求真实turn end且晚于当前input、35/55秒最低观察、6秒无新响应及playback inactive。deadline、3秒末尾观察、timeout记录与output-only失败exit1保留；没有因这次量具修复重连provider或重播输入。PCM/shape候选仍标semantic review、physical output未验/human pending。

独立执行 `python -B scripts/test_neko_voice_probe_completion.py`：**OFFLINE AST6 PASS，0.000秒**。只提取两个纯函数，不导入应用/音频/provider。该6项没有覆盖以下两个具体边界，因此不能把通过等同判据闭合。

## P2：缺preferences内部观测仍可通过

before/after output.ok=True，但两边都省略preferences时，当前None==None且config language相同非空会返回True。整个section缺失已由测试拒绝，内部字段缺失则未覆盖。这违背缺观测不通过，可能把未知默认变化误标未变。

最小修法：两preferences均须为dict（合法空dict仍可表示继承默认），随后再比较；补内部字段缺失/非法值和failed ok负例，不将临时英文升级为已存偏好。此发现已即时交Main。

## P2：bounded trace滚动仍受被排除心跳影响

签名含len(filtered events)。实际trace最多500条，新增被忽略pong/playback会挤掉最旧semantic event，filtered长度下降也被当progress变化更新native_changed；即使最后semantic wall/type和binary count不变，quiet仍被延长。小trace添加三个心跳的用例不能复现这个滚动条件。

最小修法：使用最新semantic wall/type与累计binary count，或真实累计semantic counter，不把因ignored事件挤出旧条目的长度减少当新响应。补满500trace、连续ignored滚动负例，同时保late semantic/binary正例；不删旧reject、不弱化failed或current-input约束。此发现已即时交Main。

结论 **SOURCE REVIEW两项量具P2待修**；其它原timeout/late fragment/失败停止边界保持，修后仍需只按新证据记录，不能重写35。唯一写本报告，冻结等待精确关闭。

## 两项P2精确关闭与独立AST7

只读最终增量确认：native_response_progress(snapshot,previous)仅保留monotonic binaryFrames和最高非ignored semantic wall；observer实际把previous progress传入。filtered长度/eviction下降不再参与，因此500条心跳挤出全部旧semantic也不产生伪进展；之后新的semantic wall或binary增长仍推进quiet时间。该签名仅是当前Native观察进度，不是provider utterance id、owner或ACK。

teaching_defaults_unchanged明确要求before/after ok True且preferences均为dict，再比较内容和非空effective config语言。两边都缺内部preferences不再以None==None通过；合法继承默认、不显式保存language仍可通过，不改真实prefs。原ended/minimum observation/6秒quiet/playback inactive/deadline/失败停止未改。

独立执行 `python -B scripts/test_neko_voice_probe_completion.py`：**OFFLINE AST7 PASS，0.001秒**。新增满500ignored窗口彻底evict old semantic负例及后续late semantic/binary正例、内部preferences缺失与failed ok拒绝均在actual纯函数AST上执行。仅stdlib，未加载应用/provider/设备。两项 **SOURCE REVIEW CLOSED**，限定最终增量未发现新具体P1/P2。

修复为以后量具使用，raw35及派生结果未写回，不追认完成/语义/声音/human通过。唯一追加本报告，最终冻结。
