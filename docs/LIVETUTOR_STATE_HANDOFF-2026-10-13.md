# 交接报告：LiveTutor 语音打断现状（2026-10-13 01:05 NZDT）

**最新教学结果：Goal已complete。** 真人基础教学、真实后端解释/例子/出题/判错/纠错/判对及宿主重启续题有证据；追加授权后完成真实客户端切换的语音连续性、最新两句话提示验证、完整宿主重启后的真实错题回忆。另修正语音合同与网页四节/追加练习合同的冲突，真实模型回忆不再追加题目。累计DeepSeek173/300、app19/30、tech0，全部会话已清理，未为用完额度继续测试。既有普通真人打断结果保留，跨结束真人专项/长期稳定性未扩展；OCR仍不等于架构图视觉理解。见[最终教学验收](evidence/teaching-quality-goal-accepted-2026-10-13.md)。下文各额度/判定为原时点历史，不作为当前状态或额外启动授权。

**10-13 18:25 后续结果：** 直接接管后修复了播放反馈重复发送、第二条缺失 audible 覆盖资格的缺陷，并完成一场真实麦克风插话：实际两次 handoff、新连接回答音频和用户确认旧声音停止/新问题有回答，普通 barge-in 本场 PASS。详见 [直接接管验收](evidence/native-barge-in-direct-takeover-2026-10-13.md)。跨结束真人专项与教学质量仍未通过；当前累计 DeepSeek 60/60、Lanlan.app 11/12，已清理全部会话，不再使用本文旧启动配方追加在线测试。

写给**没有任何本轮上下文的下一个 agent / 独立评审**。凡是我没亲手核过的，都标在 §6 的"推断"列里，
不要把我的措辞当成实测。学习者（本项目唯一维护者兼使用者）的三条约束在 §8 末尾。

**10-13 后续补记：** 先读 [静默录音内存检查](evidence/silent-recorded-pcm-memory-2026-10-13.md)。
结论为“能量回退 + mock handoff PASS / 真实 barge-in UNVERIFIED”，不改变本文件的 P0-1 判定。
本文保留历史快照；§8 的裸启动命令与“≤1 CONNECT”、§10 的“全部只读”标题不能作为当前执行配方，边界更正见补记 §5。

## 0. 一分钟版

- 产品战线只有一条：**说话能不能插进老师正在念的回答里（P0-1）**。当前判定 = **未证明**，
  不是"无效"——真机上从来没拿到过一次可归因的 armed 事件。
- 代码侧最新一段工作是**未提交**的 native handoff（§5）：不再猜阈值，改用宿主自己的连接代际 + 有界 PCM 缓冲 +
  前端定向取消。它 10-12 **21:17 真机人测 FAIL**（AttributeError），21:33 修好，**修后一次真机都没跑过**。
- **额度没有被用完，是上限被人压低了**（§3，这是本报告最重要的一条更正）：学习者在 15:3x 已把
  **300 次 DeepSeek / 12 条 CONNECT** 的授权写进 `docs/LIVETUTOR_REAL_MIC_FIX_PLAN.md` §1，
  实际只花了 30 / 6；但 21:14 那次交互启动把 cap 文件的 `budgets` 写成 **30 / 8**，于是读起来像"见底"。
  恢复这两个数字是**一次行编辑**，且需要学习者点头。
- 远端形状危险且误导（§2）：`origin/master` 停在 10-10，本地领先 135 个提交；学习者推上去的是
  `fix/neko-realtime-barge-in` 上那**一个**提交，它缺今天全部的仪器与账本。

## 1. 靶心与判定口径

每条结论必须标证据层级：**L1** 模型/插件产出、**L2** 客户端帧与日志、**L3** 系统回环能量、**L4** 人耳。
**L4 一律"待用户听测"，agent 不得自判通过。** 夹具（假麦克风 wav）跑出来的数字是 L2，
**不得当作产品结论**——本轮最贵的错误就是这么来的（§4 第 7 层）。

## 2. Git / 远端现实（我用 `git ls-remote`、`merge-tree`、`sha256sum` 逐条核过）

| 项 | 事实 |
|---|---|
| 本地 `master` HEAD | `73bf0d1`（10-12 17:28）"Add the stage the pre-flight gates could not cover…" |
| `origin/master` | `f1e8f3f`（10-10 02:02）→ 本地领先 **135** 个提交，全部未推 |
| 学习者推上去的东西 | `refs/heads/fix/neko-realtime-barge-in` = **单提交 `c558c67`**（10-12 23:38，父提交 `f1e8f3f`），10 文件 +2813/−4 |
| PR | **无**（`gh pr list --state all` 返回 `[]`）；仓库 **private** |
| 内容一致性 | `c558c67` 里 `neko_voice_host_patch.py`=8e7c3e54…、`neko_native_barge_in_patch.py`=50e31380…、manifest=cc19b7b1… 与工作树**逐字节一致**（前两个还等于 manifest `source_scripts` 自声明的 sha256；**manifest 自己没有自声明哈希，`source_scripts` 只有那两个 `.py`**）。但同提交的另外 3 个文件**与工作树不同**：`patches/.../README.md` 93ef3477≠d1da0b61、`neko_desktop_tutor_host.py` caa689a0≠07b8481d、`neko_tutor_start.py` 147392e4≠7d93e587 —— 即**启动器/宿主封装那一侧，远端比工作树旧**。离线那三套测试不 import 这三个文件，所以"我跑绿的那份"只对补丁与用例正文成立 |
| 那条分支缺什么 | **`git diff --diff-filter=D --name-only master c558c67` = 128 个 master 独有文件不在那条分支上**：今天的全部仪器与证据、`neko_run_barge_in_scenario.sh`、`test_neko_turn_chain.py`、`docs/evidence/**`、`Start-Avatar.cmd` 等（我先前只点了 8 个名字，**低估了 16 倍**）。反向只有 3 个文件是分支独有且与工作树逐字节相同 → 分支上没有本地复现不了的东西 |
| 能否合回 master | **会冲突 5 个文件**：`patches/.../README.md`、`manifest.json`、`neko_desktop_tutor_host.py`，以及 `neko_voice_host_patch.py`、`test_neko_realtime_barge_in.py` 两处 **add/add**（`git merge-tree --write-tree master fix/...`，只读模拟） |
| 未提交改动 | 按 10-13 01:45 的状态重数：**5 个代码文件被改**（manifest、`neko_desktop_tutor_host.py`、`neko_tutor_start.py`、`neko_voice_host_patch.py`、`test_neko_realtime_barge_in.py`）+ **2 个 `.workbuddy/memory/*`**（10-09 另一个 agent 的笔记，Goal 要求保留、别顺手带进提交）+ **4 个未跟踪**（3 个新脚本 + 本交接文档）。我先前写的"6 改 + 3 新"是写文档当时的快照，已被这份文档本身过期掉 |
| 另一个 worktree | `C:/Users/Shmily/AppData/Local/Temp/livetutor-barge-publish-f1e8f3f`（干净，pin 着那条分支；`git worktree list` 里带 `+`） |
| 备份风险 | 135 个提交（今天全部的仪器、闸门、两份交付报告）**只存在这一块硬盘**。学习者已否决"push master"，我提的折中是推旁路 ref `backup/master-2026-10-13`（不动 master、不建 PR、无合并语义），**待他点头** |

## 3. 额度现实与它闸住了什么（10-13 01:20 更正过）

`benchmarks/raw/neko-desktop-egress-cap`（10-13 00:30 实读，**我没有改动它**）：

```json
{"budgets": {"api.deepseek.com": 30.0, "www.lanlan.app": 8.0, "www.lanlan.tech": 0.0},
 "round": "bargein-autocheck-20261012",
 "spent": {"api.deepseek.com": 30, "www.lanlan.app": 6}}
```

**这三行很容易被读成"额度用完了"，但它不是。** 语义在 `scripts/neko_desktop_tutor_host.py:430/535`：
`budgets` 是**本次启动采用的上限**（操作员对 cap 文件的编辑会被当场采纳并在下一个请求生效），
`spent` 才是本轮累计消耗。对照另外两份文件可以还原真相：

| 证据 | 内容 |
|---|---|
| `docs/LIVETUTOR_REAL_MIC_FIX_PLAN.md` §1（15:3x，仓库文件，学习者原话"再给你300次你做一下"） | **本轮授权 `--egress-budget 300` / `--api-budget 50` / `--voice-connects 12`**，轮次 `bargein-autocheck-20261012`，用途限定 P0-1 打断的无人值守验收；§1 末尾明确作废了"300 需要你点头"那句——**点头已经发生** |
| `benchmarks/raw/live-human-acceptance-restore.json`（21:03:46 写） | `budgets 300/12/12`，`spent` DeepSeek 30、lanlan 5 —— 即"给人机交互那场之前，先把上限恢复到授权值"的还原目标 |
| `benchmarks/raw/evidence/neko-live-human-acceptance-20261012-ui-blocked.json`（20:06:55） | 上一场以 `BLOCKED_DESKTOP_AND_CLEANUP_PERMISSION` 收场（agent 的子 UI 在 CodexSandboxDesktop、物理输入桌面是 Default，够不到真桌面），`human_microphone_trial_started: false`，DeepSeek 30→30、CONNECT 5→5 **没有消耗**；它的 `ceilings_retained_for_user_interactive_launch` 正是 **30 / 8 / 0** |
| cap 文件 mtime | **21:14:15** —— 21:17 那场真人试验收所用的上限，是这次启动写进去的 30/8 |

**结论**：本轮纸面剩 **DeepSeek ≈270、CONNECT ≈6**；`budgets: 30` 是留给"学习者在场的那一次交互启动"的保守上限，
恰好等于已花数，于是把两道闸都读成红了。

由此产生的四条判据：

**补两条机制细节（我 01:35 读 `neko_desktop_tutor_host.py` 的记账线程得到的，直接决定"恢复上限"这个动作长什么样）：**

- `scripts/neko_desktop_tutor_host.py:469-477` 的 `_limit()` 每次请求前先跑 `_adopt_live_caps()`
  （`:479-504`，把整个 cap 文件的所有 host 拉进内存），注释写明"unless the operator has raised it mid-launch"。
- `:441-444` + `:516-524`：启动时如果 `round` 与文件一致就 `_load_ledger()`，而它**用文件里的 `budgets` 覆盖 CLI 传进来的上限**（`:522-523`）。
  → **`--egress-budget 300` 在本轮（同一 `--budget-round`）是无效的**，文件里的 30 会赢；
  只有**编辑 cap 文件**才能抬起来。学习者那句"点头"要落到一次文件编辑上，不是启动参数。
- 反过来：换一个 `--budget-round` 会让 `resumed=False` 并 `_persist()` 写入 CLI 上限 —— 那才是
  Goal 里"不许新建轮次绕过额度"所防的那个洞。

1. `neko_voice_autocheck.py --readiness` 的 `budget_round_is_the_authorised_one_with_room_left` **现在是红的**；
   `scripts/test_neko_autocheck_readiness.py` 我实跑 **12 passed / 1 failed**（只红这一条，00:30）。
2. 红的原因不是"授权用尽"，而是**上限被压低**。恢复 = 把 cap 文件的两个数改回 300/12，
   这**属于已有书面授权的还原**，但仍要学习者点头（我不会自己动 cap 文件，也不新建轮次、不重置计数）。
3. 按 10-13 的算术：自动场景一场约 4.7 条 CONNECT（今天 6 场 15→43=28，DELIVERY §4 账本表）→ 剩 6 条**够开一场**；
   DeepSeek 270 次 ÷ 实测 21.6 次/分钟 ≈ **12 分钟讲话量**。所以"完整验收排不了期"这个判断**当时是错的**。
4. 一条重要解耦（学习者提出、我在代码里核实为真）：`--readiness` 只出现在
   `scripts/neko_run_barge_in_scenario.sh:45` 与 `scripts/neko_voice_autocheck.py:239`；
   `scripts/neko_tutor_start.py` 和两个 `.cmd` **完全不调它** → 真人直启不经过自动仪器的闸。

## 4. 打断战线：七层根因（都已钉成用例，别重新发现一遍）

出处：`docs/LIVETUTOR_REAL_MIC_FIX_PLAN.md` §2.1（前六层）、`docs/LIVETUTOR_DAILY_USABLE_DELIVERY.md` §10.1（第 7 层）。

1. `handle_interruption` 首行 `if not self._is_responding: return`；`_is_responding` 只由
   `_begin_response_lifecycle` 写；免费代理从不播报 `response.created` → **provider 侧 `response.cancel` 结构性不可达**。
2. 路由名 `lanlan_app_gemini` 是陷阱：`_is_gemini` 取 `api_type`，不代表走 Gemini SDK。
3. 接线一度写在 `if not self._has_server_vad:` 里，而宿主自己的 `session.update` 就发了 `"turn_detection":"server_vad"`
   → 永不执行。300 s / 24 个有回答的回合，`speech_started` **0**，所以"这条路由自己会打断"是假的。
4. `elif raw_loud` 在 `_rnnoise_vad_live` 为真时不可达；且上行 chunk≈10 ms，"16 帧"只有 160 ms。
5. 武装判据只看 int16 裸 RMS>500，真正的语音证据是降噪器概率（`[voice-rnnoise] probability_peak=0.9995`）。
6. "0.5 s 不间断响度"人类做不到：真实提问录音里最长无间断段 0.08 s（原始）/0.07 s（降噪后），
   换切片口径 0.45 s → 窗口允许 0.15 s 换气缝。
7. **最贵的一层**：假麦夹具喂的是 48 kHz 满量程恒定音，RMS 判据在它身上成立（21 次静音）；
   原生路线经 `main_logic/voice_turn/audio_input.py` 降噪重采样后给 `stream_audio` 的是 **16 kHz / 512 样本**帧，
   `_transport.py` 用 `is_48khz = (num_samples == 480)` 猜采样率 → `_rnnoise_vad_live` 为假 → 退回 RMS →
   **真麦 13 分钟实测 `local speech onset` 0 行**（10-12 11:35–11:48 学习者场）。

**因此 §2.3 那些"21 次 / 66 个被挡增量 / 尾巴 1.55 s"只在夹具路径成立**，判定已两次下调，现为
**未证明 — Blocked (Automated Test Harness)**（`docs/LIVETUTOR_AUTOCHK_READINESS.md`）。

停播的实现层前提（学习者 10-13 00:45 指出、我核代码确认）：本地判定的锚点是**投递过的 provider delta / response id**，
补丁里就写着 `local speech onset (%s) with no response anchor: not muting - the route is …` 和
`local speech onset declined: %s`。→ **磁盘外放一段"老师的录音"不会产生 delta**，插话只会得到 declined。
这条直接决定了 §8 里"用现有录音"该走哪条路。

## 5. 未提交的 native handoff（这段是最新、也是文档最缺的一段）

### 5.1 它是什么

`scripts/neko_native_barge_in_patch.py`（484 行，未跟踪）由 `neko_voice_host_patch.py` 在启动时重放。
不再新建 VAD/播放器，而是**复用宿主自己的机制**：

- 归属边界 = **connection generation**（不是 provider response id）；
- 插话时把**旧连接的播放**定向退役：前端 `static/app/app-audio-playback.js` 的 `cancelNativeConnectionPlayback(correlationId)`，
  显式**不进**全局 `applyUserActivityCancel` 路径；
- 学员 PCM 进宿主现成的 `main_logic/voice_input.activation` 的 `BoundedAudioFrameBuffer` / `VoiceActivationConfig`
  （上限 8 s、pre-roll 0.3 s，取自宿主默认），代际轮换时标 `_native_barge_in_overflow` 而不是无限缓冲；
- 游戏语音保留原有 request ownership，不在本次改动范围。

### 5.2 补丁面从 4 个文件扩到 8 个

manifest `patches/neko-study-2026-10-10-host/manifest.json` 新增/重封：
`main_logic/core/session_lifecycle.py`、`main_logic/core/lifecycle.py`、`main_routers/websocket_router.py`、
`static/app/app-websocket.js`、`static/app/app-audio-playback.js`、`main_logic/core/tts_runtime.py`、
`asr_runtime.py`、`_transport.py`。

另外两处结构性改动，评审时值得单独看：
- `neko_voice_host_patch.py` 的 `TARGETS` 现在由 `upgrade_targets()` 在其上追加 owner-trace 与 native handoff 两类 hunk，
  且 `apply_to()` 先跑 `_OWNER_TRACE_REPLAY` 再跑常规 hunk；
- `neko_desktop_tutor_host.apply_voice_host_patch()` 改成 `HOSTS × TARGETS` 双循环（原来只打一个 `RELATIVE`），
  `neko_tutor_start.py` 把**"打补丁"挪到"验指纹 `verify_source_audio_gate()`"之前**——这是为了消灭
  `partial(4/5)` 那类"改了补丁没重部署就验闸"的不一致。

### 5.3 21:17 那次真机 FAIL 的原样记录（docs 里目前没有这段）

`manifest.json` 的 `native_barge_in_handoff.live_acceptance` 原文：
> Pre-fix human trial FAIL: onset raised AttributeError on LLMSessionManager.speech_id at 2026-10-12 21:17:33 NZDT,
> then generic close handling dropped later PCM. Corrected build requires future live acceptance; not run.

根因性质：**夹具发明了生产里没有的属性** `manager.speech_id`；生产契约是 `read_current_speech_id()`
（manifest 的 `owner_accessor_fix` 字段这样写，`scripts/test_neko_native_barge_in.py` 的夹具也按此重写）。

**一手记录是有的，是我先前搜错了关键词**（两份独立评审各找到一处，我复算确认**两份日志里都有这一行**）：

```
benchmarks/raw/neko-product-data/N.E.K.O/logs/N.E.K.O_Main_20261012.log:11321   ← 宿主应用自己的日志
benchmarks/raw/neko-desktop-host.log:29998                                      ← 启动器那份（我搜过的就是这份）
21:17:33 - N.E.K.O.Main.main_logic.core - WARNING -
    [YUI] Omni native microphone connection closed: 'LLMSessionManager' object has no attribute 'speech_id'
```

我先前只在启动器日志里搜 `AttributeError` 与 `Traceback` —— 两个词都必然搜不到：异常被 catch 之后
以**消息字符串**拼进了"连接关闭原因"这句 WARNING，既不含类名也不产生栈。
`grep -c 'has no attribute' benchmarks/raw/neko-desktop-host.log` = **1**，就是它。
全文件里这种"被吞掉的异常"形状只有 **1 行**。

**同一场 21:17 还顺手替我证掉了 P0 的一半**（这四行就在上面那条之前，L2）：

```
:11318 21:17:30  🔊 首个 audio.delta 已收到 (bytes=12696)            ← 老师当时确实在念
:11319 21:17:31  [barge-in-meter] frames=65 speaking=0 raw_loud=0     ← 真麦的帧到达了客户端（第 7 层已跨过）
:11320 21:17:33  [barge-in-owner] connection=1 dispatch_connection=1 dispatch_speech=98238597-…
:11321 21:17:33  …connection closed: 'LLMSessionManager' … no attribute 'speech_id'
```

→ 崩溃发生在 owner-trace **之后**、归属字段本身读得通；`frames>0` 这条判据在修前的真机场次里就已经成立过，
不必等下一次。P0 现在真正要证的只剩一件：**accessor 修好之后那条 close 不再发生**（判据写法见 §8）。

**这就是 P0 的最小靶**：这次崩溃发生在 onset 处理器**入口**（`_trace_local_playback_owner()` 在读归属字段），
不需要任何模型调用就会抛 → 复验它可以 0 DeepSeek。

### 5.4 我（10-13 00:30，宿主未启动、0 请求、0 CONNECT）实跑的结果 —— **其中一条不是离线测试**

```
benchmarks/raw/neko-product-host/.venv/Scripts/python.exe -B scripts/test_neko_realtime_barge_in.py  → Ran 19 tests OK
… -B scripts/test_neko_native_barge_in.py                                                          → Ran 12 tests OK
node scripts/test_neko_native_barge_in_playback.js                                                  → PASS: queued/playing old audio, late stop,
   same speech ID, arrayBuffer/decoder in flight, metadata pairing, reconnect, next reply
… -B scripts/test_neko_autocheck_readiness.py                                                       → Ran 13 tests, FAILED (failures=1)
   失败项 = test_the_gate_passes_right_now → ['budget_round_is_the_authorised_one_with_room_left']
```

**评审纠正、我复验成立的那一条**：前三条确实设备无关，**第四条不是离线测试**。
`scripts/test_neko_autocheck_readiness.py:156` 的 `setUpClass` 直接调 `autocheck.readiness(tap_seconds=1.0)`，
而 `scripts/neko_voice_autocheck.py:665 → :771 → :495` 会 `get_default_wasapi_loopback()` **真的打开系统回环设备**，
并把 wav 写进 `docs/evidence/audio-autocheck`（该目录 30 个文件里 22 个是 wav；
**23:46 那两份就是我这次跑出来的**，不是场景跑的）。它还依赖磁盘上的宿主日志（`:153` 没日志就 `SkipTest`）
→ 换机器或换轮次**不可复现**，"12 passed / 1 failed" 只是本机此刻的读数。
所以我不能把它计进"离线守卫绿"，正确说法是：**3 套设备无关的守卫绿，第 4 套需要回环设备 + 历史日志，此刻红在 budget。**

运行时树确实带着修后的 build（`grep` 命中且带 cpython-311 新 pyc）：
`isolating old native connection`→`_transport.py`；`_capture_native_barge_in_pcm`→`_transport.py`+`session_lifecycle.py`；
`read_current_speech_id`→`asr_runtime.py`/`lifecycle.py`/`turn.py`；`cancelNativeConnectionPlayback`→两个 JS。

## 6. 我核过的 / 我推断的 / 我不知道的

| 已核（可复算） | 推断 / 需要复核 | 不知道 |
|---|---|---|
| §2 全部 git 事实（`ls-remote`、`merge-tree`、逐文件 sha256 三方一致） | ~~"DeepSeek 见底 → 完整场景走不完"~~ **已被 §3 推翻**：纸面剩 270/6，红的只是被压低的上限 | 修后的 native handoff 在真麦上是否还会抛别的异常 —— **这是 P0 要回答的** |
| §3 cap 文件三份时间线（21:03 还原目标 / 20:06 blocked 证据 / 21:14 启动写下 30/8） | 21:17 崩溃的**消息与时间戳已归档**（§5.3 与 §12），缺的只有调用栈——异常被 catch 成一句 WARNING | 原生路线能否用 `--use-file-for-fake-audio-capture` 喂 wav 且**产出与真麦同形的 16 kHz RNNoise 帧**（`getUserMedia` 在 `static/app/app-audio-capture.js`，属 Electron 渲染进程 → 理论可行；第 7 层教训正是"帧形状不同"，未证明之前不许当产品路径） |
| 12/13 离线结果、`--readiness` 不在直启路径、运行时树带补丁的四处 grep + pyc 时间 | 自动场景 ≈4.7 CONNECT/场（由 28÷6 平均得出，非单场实测）；DeepSeek 21.6 次/分钟（11:35 那场实测，静置只有 3.5） | 聊天窗 UI 自己的历史裁剪参数（DELIVERY §10.5 标"待查"） |
| 无 PR、仓库 private、N.E.K.O 进程 0、宿主日志 mtime 21:20、磁盘上 66 份录音 wav | §5.2 里"apply 挪到 verify 之前"的意图是我读代码得到的，没问过写它的人 | 念题 0 帧（回合有文字无音频）归因，上游行为 |

### 6.1 §6 第三行那条"不知道"，我在 01:40 已经追掉了一半

原生麦的帧**确实来自 Electron 渲染进程的 `getUserMedia`**，Python 侧只是接收方：

- `static/app/app-audio-capture.js:1887` `socket.send(frame)` 把采集帧发出去；
- `main_routers/websocket_router.py:188` 的判据是 `action == "stream_data" and message.get("input_type") == "audio"`，
  并在 `:150` 把 `audio` 列进 `_SESSION_INPUT_TYPES`；
- 收到后进 `main_logic/voice_turn/audio_input.py` 做 RNNoise + 重采样，再进 `stream_audio`
  （这就是 §4 第 7 层描述的链路）。
- `main_logic` 里**没有任何 Python 侧话筒采集库**（pyaudio/sounddevice/WASAPI 直采都搜不到；
  `main_logic/asr_client/audio.py` 是缓冲/队列模块，不碰设备）。

→ 结论：**用 `--use-file-for-fake-audio-capture` 驱动那条 Electron 采集，替换的只是设备层**，
`getUserMedia` 之后的链路与真麦完全同一条。剩下未证明的只有一件事：
Chromium 把 wav 灌进 `getUserMedia` 之后，**降噪/重采样出来的帧形状是否仍是 512 样本 / 16 kHz 那一形**
（第 7 层骗过我的正是形状不同）。这一条 0 额度可测：假采集启动一次，读 `[barge-in-meter]` 的
`frames` 与单位即可判定 —— 判不出来就不许把假采集场当产品结论。

## 7. 评审 agent 必读的执行陷阱（每条都是真踩过的）

1. **`python scripts/neko_voice_host_patch.py` 默认会写运行时树**（argparse 只有 `--check` 是"report without writing"）。
   只想读代码的人最容易在这一条上把树改掉。
2. `--readiness` **会开 WASAPI 回环 2.5 s**（`readiness(tap_seconds=2.5)`），并往 `docs/evidence/audio-autocheck/` 落 wav。
   `docs/evidence/**/*.wav` 被 `.gitignore:22` 忽略 → **声学证据不入库**（该目录 30 个文件在盘上、只有 8 个被跟踪）。
   要带走的数必须自己变成 JSON/txt。
3. 仓库全局忽略 `*.log`：证据命名成 `.log` 会静默不入库。
4. `python scripts/neko_session_guard.py check` 用系统 Python 直接 `ModuleNotFoundError: psutil`，输出看着像"没有会话"其实根本没问成；
   用 `uv run --with psutil python scripts/neko_session_guard.py check`。
5. 离线测试请用宿主 venv：`benchmarks/raw/neko-product-host/.venv/Scripts/python.exe`（3.11）。
6. 枚举音频设备请用现成的 `scripts/neko_voice_autocheck.py --list`；`sounddevice` **没装**（我试了，ModuleNotFoundError）。
7. Windows 打印中文要 `PYTHONIOENCODING=utf-8`，否则 cp1252 崩。
8. 宿主日志里 `[voice-rnnoise]` 这类 logger **每秒写两遍**，按行数推时长会高估一倍；被计数的 5 个标记只出自"从不写 `,ms`"的 logger。
9. 未设 `_ai_recent_activity_time` 时宿主会打印 `nothing audible for 1791731783.6s` —— 那是 **epoch 不是时长**，读端按 `never_delivered` 分类。
10. 改了补丁文本但没重部署 → 运行时树 `partial(4/5)`，且 `apply_to` 无法自愈（`old` 已不在文件里会抛 "vendored code has moved"）。
11. **正则里没转义的 `.` 会把计数器吞进来**（我今天栽过）：`grep -c "audio.delta"` 在全天命中
    **783 处真事件 + 822 处 `audio_deltas=` 字段**，于是"9 行 audio.delta"这种读数可以整段是假的。
    统计事件一律写 `response\.audio\.delta`；跨含义的字段名（`audio_deltas` / `delta_counts`）分开数。
12. **`[barge-in-meter]` 自己的单位不可全信**：hour 15 的 275 个桶里有 **31 个 `rms_max > 32767`**（最大 **9,079,439**，
    远超 int16 量程），可同一小时里 `raw_loud>0` 只有 2 个桶 —— **这两个字段在那一小时互相矛盾**；
    hour 16/21 没有这现象（最大 2956 / 1921）。readiness 的 `meter_reports_int16_units` 只检查"最近 5 行 rms_max≤5"，
    所以**这种行存在时它照样绿**。判据建议改成"全窗口越量程计数 = 0"，
    任何拿 `raw_loud`/`rms_max` 做的推论都要先按小时切一遍。
13. **宿主日志有两份**（§5.3）：启动器写 `benchmarks/raw/neko-desktop-host.log`，
    宿主应用自己写 `benchmarks/raw/neko-product-data/N.E.K.O/logs/N.E.K.O_Main_<date>.log`。
    只搜其一会得出"没有记录"的错结论。

## 8. 下一步（学习者已定的顺序 + 我的具体建议）

**P0 · 最小真麦 smoke —— 两步式（13:2x 按并行评审的意见改掉）**
0 DeepSeek、**≤1 条 CONNECT**、需要学习者 **90 秒**。全程不碰 cap、不改补丁文本。

```
0. python scripts/neko_voice_host_patch.py --check     # 只读！2 根 × 10 目标 = 20 条路径
1. Start-Tutor.cmd --voice → 你点麦 → 先提问，等日志出现"首个 audio.delta"（老师真的在念）
2. 在它还在念的时候，连续说满 0.5 s
3. 抓日志判定；一次即停
```

**第 1 步不能省**：21:14–21:17 那五次 `onset declined: nothing audible` 证明——**不等老师在念就插话，
大概率只会复现 declined**，看起来像失败其实什么都没测（§13）。
`--check` 是启动前唯一覆盖"第二个根 + `_tools.py`"的护栏（指纹闸只看一个根、17 条，§11.5）。

判据**要按"被吞掉的形状"写，不能按 `Traceback` 写**（§5.3 那次在两份日志里都没有 Traceback、
也没有异常类名，只有一句拼进文案的 `no attribute`）：
① **主判据** = 宿主应用自己的当天日志 `neko-product-data/N.E.K.O/logs/N.E.K.O_Main_<date>.log` 里
**不出现** `Omni native microphone connection closed:` + `no attribute` / `handoff failed kind=`；
② `Traceback` 计数 = 0 只作辅助，**不许单独当通过**；
③ `local speech onset`（含 declined 句式）≥ 1；`[barge-in-owner]` ≥ 1；
④ `[barge-in-meter] frames>0`（21:17:31 已读到过 65，这条在**修前**场次里就成立，别再当新增证据）；
⑤ **时序前提（本轮新增，是这次改动的核心）**：那条非 declined 的 onset 行必须落在
「首个 `response\.audio\.delta` 之后、同 response 的 `response.done` 之前」。
不满足这个窗口的 onset **不算证到打断**，只能记成"判据又响了一次"；
⑥ onset 之后会话仍活着 —— 其后还能出现新的 `首个 audio.delta` 或转写行。
21:17 那次是 `:11321` 关掉连接、`:11322` 宿主自己写 "the host is already on a new turn … leaving it"，
所以"异常没了但连接被关掉"与"一切正常"，在两行之内就能分开。
**一次即停**：出异常就记 Blocked 并停止，不追第二次；**若只是 `declined`，那不算失败**，
按 §13 记成"窗口没对齐"，并把它当作⑤时序前提的一次负例留档。
对学习者两条承诺：(a) 若 ⑤ 成立，这 90 秒可能**第一次**拍到"落在正在念的回答上的 onset"（0 付费，§13.2）；
(b) 但 0 付费的音频很稀疏（9 行 / 8 分钟），够长的念读不一定出现——出现不了就记 Partial，不追第二轮。

**P0′ · 用现有录音/现成 trace 的回归（0 额度，40–60 分钟，可与 P0 并行）** —— "减少重复真人测试"的正确落点。
今天 01:20 我核了它到底能做到哪一步，**结论比想象的受限**：

- 可重放的是**事件骨架**：宿主日志里 `[wire-trace]` 的 JSON 只有
  `cid/dir/first_delta/gen/item_id/response_id/t/type`（实测 188 字符，**不含音频载荷**），
  共 612 行提到 `response.audio.delta`。真 id、真代际、真时序都在 → 足够驱动 native handoff 的归属与轮换逻辑。
- 音频载荷拿不回来（日志只记 `bytes=11760` 这种计数），得用合成帧或 `benchmarks/raw/voice-input/*.wav`
  （磁盘上 66 份，`barge-in-once.wav` 3.5 MB / `interrupt-chain.wav` 2.3 MB / `explain-then-quiz.wav` 14 MB）代填。
- 先例是现成的：`scripts/test_neko_turn_chain.py`（queue socket + 真实 `handle_messages()`，事件形状照线上抄）10 轮 0.34 s。
- 要验的两件事：native handoff 在事件层能走到 `[native-barge-in] handoff complete connection=A->B`；
  且 accessor 改动**没把停播逻辑改坏**（`local speech onset (%s): suppressing the rest of response=… deltas_delivered=…` 仍能出现）。
- **产物层级 = L2 夹具**，只当回归闸门，**不得写成产品 PASS**。
- 反面路线（磁盘外放"老师的回答"）会因 §4 末尾的锚点前提只得到 `declined` —— 它验不到停播本身，别指望它。

**P1 · 完整真人打断验收** —— **不缺授权，缺一次点头**：`docs/LIVETUTOR_REAL_MIC_FIX_PLAN.md` §1 已写明本轮 300/50/12，
已花 30 DeepSeek、6 CONNECT → **纸面剩 270 次 + 6 条 CONNECT**。按实测 21.6 次/分钟，270 次 ≈ **12 分钟讲话量**；
按 4.7 条/场，6 条 CONNECT ≈ **够开一场**（很紧，只有一次机会）。
要做的只是把 cap 文件的 `budgets` 从 30/8 恢复成 300/12
（还原文件 `benchmarks/raw/live-human-acceptance-restore.json` 里就是这两个数）。**我不自行改 cap。**

**P2 · Git 与文档收拾** —— 不合 `fix/…` 分支（冲突 5 处、内容已在 working tree）、不 push master（学习者已否决）。
本文件就是那条"补 docs"的交付；21:17 的异常原文已在两份日志中找到（§5.3），缺的是修后真人验收记录。

**本轮不做**：新 VAD、新 ASR、PlaybackCoordinator、新调度层、新监控、第二套消息系统、
**以及第 N+1 道闸门**（学习者 10-13 明确指示：尽量减少开发工作，把重点放在证明已完成的修复有效）。

**学习者的三条硬约束**：① 先解决真人语音链路再整理 Git；② 不许为了让 readiness 变绿**擅自**动预算
（§3 的"恢复已授权上限"与"自己加额度"是两件事，都要他点头）；③ L4 只有他能判，agent 不得自判通过。

## 9. 请评审回答的 6 个问题

1. §3 这条更正成立吗？如果成立，"上限被压低"与"授权用尽"这两种状态，readiness 闸门应该怎么区分上报？
2. §5.3 的原文已经找到（两份日志各一份副本），在这种情况下 P0 的判据要不要再收紧一步——
   具体说：**"onset 发生时老师正在念"这一条能不能也写成日志判据**，还是只能靠回环能量（L3）？
3. §8 的 P0′ 只能用事件骨架 + 代填音频，它的 L2 定位会被误读成产品结论吗？怎么写才照不出第二个"21 次"？
4. 用 `--use-file-for-fake-audio-capture` 驱动**原生路线**算不算走了产品同形路径？第 7 层的教训在这里适用吗？
5. `neko_tutor_start.py` 把 apply 挪到 `verify_source_audio_gate()` 之前（§5.2）—— 那道指纹闸还能不能发现"补丁与树不一致"？
6. 8 个文件的补丁面里，有没有哪一处本可以用更小的接缝做到（尤其 `lifecycle.py` / `websocket_router.py`）？

## 10. 复现命令（全部只读，除第 4 条）

```bash
# 1. 远端真实形状
git ls-remote origin
git merge-tree --write-tree --name-only master fix/neko-realtime-barge-in   # 只读模拟合并
# 2. 守卫套件（0 额度）—— 前 3 条设备无关；第 4 条**会打开 WASAPI 回环并写 wav**，别当只读检查
PY=benchmarks/raw/neko-product-host/.venv/Scripts/python.exe
$PY -B scripts/test_neko_realtime_barge_in.py
$PY -B scripts/test_neko_native_barge_in.py
node scripts/test_neko_native_barge_in_playback.js
$PY -B scripts/test_neko_autocheck_readiness.py        # 12/13，红在 budget 闸门
# 3. 额度与现场
cat benchmarks/raw/neko-desktop-egress-cap
uv run --with psutil python scripts/neko_session_guard.py check
# 4. 会写运行时树 —— 只想看状态请用 --check
$PY -B scripts/neko_voice_host_patch.py --check
```

## 11. 本文件被独立审阅过（10-13 02:10），审阅报告在仓库里

**先读 `docs/evidence/handoff-review-2026-10-13.md`**，再读本文。两个只读评审 agent 分头证伪、我逐条复算后
就地改了 6 处、新增 3 处、把 2 个数字降级。要点（细节与行号在审阅报告里）：

1. §5.3 我原本写"崩溃一手记录找不到"是**错的**：记录在
   `neko-product-data/N.E.K.O/logs/N.E.K.O_Main_20261012.log:11321`，而且**异常被吞成一句 WARNING**
   （全文 `AttributeError` 0 次、无 Traceback）→ P0 判据若只看 Traceback 会原地漏掉同类失败。
2. 那场 21:17 已经顺手证掉 `[barge-in-meter] frames=65`（真麦帧到达客户端）与 `[barge-in-owner]` 可读
   → 第 7 层"喂不到"在修后 build 上不再成立，**别把它当新的证据**。
3. §2 的"分支缺 8 个文件"**低估 16 倍**（实测 128 个 master 独有文件不在分支上）；
   且分支里启动器那 3 个文件比工作树**旧**，"远端=我跑绿的那份"只对补丁正文与用例成立。
4. §5.4 我把 `test_neko_autocheck_readiness.py` 叫作"离线"是**错的**：它 `setUpClass` 里真的打开 WASAPI 回环
   并往证据目录写 wav，还依赖本机历史日志 → 12/13 只是本机此刻读数。
5. 新增一条设计缺口（§5.2 那处改动的代价）：**指纹闸只覆盖 2 个根里的 1 个、10 个 TARGET 里的 9 个**
   （`_tools.py` 不在 manifest `files` 里，而它是卡死修复的落点）；apply 挪到 verify 之前 + 删掉 per-target
   `try/except` 之后，最坏形态变成"半打补丁 + 启动器中途崩溃"，比原来的 `partial(4/5)` 更难读。
6. 两个数字降级：`4.7 CONNECT/场` 来自**上一轮**（cap 100）的均值，本轮只花过 6 条；
   `21.6 次/分钟` 出处是一场**帽 80 被打满**的开场压缩期（80 个请求全是 200，重试没被计入），
   规划请按 **≈20 次/分钟 → 270 次 ≈ 13 分钟讲话量**。
7. 额度那条判定经复核**保留**：`budgets` 是上限不是授权余量（DELIVERY §4 的 `520/520` 是同形状的上一轮旧帽），
   300/50/12 的授权在 `LIVETUTOR_REAL_MIC_FIX_PLAN.md` §1 权威生效、§1b 是被取代的旧口径。

## 12. 第二份独立评审（`docs/LIVETUTOR_HANDOFF_REVIEW-2026-10-13.md`）带来的四处加硬

那份评审在我写 §11 的同时并行发生（12:2x），我逐条复算了它的承重引用，**三条成立且比我写得更好**：

1. **第 7 层从此有了定量现场**（原报告只有"13 分钟 0 行"这种间接说法）。启动器日志 21:17:31–32 连着三行：
   `[barge-in-meter] frames=65 raw_loud=0 rms_p50=0 rms_max=8 gate=500` 与
   `[voice-rnnoise] probability_peak=0.9989 / peak_ge_0_5_chunks=51`。
   → 真麦在同一时刻**同时**给出"降噪器判定有语音（0.9989）"和"裸 RMS 只有 8 / 门限 500"。
   这不光证明旧判据在真麦上永不满足，也证明**改概率判据的方向在真麦上是有信号的**——不是没数据。
   （同一窗口里还有 `probability_peak=0.0358 / peak_ge_0_5_chunks=0` 的静默秒，说明这条通道会回落，不是恒真。）
2. **P0 判据可以写成具体可证伪的断言**（不必停在"无异常"）：主判据加一条
   **`has no attribute 'speech_id'` 在当天两份宿主日志里出现 0 次**。我先前搜的是类名和 Traceback，那两个词必然搜不到。
3. **陷阱清单第 11 条**（它和我这边另一个评审 agent 独立得出同一条）：
   **`--egress-budget 300` 传参是静默无效的** —— `_load_ledger()`（`neko_desktop_tutor_host.py:516-523`）
   在 round 匹配时用 cap 文件的 `budgets` 覆盖启动参数，而本轮 round 没变。
   → 想恢复上限**只能编辑 cap 文件**；用传参重启会表现为"跑了但上限还是 30"，极易被误读成"授权没生效"。
4. **两处口径要收紧**（我复算同意）：
   - wire-trace 的原始行长度是 **173 字符**（`grep -o '{"dir":"recv".*first_delta[^}]*}' | 长度分布`：136 条=173），
     我 §8 写的"实测 188 字符"是 `json.dumps` 长度，两种口径别混用；
   - cap 文件里只有 `api.deepseek.com` / `www.lanlan.app` / `www.lanlan.tech` 三项，
     **`--api-budget 50` 在文件里没有对应项**（它是启动参数，`neko_tutor_start.py:405` 默认 30）
     → "恢复 300/12"覆盖不到那 50，执行时别以为三个授权数都还原了。

**采纳的顺序调整**（那份评审的论证，我复核后认为比原 §8 更好）：
**先别恢复 cap。** 因为 P0 是 0 DeepSeek、P0′ 是 0 额度，恢复上限在两者跑完之前**不解锁任何工作**；
而 budget 闸门此刻红着的实际作用是把"误开一场付费场"挡在外面——**在修后的接线被证明不崩之前，那道红是保险丝不是障碍**。
顺序应为：P0 → P0′ → 拿到绿灯 → 再为 P1 手改 cap（记住第 11 条：只能改文件）。

**P0 依赖学习者的一个前提**（原 §8 没写）：那场会**发声**（角色会念回答，宿主也可能自行播报），
而本项目长期红线是"agent 不得擅自发声"、且学习者在开放办公环境。
所以 P0 只能在他给定的时间窗里跑；它 ≤1 条 CONNECT，当前 `www.lanlan.app` 8/6 **剩 2 条够用**，
因此 **P0 不依赖 cap 恢复**，这两件事可以分开点头。

## 13. "判据没换"这个担心可以撤掉了（13:0x，我用现成日志把它证伪了）

并行评审的最后一节提出：修复只换了归属/停播机制、**武装判据没换**，所以 P0 可能出现
`frames>0` 但 `onset=0`，即"不崩，但也不打断"。**这条在代码和实测两边都不成立。**

**代码侧**：部署树 `main_logic/omni_realtime_client/_transport.py:1638-1643` 的武装判据是

```python
_speaking_now = (speech_active if speech_active is not None
                 else ((audio_processor.speech_probability > 0.4) if _rnnoise_vad_live else raw_loud))
```

调用方送进来的 `speech_active` 优先，而它由宿主自己的
`asr_runtime.py:4698 _voice_session_activation_has_speech(...)` 算出，函数体在
`rnnoise_available` 且有帧时把**概率当权威**（`:4705-4712`）——RMS 只是没有概率可用时的退路。

**实测侧**（hour 21 = 真人那场 21:14–21:18；只读重数，正则收紧成 `response\.audio\.delta`）：

| 计数 | 结果 |
|---|---|
| meter 桶总数 | **96 个** |
| `speaking>0`（新判据） | **64 个桶** |
| `raw_loud>0`（旧 RMS 判据，门限 `gate=500`） | **4 个桶**；该小时 `rms_max` 最大只有 1921 |
| `local speech onset declined:` | 该小时 **5 次**（21:14:43 / 21:15:26 / 21:15:48 / 21:16:38 / 21:17:12），句式全是 `nothing audible for …` |
| 进过停播/交接分支（`isolating old native connection` / `interrupting the answer in the speaker` / `suppressing the rest of response` / `with no response anchor`） | **0 次** |

全天 onset 共 **66 行 = 45 declined + 21 次非 declined**，而那 21 次**全部落在 04 点这一小时**，
且 04 点**一个 meter 桶都没有**（仪器是当天晚些才装的）→ 与 §4 第 7 层那批"夹具 21 次"完全吻合；
按并行评审的意见写成**疑似夹具**，不写"已证"。**真麦所在的 15/16/21 三个小时里 onset 尝试 16 次、成功 0 次。**

也就是说：新判据在真麦上确实在开火（64/96 桶），旧 RMS 判据几乎从不成立（4/96）——第 7 层被**正向**复现；
armed 窗口在线上走满过，但每一次 declined 的原因都是"当时没有东西在出声"，
唯一走到交接那步的 21:17:33 随即崩在 `speech_id`。

**这把 P0 的问题收窄成一件事**：不是"判据能不能响"（已答：能，L2），而是
**"onset 落在回答正在念的那一刻时，交接会不会再崩"**。由此：

1. 原 §8 的 P0（点麦说一句、0 DeepSeek）如果**不等老师在念就插话**，大概率只是复现 declined ——
   看起来像失败，其实什么都没测。脚本已改成两步式，见 §8。
2. **我上一轮写在这里的"便宜路已关闭"是错的，撤回。** 错因是一个没转义的 `.`：
   我 grep `audio.delta` 时它同时匹配了全天 **822 处 `audio_deltas=`**，于是得出"9 行全在见底边界"的假象。
   收紧正则后按窗口重数（DeepSeek 于 11:39:47 见底）：

   | 窗口 | `response.audio.delta` 行数 |
   |---|---|
   | 11:35:00–11:39:46（见底前） | 13 |
   | 11:39:47–11:40:04（边界） | **1** |
   | 11:40:05–11:48:01（见底后） | **9** |

   → **0 次付费请求时教师语音仍会到达**：那条路走免费 realtime 代理，不经过 DeepSeek 计数器。
   并行评审这条成立。**但分寸要留着**：9 行摊在 8 分钟里，比见底前（13 行 / 4.8 分钟）还稀疏，
   所以"0 付费能出声"**不等于**"0 付费能有一段够长的念读供打断"——P0 可能只遇到短促间歇的音频。
   这条只能等真跑一次才知道，不许提前当已证。
3. 顺序再改一次：**恢复 cap 不再是"看到 onset"的前提**，它只在需要*教学内容*（真正的讲解回答而非兜底播报）
   时才有消费者。新顺序：两步式 P0（0 DeepSeek、≤1 CONNECT）→ P0′（0 额度）→ 出结果之后再谈 P1 与恢复 cap。

**给下一个 agent 的一句话**：两个已被排除的假设别再捡回来——"判据没换"与"0 付费听不到任何声音"；
真正没证的只有一件：**落在正在念的回答上的那一次 onset，交接会不会再崩**。

