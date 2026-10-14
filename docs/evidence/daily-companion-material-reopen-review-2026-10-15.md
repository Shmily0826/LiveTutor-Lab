# 阶段47：材料页面主动重开设计独立审查

范围为当前launcher浏览器命令、Study index工具栏/main bootstrap、Surface根入口。仅读源码与当前状态记录，未运行测试、浏览器、应用、API或设备；只新增本报告，不改46报告、产品、manifest或共享记录。阶段46实际双主窗/无翻译aux证据承接，不能再把恢复入口问题误写为当前图未接store。

## 最小方案与现有接点

该方案可在既有链上实现，不需新服务、队列或模型。launcher当前先生成Study Chrome模板，在Surface port0创建后才得surface_url，最终经browser_window_commands构建Study与Surface各自app命令。应仅在这个最终构建点对Study app URL用标准URL编码附加learning_surface，保留其他query/片段规则与原模板，Surface app仍只用原根URL；readiness及后端UI_PATH不用跟着改。不要向query传X-Learning-Surface-Token，也不要把env token复制入DOM、日志或href。

当前Surface根GET会自行生成当前server bootstrap token，后续页面API使用其header；学习者导航到根即可复用本次课程/图/指示状态，不需要Study拿到token或代发API。入口只承诺打开本次仍存活的Surface；任务结束或随机端口已失效时不能保证恢复，也不能把任意loopback URL当经过认证的本任务服务。不会因此扩大server Host/token围栏。

Study index.html:71附近的toolbar-actions适合新增语义anchor，复用button样式，默认hidden且无href。target=_blank及rel=noopener可防新页取得opener；可附noreferrer减少传递来源URL。无需onclick/window.open、自动弹窗、轮询服务或付费调用。文字“学习材料”清楚，建议可读辅助说明其打开新页；不声称一定是独立app窗口或会自动并排。

## 必要解析与失败边界

- main在配置前先令anchor隐藏、removeAttribute('href')，避免重复初始化/坏参数保留旧href；缺DOM、缺参数、重复参数歧义、URL解析异常均安全保持无入口。
- 只允许绝对http://127.0.0.1:端口的根地址。端口为整数1..65535，必须明确非空；reject HTTPS/其他协议、localhost/IPv6/相似域名、userinfo、非根pathname、search/hash、相对地址、控制字符或超长值。可同时核原字符串的封闭形式和new URL规范化结果，避免URL容错把userinfo、反斜杠或替代IPv4表示洗成看似合法地址。查询参数先由URLSearchParams解码一次，不额外反复decode。
- 赋值用校验后的URL规范字符串与anchor.href，不用innerHTML。该参数只有导航能力，没有current material/course证明；真实课程仍由Surface已绑定store和原身份检查决定。
- 当前bootstrap首次await是I18n.init。恢复入口配置宜在首次await之前独立执行；若等语言初始化/后端状态成功才配置，离线或i18n失败会让这条无模型恢复路径一直hidden。错误不应阻断原bootstrap或修改课程/作答状态。
- 不能只用anchor.hidden=true断言用户看不见；既有button样式若声明display可能覆盖浏览器默认hidden样式。需实际computed visibility、键盘focus和缺href验证。此次定向猜测的base style路径不存在，未扩大检索；CSS是否已有可靠[hidden]规则属于实现/DOM检查待核，不是已证产品缺陷。

## CSP与ownership

当前meta CSP为script/style self、connect-src self、img self/data/blob、base-uri self、object none，没有导航限制。顶层anchor到另一个loopback端口不属于connect-src fetch，也不是嵌入iframe；无需为此放宽connect-src、script-src或加入inline handler/style。实际HTTP header可能还有policy，因此应使用最终task部署页面实查零CSP/page error，而非仅靠canonical meta判断运行成功。

target=_blank可能创建普通标签或新窗口，需以实际任务Chrome行为确认。用户从已记录task-profile app页点击后，应仍留在该profile和其owned进程树；现有launcher root创建时间清理机制不应为了新页扩大到个人Chrome或全系统同名进程。不能把新target/CDP id当OS进程ownership，更不能凭mock anchor.click认定物理可见。若真实行为只开tab，这仍可作为明确的主动恢复页，但报告须准确描述，不把它说成新增独立app保证。

## 最少验证建议与结论

1. 纯函数/命令测试：Study app唯一编码参数、Surface原URL/原mute/profile不变，未启Surface的旧命令不变；合法根地址与上述无效/边界输入不改变bootstrap业务。
2. 共享inspector真实DOM：无/非法参数入口不可见且无href，有效参数显示正确href/rel/target，无inline CSP错误；i18n失败时入口仍可用。桌面/手机不挤出既有controls，按钮样式不能使hidden入口露出。
3. 唯一task offline原入口：主动关闭材料页面、从Study点入口，检查新页URL/当前课图及task profile归属；不依赖模型、不重提图片/重造题、不声称pointer已经渲染。退出后owned/端口清理沿原证据检查。

目前是设计审查，没有冻结实现或新运行结果，未发现方案本身必须另建系统的P1/P2。以上是最小必要边界，等待Main冻结后仅复审实际增量。关闭材料页恢复、旧URL过期和Chrome app/tab行为与整项A/E、模型/设备/human验收分开记录。

## 阶段47冻结实现独立复审

六文件SHA实核与Main冻结值一致：

| 文件 | SHA256 |
|---|---|
| `scripts/neko_tutor_start.py` | `2e0676438ea207c1cfacc116fd4bccb8de53f4f4a17b7810be269f4116360b26` |
| `scripts/test_neko_material_windows.py` | `14861d9e7470bae204643e36832c298619ca2f70221ec1048ba2e6bf7e1e04ee` |
| `scripts/test_neko_material_link.cjs` | `32add7261a7e040eea97cd950cc13e764dd1b2f7c935526e53fdc86726b3749d` |
| `scripts/test_neko_material_link_browser.py` | `766bfe4ad10b8a08850fc91a9472e91025deb54dd3d8e3986c0e9df2ca3e3574` |
| canonical `static/index.html` | `e8326a83958fab73370a99943ed43bd9c5aa2ca9a5231a39a6f9d27aa9303ca3` |
| canonical `static/main.js` | `add5f2c643e41e11654b9929429e6da82d55eab61fc30c5d876a043cb3c13beb` |

### SOURCE/OFFLINE

launcher仅在Study app命令且surface_url非空时，用urlencode追加learning_surface；独立Surface app仍保持原URL，模板/mute/profile/Translate参数与ownership逻辑不变。当前输入UI_URL是固定无fragment的本机UI路径，该实现满足实际调用；它不是支持任意URL拼接的通用函数，也没有将token加入query。原Study-only/surface-only行为保留。

index工具栏新增默认hidden且无href的anchor，target=_blank、rel=noopener，title明确新页面。只补局部min-height/padding/border/radius/text-decoration样式，未改CSP；canonical现有style-src-attr允许inline属性。最终部署HTTP CSP仍待实际任务页面核验。

configureLearningMaterialLink先hidden并移除旧href；缺DOM安全返回，getAll要求恰一个参数。原串regex限定http、精确127.0.0.1、显式非零数字端口及可选根斜杠，再由URL解析核协议/hostname/port及无userinfo/path/query/hash；非法端口由URL异常拒绝。无innerHTML、网络请求、额外decode或持久化。URL会把显式默认端口80规范为空而被拒，这不影响当前port0产生的实际Surface URL，不声称解析器支持所有合法HTTP服务。该函数在bootstrap首次I18n await之前调用；$id实际定义于main.js:54，独立fixture并非补出一个生产不存在的helper。

独立执行纯本地`node scripts/test_neko_material_link.cjs`通过（合法值、旧href reset、重复参数、18个缺失/不安全输入）；Source venv `-X utf8 -B scripts/test_neko_material_windows.py` 4项PASS、0.003s。未运行browser.py或任何服务。Main报告text-start9通过，本Agent未重复。

### Main共享浏览器原件的独立只读核验

最终`daily-phase47-material-reopen-browser-closecheck.json` SHA实核 `94f27bb039d1db5450a94a093ee83b51c38cc545c118bed04871d0616203f6f7`。桌面与手机有效参数各5checks=true，target_events均loaded=2/closed=1；实际第一张PNG ready后调用window.close，再以自身window.closed===true的beacon记关闭，第二次anchor导航重新PNG ready。两种viewport缺参时computed checkVisibility为false且无href、loaded/closed均0。四组inspector_exit=0、pageErrors=[]、consoleErrors=[]、无horizontalOverflow，原forward PNG SHA `057d5bac5ae440dfa0d3269f5138f1188fa182bc0fce81435676c6a4caa65dcc`保持。

此前`daily-phase47-material-reopen-browser.json` SHA `4fbdfea2cc3f8afcdada61a8ae02c2fb50d9845a4b6bd65595f435cdd7ada7af`原FAIL保留：有效参数两组loaded=1/closed=0，等待关闭观测超时；缺参隐藏通过。Main说明其pagehide观测器未得到关闭事件，后改window.closed观测，不改产品来迎合测试。新原件支持浏览器级关闭并重开的窄证据，不能因此回改旧FAIL。

browser fixture仅读shipped HTML/CSS并抽取精确initializer，删除其余script，不运行完整Study bootstrap；target是既有LearningSurface+原图片，没有plugin/DB/provider。其局部fixture HTTP、导航与自动click由Main运行，本Agent仅读原件，不能冒本Agent独立browser执行，也不等于物理任务Chrome profile或真人主动点击验收。

Main另报旧product-ui.test.cjs在备份旧main亦因$id未定义失败，临时补stub后又缺studyMaterialRevision，相关测试改动已撤销。本审查确认生产$id存在；没有运行/修补该陈旧fixture，保留F测试维护局限，不将其说成新feature已通过整套产品UI测试，也不据此否定当前定向证据。

本次窄审未发现新的具体P1/P2，可交Main进行双static受保护部署及唯一57完整实际boot。尚缺完整bootstrap/最终HTTP CSP、实际task profile重开与owner退出证据；不以fixture导航宣称新增独立app或并排保证。没有新模型、pointer物理渲染、音频设备或human通过声明。实现复审追加后冻结，除本报告外未修改文件。

## 最终57原件只读收尾

原件`daily-companion-material-reopen57.json` SHA实核 `0e023b5284ae8de32349d32e54e8bfe5d0b364e9d032d1ad6e09aa9538d56892`。owned browser实际args含当前`learning_surface=http%3A%2F%2F127.0.0.1%3A53515`和Translate feature参数；actual status material仍为daily-window-fixture54-A、study_store_snapshot/image，原forward PNG SHA `057d5bac5ae440dfa0d3269f5138f1188fa182bc0fce81435676c6a4caa65dcc`相同。参数传递与同课同图恢复获得本场实际证据。

共享inspector访问正式served/protected Study，finalUrl为带上述query的48916 Study路径，HTTP200、success=true、failedRequests=[]、consoleErrors=[]、pageErrors=[]、无横向溢出；bodyTextSample实际含“显示学习材料”。这证明正式脚本的早期initializer入口可见且该快照无CSP/page错误。title仍是“N.E.K.O protected · 文字模式（麦克风已关闭）”，页面样本仍含Refreshing，不能宣称其余异步bootstrap或status就绪全部完成。也没有实际task Chrome点击入口的新证据；真实关闭再重开的证据仍限前节完整披露的共享fixture，不补成task profile验收。

实际窗口枚举再次为两个1050×832预期主app加“Translate this page?”355×101辅助弹窗；原`two_expected_windows=false`保留，其他所列checks为true。46的56曾无aux只证明那个单场，不能外推Translate参数稳定解决。此复现是后续局部UX问题，不能靠改窗口计数或再原样启动掩盖。

exec_session=86035，终态exec_exit=0、cleanup_errors=[]、browser_owned_alive=[]、Native16508不存活；48911/48916/9234/53515均无listener。原round/DS835/app78/tech0保持，audio/capture/loopback=false。以上均为Main保存原件的独立只读复核，本Agent未运行当前服务、API、浏览器、设备或测试。

阶段47链接实现的SOURCE/OFFLINE、共享fixture关闭重开、正式页面早期入口显示分别成立；本场整体窗口UX仍PARTIAL，Translate可靠性与陈旧UI fixture保持F余项。没有新增模型、指示物理渲染、音频或human验收。原57和先前FAIL未修改；本次仅追加本报告，审查收尾冻结。
