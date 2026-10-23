# 2026-10-13 静默录音内存检查：回退判据 + mock handoff

**结论：离线能量回退 + mock handoff PASS；整体 PARTIAL，真实 barge-in UNVERIFIED。**
P0-1 产品验收状态保持“未证明”。本记录整理本会话已返回的执行结果；整理时只读核对源码、文档与账本，没有重跑。

## 1. 输入与记录来源

- 输入仅为项目内 `benchmarks/raw/voice-input/interrupt-short.wav`：403,278 bytes，RIFF/WAVE、无压缩 PCM16、48,000 Hz、单声道、201,600 样本、4.2 s。
- SHA256（此前头信息读取与成功检查的 stdout 一致，本次未重新计算）：

  ```text
  58f935fdcc41b1363c36a541d3fd93b47f29dd4cdb9e49825c669f74a06f9115
  ```

- 该文件是用户提供背景中指出的派生语音片段，不是已核验的原始录音；原始文件、派生步骤和作者未独立确认。文件名、mtime 或 WAV 头不能证明作者和录音来源。
- 结果来源是本会话工具返回的 stdout JSON/异常文本，没有独立落盘的原始输出、运行时日志或可执行夹具。本 Markdown 是后补记录。
- **复现状态：无持久化可执行程序，不能精确重放；下列只是命令形状，不是可复制的测试配方。** `$silentCheck`、`$headerRead` 是当时 PowerShell 内存中的代码字符串，未保存为项目脚本：

  ```powershell
  & 'D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-product-host\.venv\Scripts\python.exe' -I -S -B -c $silentCheck
  & 'D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-product-host\.venv\Scripts\python.exe' -I -S -B -c $headerRead
  ```

## 2. 做了什么、实际观察到什么

1. 首次夹具选错 `stream_audio` 内的 AST `if` 块，执行到 PCM 缓冲入口，报 `Client` 缺少 `_capture_native_barge_in_pcm`。这是夹具不完整，**不是产品故障证据**；尚未执行目标持续语音块和 handoff。
2. 只读头信息读取确认上述容器、PCM 参数及 SHA256。
3. 用户随后明确允许最多一次追加尝试；只修正内存 AST 选择，定位生产 `_transport.py:1624` 的持续语音块，第二次成功。没有修改生产源码或新增脚本。

| 环节 | 成功尝试的观察 | 范围 |
|---|---|---|
| 16 kHz 输入代理 | 每三点取一点；131 个完整帧，每帧 512 PCM16 样本 / 32 ms；末尾 128 样本未纳入 | **不是生产 soxr 重采样，也没有 RNNoise** |
| 宿主能量回退 | RMS 阈值 262.144；44/131 帧为活动；RMS 最小 0、最大 6878.582 | 执行生产函数，显式传 `speech_probability=None, rnnoise_available=False` |
| 持续语音时间窗 | 持续阈值 0.5 s、允许间隙 0.15 s；首次触发帧为录音时间 3.232–3.264 s | 使用样本时间轴，未按实时速度播放或输入设备 |
| accessor | Manager 故意没有 `speech_id`，生产 `read_current_speech_id()` 正常返回 | 没有复现旧 AttributeError；不等于完整生产 Manager 已验收 |
| 内存 handoff | generation 1→2、一次 mock reconnect、针对旧连接的取消消息 | 生产 handoff 函数 + 受控替身；没有真实连接 |
| PCM 保持 | 所提供 131 帧 / 134,144 bytes 重放后逐字节一致 | 全片段预装入 mock buffer；未验证生产有界缓冲、pre-roll、实时尾帧并发 |

**判据必须分清：** `core/asr_runtime.py:4698–4720` 的 `_voice_session_activation_has_speech` 在概率可用时优先采用 `>=0.5`；本次只执行其能量回退 `energy >= (0.008*32768)^2`。它不是传输层旧 `raw_loud` 的 RMS>500 判据。本次算出的布尔值作为 `speech_active` 送入抽取的时间窗，**没有强设 True，也没有证明真实麦克风 RNNoise/speech_active 语义**。

本次只读核对的其他源码接缝：`_transport.py:1638–1658` 优先采用 `speech_active`；`core/turn.py:110–123` 提供 accessor；`core/asr_runtime.py:4411/4440` 提供 handoff 两函数（可重放补丁对应 `scripts/neko_native_barge_in_patch.py:71–172`）。函数引用没有冻结整棵宿主树的哈希。

以下是**内存 logger 的 stdout 文本**，不是 N.E.K.O 实际运行时日志：

```text
local speech onset (speech-sustained): isolating old native connection
[native-barge-in] handoff complete connection=1->2
```

## 3. 静默与零网络边界

- 执行仅用标准库读取指定 WAV 和三个源码文件；AST 抽取函数，不导入 N.E.K.O/配置管理器，不运行整套 Python 测试。
- 没有创建 GUI、宿主、真实事件循环、provider session 或音频输入/输出设备；没有调用播放、TTS、WASAPI、loopback 或音量/静音接口。OS mute 不是防线。
- `asyncio` 名称绑定到内存替身；`close/connect/stream_audio`、输出 socket、buffer 和播放活动状态均为受控 mock。真实网络/API/CONNECT 为 0。
- 成功尝试的 Python audit 记录为 4 次允许的只读文件打开、0 次禁止操作尝试；禁止 socket、子进程、ctypes、环境修改和文件写操作。
- 内联执行未写报告、脚本或音频文件。这里不据此断言全部 ignored 文件从未变化，也不保证其他系统应用没有发声。

## 4. 证据层级与未覆盖部分

- **L2 夹具 PASS：** 派生录音经抽样代理触发生产能量回退/时间窗；生产 handoff 核心控制流程可读 accessor、发旧 owner 取消消息并保持所提供 PCM。
- **UNVERIFIED：** 生产 RNNoise/soxr、真实 ASR/provider 识别、实际连接代际建立/重连、监听器取消竞态、前端解码/播放取消及新回答存活。本次没有执行前端 JS。
- **L3/L4 未测：** 没有系统回环能量或播放尾巴数据，也没有人耳确认；不能据此宣布真实旧语音已停止。
- 历史 realtime 19/19、native 12/12、JS PASS 与指纹结果仍属于先前各自范围的证据，本次未重跑。
- 另一路 Oct13 静默 GUI 尝试的 `--check 20/20`、三个 fake-capture 参数、`micRect=[1111,591,48,48]` 与 driver 0×0 冲突、0 CONNECT，**本次未核实为一套可归因证据**。已有当天壳日志与单条 `agent_connectivity_probe_blocked` 记录不足以确认这些说法；不计入本次 PASS。

## 5. 给下一位 agent：旧文档的执行边界与最小下一步

- 21:17 崩溃原文已找到：`benchmarks/raw/neko-desktop-host.log:29998`，以及应用日志 `N.E.K.O_Main_20261012.log:11321`；它被 catch 成 WARNING，不必继续寻找，也不能只搜 `Traceback`。
- `--readiness` / `test_neko_autocheck_readiness.py` 不是纯离线只读检查：会打开 WASAPI 回环、写 WAV，并依赖历史日志。Python native 测试的项目模块导入还会初始化配置管理器，不能因有 `-B` 就保证零写入。旧文档“全部只读/全部离线”标题不是当前安全配方。
- 本次整理时只读账本：round=`bargein-autocheck-20261012`；DeepSeek 30/30、Lanlan app 6/8、tech 上限 0。FIX_PLAN §1 的 300/50/12 是书面授权上限，**没有自动扩大当前 cap**。同轮 `_load_ledger()` 使用文件上限覆盖 CLI（`neko_desktop_tutor_host.py:516–524`）。
- 将来获准启动时必须显式指定现有 `--budget-round`、`--egress-budget`、`--api-budget`、`--voice-connects` 和允许的语音 host，并核对实际账本；不能照抄裸 `Start-Tutor.cmd --voice`。未指定 round 会生成当天轮次（host `:770`），启动器默认付费上限是 200、每 host CONNECT 上限 20（`neko_tutor_start.py:408/422`）。不得重置 spent 或换轮次绕过限制。
- 初始连接加 handoff 替换连接理想情况下**至少 2 条 CONNECT**，重试可能更多；旧“≤1 CONNECT”不覆盖完整交接。当前两条余量没有重试空间，必须按当场读数决定能否进行，不能预先保证够用。DeepSeek 触顶也不必然阻止 realtime 音频；历史 21:17 场次记录 17 个 audio delta，不等于仍有正确教学内容。
- 用户能说话并允许出声后，只做一次有界真人麦克风验证：先等真实回答音频，再插话；检查真实 owner/onset、handoff、新回答与账本增量，L4 留给用户。异常即停；窗口没对齐记 PARTIAL。当前图书馆约束下不启动在线 WAV 或 GUI 场次，不新增 harness。
