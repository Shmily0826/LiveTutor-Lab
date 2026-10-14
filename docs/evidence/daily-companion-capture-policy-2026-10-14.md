# Output-only 页面捕获拒绝 bootstrap

日期：2026-10-14。承接完整 contract 和 plan/status/blockers 当前阶段十记录。最新授权允许必要约4%扬声器，不允许房间/物理/虚拟捕获设备和回环；本轮仅纯 Node 假环境，没有使用扬声器或任何设备。Main 记录额度594/2000、app56/null、tech0/0，本轮未直接查询/调整账本。Goal 继续，不因本模块交付认领完成。

## 独占交付

仅新增 `scripts/neko_capture_policy.js`、`scripts/test_neko_capture_policy.mjs` 和本报告；不修改真实前端、host、模板、manifest、共享记录或普通用户配置。已有 Node v24.15.0，无安装依赖、浏览器、服务、模型调用、设备初始化或新 Agent。

JS 是普通同步 bootstrap 脚本，不需 module import/bundler。只加载脚本时暴露冻结的 `globalThis.NekoCapturePolicy`；**不自动设置安全标志，不自动安装**。只有参数 `enabled === true` 才尝试 output-only 安装；缺省/false/字符串 true/数字1均返回 disabled receipt，不改捕获API。

显式调用：

```javascript
const receipt = globalThis.NekoCapturePolicy.installOutputOnly({enabled: true});
if (receipt.status !== 'installed' || receipt.captureBlocked !== true ||
    globalThis.NekoCapturePolicy.getResult() !== receipt ||
    globalThis.__NEKO_OUTPUT_ONLY_CAPTURE_BLOCKED__ !== true) {
    throw new Error('Output-only capture protection is not installed');
}
// Only now load/execute the application's other scripts.
```

Main 必须把该检查放在**实际最早模板 bootstrap**，在任何 app 脚本、权限询问、输入设备枚举或捕获函数引用缓存之前。成功是上述 installer 返回与本模块 receipt，不是仅看一个可能已存在的全局 true。不能只插入一份会 throw 的 script 后继续加载不受条件控制的其他 script：浏览器对独立后续 script 仍会执行。

## API 行为

| API/状态 | 安装成功后的行为 |
| --- | --- |
| `navigator.mediaDevices.getUserMedia` | 任意约束均返回 rejected Promise，DOMException.name=NotAllowedError；音频、摄像头以及空约束均拒绝。 |
| `navigator.mediaDevices.getDisplayMedia` | 同上，拒绝屏幕/系统音频捕获。 |
| `navigator.mediaDevices.enumerateDevices` | 同上，完全拒绝设备枚举，不返回虚拟设备，也不调用原实现。 |
| `navigator.getUserMedia/webkitGetUserMedia/mozGetUserMedia` | 仅异步调用 error callback；success callback 不执行。缺 error callback 时同步抛 NotAllowedError。 |
| 上述缺少的方法但 mediaDevices 存在 | 安装不可覆盖的拒绝桩，防止后续赋值/原型新增实现恢复常规 API 入口。 |
| navigator 或 mediaDevices 对象缺失、DOMException 缺失 | 明确安装失败，抛 `NEKO_CAPTURE_POLICY_INSTALL_FAILED`；receipt.status=failed、captureBlocked=false，不伪装成功。 |
| 本对象不可改写 descriptor、冻结/不可扩展目标、已有 policy marker | 同上，preflight 在任何捕获方法变更前拒绝。可写但不可配置的数据属性保留原 enumerable 后可以替换并锁定。 |
| late host-object defineProperty 拒绝 | 抛明确失败；已安装的拒绝桩不恢复为真API，partial receipt 给出已锁入口，Main 必须停止 app bootstrap。 |
| AudioContext、webkitAudioContext、Audio、HTMLMediaElement.play、speechSynthesis、mediaDevices.selectAudioOutput | 本模块不改、不调用、不构造。输出播放是否实际工作由 Main 后续设备验收证明。 |

每个受保护方法为 own readonly/nonconfigurable property；同时锁定该 realm 的 `navigator` 及 `navigator.mediaDevices` 引用，避免常规替换恢复捕获。成功最后才设置 readonly/nonconfigurable `__NEKO_OUTPUT_ONLY_CAPTURE_BLOCKED__=true`；另有冻结 `__NEKO_CAPTURE_POLICY_RESULT__` receipt 与 closure-owned `getResult()`。安装幂等，成功后不可撤销；失败为终态，重复启用继续抛错，不能靠再次尝试绕过部分失败。普通环境恢复通过新的未启用页面实现，不全局持久修改浏览器。

不可改写的真 API 冲突无法仅用 JS 把该真 API 变成不可调用：本模块对此**没有宣称硬拦成功**，而是明确失败并要求启动器不放行应用。在所有入口实际锁定之前不允许 Main 初始化输入/输出宿主。

## 已执行的离线证据

命令：`node --test scripts/test_neko_capture_policy.mjs`。纯 `node:vm`、fake navigator 与 DOMException，无 browser/PortAudio/WebAudio 初始化。13 tests PASS；增强输出调用计数后 `node --test --test-name-pattern 'output' scripts/test_neko_capture_policy.mjs` 输出相关1项定向复核 PASS。

- 未 opt-in 不设置安全状态、不改真实方法；所有现代约束与 legacy 成功/失败回调语义；原捕获实现调用计数为0；
- readonly flag/API/reference、冻结 receipt、重复安装；缺少方法的 late prototype 实现仍不经常规入口调用；
- navigator/mediaDevices/DOMException 缺失，readonly descriptor、不可配置 accessor、冻结目标、policy marker 冲突明确拒绝；
- non-configurable 但 writable 方法正确覆盖；Proxy late define 失败不声称成功、不恢复已拦方法；
- 输出API精确引用保留，模块加载/安装不构造或调用输出假实现。

这是**源码/纯 Node 离线 PASS**。真实最早模板注入、浏览器 host-object descriptor 可适配性、应用实际跳过 capture、后端捕获权限、Native 启动、固定 WAV 内存/WS输入、模型、实际输出播放、音量与真人体验均未在本轮执行。

## Main 接续边界

本模块只保护当前 JS realm 的常规 navigator API；不取消已经开始的 MediaStream，不撤销安装前保存的 bound 原函数，也不自动覆盖 iframe/worker/其他窗口、直接原型调用、Electron/preload/本地设备SDK等旁路。不是恶意 JS 的安全沙箱或系统设备权限替代品。最早注入和后端权限/实际 capture skip 均需 Main 独立实现。任何新增 realm 也要先完成相同安装并被启动器核实；不能用旧普通 fake-device probe 推导无捕获。

安装阶段对 navigator/mediaDevices 的属性读取只获取待保护对象，不调用 capture/enumerate/output 实现；属性 getter 自身异常会安装失败。Main 需在实际浏览器仅检查 descriptor/拒绝结果，不能为“验证拒绝”先触发原权限API。拒绝摄像头是此次无捕获测试路径的统一策略，不改变普通用户环境的功能契约。

冻结：三文件交 Main；本 Agent 不注入真实模板、不修改后端或启动任何设备。
