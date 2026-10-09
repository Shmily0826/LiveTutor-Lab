# 2026-10-09 第五轮：显式目标窗口采集闸门（target_window）

一个文件：`entry_ocr_entries.py`。已同步到运行树的两处副本，尚未 commit、尚未 push。
验收与实测见 `../../docs/neko-safe-screen-desktop-tutor-2026-10-09.md`。

## 为什么要改

原来的 `active_window` 采集模式解析的是**当前前台窗口**。在真实桌面上前台是谁并没有任何保证，
上一轮就出过一次事故：一次采集把用户自己的“另存为/文件资源管理器”窗口截了进去，OCR 文本
被发给了模型一次。当时只能在**调用方**做事后过滤（识别到课文行不够、或看到外部窗口关键词就丢弃），
闸门在脚本里，不在产品里。

`target_window` 把闸门搬到插件内部，语义是**只允许截你点名的那个窗口，任何一点不符就拒绝**：

1. 必须显式给 `window_title`；没给 → `TARGET_WINDOW_REFUSED: expected_markers are required`。
   没给预期文本时**一个像素都不读**，因为无法证明截到的就是学习材料。
2. `allow_fullscreen_fallback` 在本模式里被强制为 `False`：目标窗口解析失败/截不到，
   直接返回 Err，绝不退化成全屏或另一个前台窗口。
3. 目标窗口必须是**当前前台窗口**（`FindWindowW` 精确标题 + `IsWindowVisible` + 非最小化 +
   `GetForegroundWindow() == hwnd`）。窗口存在但被压住时不做“隔着一层截屏”，因为那会把盖在它
   上面的内容截进去。
4. 采集之后**再复核一次前台身份**（`target_lost_foreground`）：从取标题到真正抓帧之间窗口可能被切走。
5. OCR 文本必须命中 `expected_markers`（空白/大小写归一后计数，阈值 `min_marker_matches`）；
   不命中 → `TARGET_WINDOW_CONTENT_MISMATCH`，并且**不回传文本、不写 `last_ocr_text`、
   不进任何分类/监督状态**（Err 在 `build_ocr_payload` 与状态写入之前返回）。
6. 取帧只按目标矩形向 PIL 请求（`ImageGrab.grab(bbox=…)`），打包运行时若无
   `ImageGrab.ScreenSize` 才退回「整屏取一次再裁」这条老路；离线用例把这一点钉住了：
   `grabs` 必须只有一个元素且带 bbox，否则测试失败。
7. 成功时才回传：`capture_mode_used=target_window`、`capture_target_title`、
   `active_window_capture_route`、`target_window_markers_matched`。

拒绝原因（`_named_window_target` 返回）：`target_window_title_required`、`target_window_not_found`、
`target_window_title_mismatch`、`target_window_not_foreground`、`target_window_geometry_unusable`。
宿主会把插件 `SdkError.code` 吃掉只留 message（`{"code":"INTERNAL","message":"…: TARGET_WINDOW_REFUSED: …"}`），
所以拒绝码写在 message 里，穿过任何传输层都还在。

旧的 `active_window` 保留不动（隔离夹具与既有用例依赖它），但函数文档里明确写了它是“截前台”的遗留解析器，
真实桌面产品路径应使用 `target_window`。本次没删任何东西，也没加新的框架/Router。

## 文件

| 文件 | 内容 |
|---|---|
| `target-window-capture.patch` | 13 个 hunk，16221 字节 |
| `_pre/entry_ocr_entries.py` | 改动前镜像，与 v02 overlay `payload/live/entry_ocr_entries.py` 逐字节一致（仅行尾为 LF） |

指纹（SHA-256）：

| 对象 | 值 |
|---|---|
| `_pre/entry_ocr_entries.py`（LF，20297 B） | `35097243f91d9765a2c861557878325aa0066b351d3fc092f09a1a9889d8cb2f` |
| overlay 原始快照（CRLF，20760 B） | `6af915f1e666938ab490486dbabe526d03c7b4a9eeedf6741294aa3e97ce5321` |
| 运行树 `plugins/` 与 `plugin/plugins/`（CRLF，29011 B） | `2acbb77ba258f35c1c24d8cb3beaffd40302b1930ad948a28e048cc1d141a655` |
| 同一内容的 LF 形式（28361 B） | `0061263b20dcde9e…`（重建核对用） |

两份部署副本已核对为逐字节相同（同一个 sha）。

## 如何重建

和上一轮一样，补丁与 pre-image 在仓库里是 LF，运行树是 CRLF：

```bash
mkdir -p rebuild/plugin/plugins/study_companion
git show HEAD:patches/neko-study-2026-10-09-target-window/_pre/entry_ocr_entries.py \
  > rebuild/plugin/plugins/study_companion/entry_ocr_entries.py
git show HEAD:patches/neko-study-2026-10-09-target-window/target-window-capture.patch > tw.patch
cd rebuild && git -c core.autocrlf=false apply ../tw.patch
```

本轮实测：重建结果与运行树的 LF 规范化内容**逐字节相同**
（`b0cac247577a754f…`），再做 `\n → \r\n` 后与部署文件逐字节相同。
先按 overlay 核对目标指纹，不要直接覆盖别人的在制改动。

## 验证（全部离线或本地，无额外付费调用）

- `python -I -S -B scripts/test_neko_lab_regressions.py` → 39/39 OK，其中新增
  `test_target_window_refuses_unverified_capture_and_never_grabs_desktop`（打桩 Win32 解析器，
  断言五种拒绝原因都不触发任何截屏、前台在抓帧后变化时不回传文本也不写状态、命中阈值才成功）。
  用 `-I -S` 是有意的：这会让 PIL 不可用，测试里不可能真的抓屏。
- `scripts/neko_target_window_guard_check.py` → `PASS_TARGET_WINDOW_GUARD` 10/10，
  `pixels_captured: 0`：拿真实 tkinter 窗口跑真实 Win32 解析，验证精确标题、前台身份、被压住的窗口被拒绝、
  `N.E.K.O` 自身界面不可作为目标、裁剪区域是主屏真子集、marker 归一化能容忍 OCR 空格。
  证据：`benchmarks/raw/evidence/neko-target-window-guard-20261009T095305Z.json`。
- `scripts/neko_target_window_host_probe.py` → `PASS_HOST_TARGET_WINDOW_GATE` 4/4，`model_calls: 0`，
  走宿主插件 `/runs` 打真实闸门（宿主是编译产物，只能这样验）：无 markers 被拒、被压住的窗口被拒、
  内容不符被拒且不带文本、点名窗口成功且标题/路由/命中数都对。
  证据：`benchmarks/raw/evidence/neko-target-window-host-gate-20261009T100716Z.json`。
