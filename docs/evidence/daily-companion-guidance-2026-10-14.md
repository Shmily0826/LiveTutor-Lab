# 日常伙伴：受控材料指示阶段

## 已交付与验收层级

| 层级 | 结果 | 本阶段证据 |
| --- | --- | --- |
| 源码 / 离线 | PASS | 4 个材料版本、授权、请求类型与图片坐标守卫 |
| 实际本地浏览器 | PASS | Chrome 154，1440×900 与 390×844 各 14 项实际 DOM / 布局检查；无控制台错误、页面错误或页面横向溢出 |
| 真实角色工具 / 模型 | 待主线集成验收 | 已提供内部 HTTP 接口，本阶段没有调用模型 |
| 实际设备播放 / 真人体验 | 未测 | 没有音频、房间麦克风或扬声器操作 |

新增文件仅为 `scripts/neko_learning_surface.py`、`scripts/neko_learning_surface.html`、`scripts/test_neko_learning_surface.py` 与本报告。未改 Sky Scout 源码、原图、native shell、host、launcher 或 Study 主文件。没有新数据库、课程记忆或付费服务。

可用行为：学习者在同一窗口选择原 HTML 或图片；HTML 的 `data-node-id`、`data-edge-id`、`data-line` 形成目标列表；图片点击产生归一化指示点。父窗口 SVG 提供高亮框和箭头，不向原材料 DOM 添加标注。仅学习者点击“指向这里”才执行 `scrollIntoView`；模型指令不滚动、不点击材料、不编辑材料。Escape / “清除指示”可取消。

指示存在时每 100 ms 读取当前 DOM 几何，包括 iframe 滚动、SVG 变换与溢出容器裁剪；图片区域随图片尺寸缩放。目标完全或部分在可见区域外时隐藏，提示学习者滚动。不存在或语法无效的目标隐藏并说明问题。原 HTML 自己的交互仍可使用，源文件不变。材料切换、重载或版本变化清空指示；指令必须携带当前 `material_id`，旧版本和非当前材料均返回 409。

## 固定材料与启动

默认使用已存在的 6 份材料，不生成新测试图：

- 用户指定 Sky Scout `.archify/architecture-sky-scout-20261003-192623/sky-scout.html`。
- LiveTutor `.archify/architecture-relations-20261013-230748/forward/forward.html` 与 `reverse/reverse.html`。
- 既有 `benchmarks/raw/evidence/diagram-input-forward.png`、`diagram-input-reverse.png`、`diagram-input-sky-dark.png`。

```powershell
python D:\CODE\project\LiveTutor-Lab\scripts\neko_learning_surface.py --port 48918
```

在本机打开 `http://127.0.0.1:48918/`。需要其他受信任材料时重复传 `--material <绝对路径>`。服务只暴露逐一指定的独立 HTML / PNG / JPEG 文件；不暴露目录、相邻文件或任意路径，单文件限制 32 MB。首次读入形成字节快照，点击“重新载入材料”才重新读取磁盘；读取失败保留旧快照。

端口 48918 避开 Study / native 使用的 48911 / 48916。同进程集成可 `LearningSurface(paths, port=0)`，线程调用 `serve_forever()`，用 `.server_port`、`.token` 完成内部调用；退出依次 `shutdown()`、`server_close()` 并 join 自己的线程。token 不应输出到日志、角色提示或报告。

## 精确 API 与材料身份

API 请求统一携带 `X-Learning-Surface-Token: <surface.token>`；没有 token 返回 403。Host 必须是实际监听的 `127.0.0.1:<port>`，不允许 DNS rebinding 主机名。没有跨域 CORS 授权。HTML 仅支持已由用户授权的开发者本地独立材料，不能把任意不可信网页当作同源 iframe 使用。

`GET /api/state` 返回：

```json
{
  "materials": [{"id": "0-<sha256前24位>", "name": "sky-scout.html", "sha256": "<完整sha256>", "kind": "html", "url": "/material/<id>"}],
  "active_material_id": "0-<sha256前24位>",
  "revision": 1,
  "command": null
}
```

`POST /api/select`：`{"material_id":"<id>"}`。由学习者选择材料使用，切换同时清除指示。角色教学先读取 `active_material_id`，不要自行替换学习者当前材料。

`POST /api/guidance` 的三个形状：

```json
{"material_id":"<当前HTML id>","kind":"selector","selector":"[data-node-id=\"entry\"]","label":"StartupPage 定位入口"}
{"material_id":"<当前HTML id>","kind":"selector","selector":"[data-edge-id=\"map-access\"]","label":"入口到地图服务的连接"}
{"material_id":"<当前图片 id>","kind":"rect","x":0.25,"y":0.25,"width":0.1,"height":0.1,"label":"正在解释的图片区域"}
```

清除：`{"material_id":"<当前id>","kind":"clear"}`。label 最长 160 字符；selector 最长 300 字符，浏览器实际查询无效目标时隐藏。图片 x/y/width/height 全部使用原图的 0–1 坐标，区域不得为空或越界。HTML 仅允许 selector，图片仅允许 rect；400 表示请求非法，409 表示材料已变或不是当前显示材料。

`POST /api/reload`，请求体 `{}`：重读既定材料，清指示并更新 hash / id。不追加外部文件、不写学习数据。成功返回新的 state。HTTP 成功只说明指令入队；尚未等同于角色已在学习者窗口正确指到目标。

图片教学路线：`GET /material/<当前id>` 返回与显示一致的固定图片字节，用 state 的完整 sha256 绑定提交给 Study 的内容。HTML 路线应由全局 `node D:\AI\tools\web-inspector\cli.mjs <原HTML或受控surface URL> --screenshot --json` 或已授权目标窗口捕获取得 PNG，再交已有 `study_submit_image`。HTML / SVG 属性可帮助定位，但不能替代真实 vision 像素证据。本阶段未增加截图 API，也没有在项目安装或导入 Playwright。

## 浏览器证据与失败记录

最终结果：`benchmarks/raw/evidence/daily-companion-guidance-browser-20261014.json`，含每项检查、实际浏览器版本、截图路径与 6 份材料验证前后相同的 SHA-256。检查覆盖原 Sky Scout 模块、原 SVG 关系、iframe 滚动、原图 zoom 操作后的重测或裁剪隐藏、图片 200%、图片滚动、换图清除、缺失目标隐藏。

共享 web-inspector 截图已复制到项目证据目录保留：

- Desktop：`benchmarks/raw/evidence/daily-companion-guidance-desktop-20261014.png`。
- Mobile：`benchmarks/raw/evidence/daily-companion-guidance-mobile-20261014.png`。

重现：

```powershell
python -m unittest discover -s scripts -p test_neko_learning_surface.py -v
$env:PYTHONIOENCODING='utf-8'
$env:NEKO_SURFACE_BROWSER_CHECK='1'
python -m unittest discover -s scripts -p test_neko_learning_surface.py -v
```

Browser 检查通过测试专用内联脚本驱动真实 DOM，再由共享 CLI 读取结果 / 截图；没有导入项目 Playwright。初次测试遇到 Python stdout cp1252 编码失败，修复量具输出，不是产品几何问题。原图放大时入口实际被裁剪，早期检查错误要求它仍可见；随后明确裁剪隐藏，并加入溢出祖先检查。desktop 检查后 active material 保留为反向图，导致早期 mobile 测试起点错误；量具现逐个视口由 API 选择原 Sky Scout。对应尝试的 JSON 已独立保存在 `daily-companion-guidance-browser-<时间戳>-desktop/mobile.json`，不删除失败文件。最早编码错误与原生 zoom 假设失败保留在本次执行输出。

Impeccable detector 已执行一次。静态检查把 CSS 变量背景当成白色，因此产生文字低对比警告；实际界面背景为 `#13191f` / `#1e2730`，正文与提示文字的对比满足 4.5:1。无 src 的图片元素初始处于隐藏容器，选择材料后才赋 src，实际浏览器无 broken image / failed requests。此项记录为静态检测的限制，不宣称整产品 accessibility 全量验收。

## 已核对的开源参考与许可证

2026-10-14 已读取上游源码和许可证：

- [rough-notation 源码](https://github.com/rough-stuff/rough-notation/blob/master/src/rough-notation.ts) 与 [MIT 许可证](https://github.com/rough-stuff/rough-notation/blob/master/LICENSE)。其实现把 SVG 插到目标元素旁，并可能改目标 position，使用 ResizeObserver / resize 重绘；直接使用会改变材料 DOM，且不直接解决父窗口图片归一化区域。
- [Floating UI autoUpdate 源码](https://github.com/floating-ui/floating-ui/blob/master/packages/dom/src/autoUpdate.ts) 与 [MIT 许可证](https://github.com/floating-ui/floating-ui/blob/master/LICENSE)。它覆盖滚动、resize、ResizeObserver、layout shift 和可选 animationFrame；用于定位浮层较全面，适配此小型无框架页面需要加入包与虚拟参考元素。

首版使用平台原生 `getBoundingClientRect` + 父层 SVG + 指示激活时的轻量几何采样，无依赖安装，没有复制 / vendor 上游源码。两套 MIT 许可均可后续使用；若引入实质源码需保留对应版权与许可。

## 支持边界、阻塞与下一步

支持：受控 surface 内的受信任独立 HTML 语义目标及普通 CSS selector；PNG/JPEG 的归一化区域；窗口移动由浏览器本地坐标处理；iframe / 图片滚动及可测量变换。实际验证的原图在 desktop zoom 和 mobile 语义视图下行为不同，检查读取实际布局，不强行假设它们采用同一缩放方式。

未交付：任意桌面应用、跨源 iframe、复杂 SVG mask / 任意 clip-path 的精确可见性计算、代码编辑器滚动行定位、自动点选材料或修改源文件。首版对部分裁剪目标隐藏整个框；不要把它说成无条件精确桌面指点。普通图片区域仍需角色/调用者从实际像素可靠定位；指示层不证明 vision 语义正确。

没有当前全局阻塞。下一步由主 Agent 将角色 `study_point` 接入此内部 API，将 Study 图片提交和当前 hash / 材料身份绑定，实测一轮解释 → 指示 → 学习者滚动 / 换图 → 新指示。指令当前只确认入队，浏览器端实际可见状态可在后续集成加回执。真人集中体验时检查指示是否帮助理解，而非单独重复已通过的几何测试。

额度：本子任务 DeepSeek / Lanlan.app / Lanlan.tech 新增均为 0，未修改共享账本。测试进程：独立 API / browser 量具服务器均 `finally` 关闭；最初 wrapper 退出后残留的 PID 54224 经 cmdline 确认为本任务 `scripts/neko_learning_surface.py --port 48916`，已明确 Stop-Process 清理。没有保留任务音频或捕获进程；48911 / 48916 交主 Agent 真实宿主使用。
