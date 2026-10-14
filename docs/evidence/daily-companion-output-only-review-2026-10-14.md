# Output-only 启动前窄审

日期：2026-10-14。复用本 Goal 已读 contract/plan/status/blockers 与最新授权：必要扬声器约4%，不调音量，不允许任何物理/虚拟麦克风捕获，不回环。当前 Main 记录594/56/0；本轮没有账本操作。唯一写入为本报告，未运行测试、设备、浏览器、服务、API、模型或 Native，没有派 Agent。

范围：`scripts/neko_output_only_runtime.py`、`neko_output_only_patch.py`、`neko_desktop_tutor_host.py` 新权限/启动分支、`neko_native_shell.py` output-only/fresh userdata、`neko_daily_voice_probe.py` output-only 分支及现 capture policy 构造器增量。没有扩大到全部外部语言、Electron/OS 或源码全仓。

## 发现

**P2：bootstrap 内容与声明 SHA 不是同一文件快照。** `neko_output_only_runtime.py:47–48` 用 `asset.read_text()` 获取 library，再用 `asset.read_bytes()` 获取 header fingerprint。若两次读取之间发生资源更新，宿主可缓存旧 library、却声明新 SHA；`neko_native_shell.py:154–161` 根据新的源文件 SHA 放行，实际页可能仍执行旧 capture policy（例如更新前没有 SpeechRecognition 拒绝）。这是可确定的文件更新竞态，不是声称本次实际出现设备捕获。

最小修法：读取一次 `blob=asset.read_bytes()`，`library=blob.decode('utf-8')` 与 `fingerprint=hashlib.sha256(blob).hexdigest()` 均来自该 blob；不要通过放宽 Native SHA 检查绕过。建议离线模拟第二次文件读取返回不同版本来验证只读一次。本报告首版此项待 Main 修复，修复后可以冻结其余当前结论。

除此项，本次限定源码没有发现可具体复现的新启动阻断。下面是已读源码确认与尚未执行层的区分。

## 安装失败不会继续启动原应用

`protected_html` 把完整原 HTML JSON 编码为字符串，转义 `<`/`>`，policy library 内出现 `</script` 即拒绝。原 HTML 在 receipt.status=installed、captureBlocked=true、closure getResult 同对象及 readonly success flag 检查前不进入 DOM；只有成功才 `document.open/write/close`。失败分支只显示拒绝信息/title/dataset，原 script tags 仍是 inert 字符串，修复了“独立第一份 script 抛错，后续 app tags 仍执行”的问题。

middleware 只在 `NEKO_OUTPUT_ONLY=1` 安装，所有响应附 microphone/camera/display-capture 拒绝 Permissions-Policy；HTML 增加 no-store 与脚本指纹。非 identity 编码、超过2MB、解码/封装异常返回503纯文本，不退回原应用 HTML。库读取失败在安装阶段直接抛错，没有无保护兜底。浏览器是否支持每一 Permissions-Policy 指令不能单凭 header 认领；页面拒绝桩是另一层独立防线。

capture policy 当前明确覆盖现代 getUserMedia/getDisplayMedia/enumerateDevices、旧 navigator/webkit/moz getUserMedia，以及 `SpeechRecognition/webkitSpeechRecognition` constructor。最后两项直接抛 NotAllowedError，不能因为独立语音识别不走 getUserMedia 就被遗漏。AudioContext/HTML output APIs 保持原样。Main 已报告 Node14 PASS，本轮仅源码核其构造器锁定，不独立重跑或外推设备。

## Native 预检与旧缓存

`neko_native_shell.py:170–176` 先检查独立 speaker permission，output-only 传任何非 None audio_input 都拒绝；随后在 EXE 检查、配置写入与 Popen 前完成 HTTP host bootstrap 预检。预检核 status200、output-only header、当前脚本 SHA、microphone policy 和明确 installer 调用字符串；它是内容/模式预检，不能替代实际 renderer 安装结果。

`185–189` 为每次 output-only 生成 UUID userdata，并将路径同时用于 surface config 和 shell_environment 的 NEKO_USER_DATA_DIR；不复用原 electron-userdata 缓存/权限。配置明确 apiBaseUrl 为当前本地source host。当前 FLAGS 只有原 GPU/sandbox flags，output-only 仅增 autoplay；fake-audio/file/device/UI capture flags 仅在 audio_input truthy 分支，而 output-only 已拒绝所有非 None 输入，因此此次路径没有 fake capture flags。

这是配置和传参源码确认；实际 Native binary 是否完整遵循 userdata/env、其他窗口是否同样收到保护须由 Main 一次实际启动确认，不凭 UUID 路径存在当浏览器缓存隔离设备证据。对普通路径仍保留原 userdata 与原 flags，未默认启用 output-only。

## speaker 权限不等于 capture 权限

`neko_desktop_tutor_host.py:98–109` 要求明确 speaker_output_allowed=true、microphone_allowed=false、capture_devices_allowed=false，并拒绝 NEKO_TASK_SILENT=1 或缺失/畸形配置。没有将旧 audio_allowed 全局变为 true。host CLI output-only 要求 source host；其 speaker guard 在读取凭据/patch/启动宿主前，旧 voice/packaged 分支继续经过原 mixed-audio guard。

source 启动通过 exact base SHA/anchor patch 输出-only middleware 和三处实际 capture skip；unknown 源码拒绝，未用“有marker就放行”替代完整已知源码判据。新 helper/JS 被复制进两source树；是否所有 manifest/fingerprint 当前匹配归 Main 的部署测试，不能由本次读源码替代。env 明确 NEKO_OUTPUT_ONLY 为1或0，不依赖上次环境残留自动启用。

## probe 的启动顺序和 meter

`neko_daily_voice_probe.py:95–99` 第一动作根据 output-only 选择 speaker guard。该分支向host传 --source/--voice/--output-only，同时 Native launch 的 audio_input=None。`244` 不生成 fake silent WAV；现有固定 WAV 仍按原内存/WS路径发送，不是虚拟捕获设备。

`276–300` 在 output-only 下先 launch renderer、attach telemetry、检查 capture policy receipt/flag/getUserMedia readonly，再发送显式 start_session；旧非 output-only 顺序保持。controller websocket 可能已连接，但这不等于已发 provider start_session；本次源码只确认显式 start_session 位于 renderer检查之后，不宣称 OS/App 没有其他未审查自动路径。

`360–363` meter Popen 只在 not output_only；`486+` 仅 meter 非 None 才 communicate/read capture，所以output-only不存在隐式回环 fallback。未在 imports 中看到 PortAudio/捕获设备库；numpy/soxr/wave 用于已有离线WAV格式处理，并不由本脚本构造输入设备。所有旧 mixed/loopback入口仍应受现任务 policy拒绝，不能在必要场失败后悄悄回退普通fake-device probe。

receipt 检查是新安装确认，主线实际场还需保存 Native renderer boot evidence、readonly方法/拒绝结果、原app readiness、实际 PCM/playback events。未用回环时，provider PCM与前端播放状态不等于扬声器物理声音幅度或真人听感；本报告不认领实际设备/human通过。

## 证据层与下一步

Main 报告的实际 ASGI+权限/旧静音9PASS、Node14PASS、global web-inspector Chrome成功/失败 bootstrap DOM/title/截图是 Main 实测，本 Agent 没有重跑。该 Chrome bootstrap结果不能自动替代新的 Native页面、provider或实际设备层。

先修复双读快照P2并保持同SHA严格预检，再按 Main 已限定的一次原0.9s单句WAV场执行。若 Native renderer 安装失败或provider拒绝，保留证据停止该场，不用旧fake flags、不启动meter、不重试绕过捕获策略。默认phrase OFF；实验比较provider分片/工具/尾约束与延迟须标实际观测，不能用此次静态审查或既有离线20项认领自然停顿已解决。

冻结范围：除本报告外无源码/测试/manifest/配置/账本改动。发现已消息交 Main；如 Main 修复，最多追加该精确修复确认，不扩大重扫。

## P2 关闭确认（精确复核）

Main 已修复。本 Agent 再次只读 `neko_output_only_runtime.py:47–49`，确认一次 `blob=asset.read_bytes()`，library decode 和 SHA256 均使用同一个 blob，不再有两次读取的内容/指纹版本窗口。原发现与当时待修记录保留；当前该 P2 **SOURCE REVIEW CLOSED**。

Main 报告 actual ASGI 单快照回归6项通过，记录于 raw `daily-phase11-output-snapshot6.log`，gate-sync PASS；本 Agent 未读取/重跑该测试，将其明确归 Main 的离线证据，不扩为模型、Native、设备或human通过。本轮无服务/API/浏览器/设备/额度操作，未扩大其他源码审查。报告再次冻结，限定范围无剩余已知具体阻断。
