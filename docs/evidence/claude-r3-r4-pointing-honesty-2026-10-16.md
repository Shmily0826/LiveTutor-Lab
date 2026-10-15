# R4：自主高亮——先诚实（已做），再尽量做成（只到可行性；Native 未验）

**证据层级：离线（真实 `study_point_tool` + 真实本地学习材料服务 + 真实 forward 图 HTML）。没有 Native 场、没有 surface_guide_attempts 新数据。**

## 第一步（必做）：没有 accepted 高亮就不许说“标出来了”
`study_point_tool` 现在对每个结果给出 `highlighted`：
- 任何失败（窗口没开、窗口无响应、没选中源码材料、材料已换、行号无效/找不到唯一目标、没确认材料身份、被材料服务拒绝）→ `highlighted=false`，并返回**角色必须如实转述的** `say_this`（中/英，按 `language`），relay 明确“Nothing was highlighted: never say you marked, pointed at or highlighted it, and do not retry with an invented selector”。
- `kind=status` 成功也 `highlighted=false`，relay：“只是查看，尚未高亮；不得说标好了；要高亮请带返回的 selector 与 material_id 再调用”。
- 只有材料服务接受命令（`command` 非空）才 `highlighted=true`，措辞仍是“已请求高亮……”，不说“已渲染”。
- 工具说明加一句同样的规则。
`test_neko_point_honesty`（8 项）：逐类失败都断言 `highlighted=false`、`say_this` 不含“标出来了/指给你/已经高亮”、材料服务 `command` 仍为空；status 不高亮；被拒的 rect 不算；英文措辞。原 `test_neko_source_point`、`point_intent`、`material_control`、`learning_surface*` 全过。

## 第二步：HTML 与 PNG 的可行性
- **HTML（可行，工具链层已证）**：用真实 `forward.html`（`.archify/architecture-relations-20261013-230748/forward/`，含 `data-node-id` 与 `data-edge-id`，边 `link0`=wex→nud、`link1`=nud→rez）经真实 `LearningSurface` 选中后，`study_point(kind=status)` 的 `targets_for_pointing` 带 “wex → nud · link0” 标签与 `[data-edge-id="link0"]` 选择器；按该选择器 `kind=selector` 被接受，`highlighted=true`，服务端命令为该选择器（测试 `test_html_edge_can_be_found_by_status_and_accepted`）。**这只证明工具与材料服务连通，不证明模型会自主这样调用**——之前三场 Native 的失败是模型没走这条路径。
- **PNG（不可行，按合同不猜）**：Study 提交的 PNG 只有归一化矩形接口，没有可靠的区域定位来源（OCR/视觉不给箭头坐标）。工具说明已要求“没有证据支持的区域就不要编矩形，请学习者选对应的 HTML”。
- **Native 最多 3 场（HTML 路径）没做**（无额度）；结论停留在“自主高亮仍未被 Native 证明；手动指向可用”。

## 手动指向怎么操作（写进验收说明 v3）
在**学习材料窗口**里自己选中想看的材料（HTML 图选“forward”那份），再点图里对应的节点/连线；角色的高亮只在受控材料窗口里生效，Study 提交的 PNG 不会被高亮。

## 限制
- 没有证据说明模型在“把 WEX 到 NUD 那条指给我看”时会先 `status` 再 `selector`；若下一轮要验，按合同在 Native 最多 3 场，以 `surface_guide_attempts` 的 `accepted` 为准。
- 回退：本改动只在 `study_point_tool` 外层包装与说明里；删除包装即恢复原行为。
