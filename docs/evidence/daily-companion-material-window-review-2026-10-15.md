# 阶段46：材料窗口可见性独立源码审查

已完整读取当前contract/plan/status/blockers；本次仅窄读launcher、Daily入口与既有Surface入口/恢复逻辑。没有启动浏览器、Native、服务、模型或设备，没有读取用户DB、修改预算、产品或共享记录。以下属于SOURCE审查，不替代Main计划执行的原入口实际桌面检查。

本次源指纹：launcher `fe03fe4541e61f5270b2d34e8b67adbf06f0f00a60d705a7de0a77a8fc671cb4`；Surface Python `8586263c3e49f7d97b631ad9e12e2fa2293e5d4fb07872ae10f2d34582161c3d`；Surface HTML `1cffcd2d16330f0a5a1449d0540a284e5a0b71c91572c4ba5cbd276c73407a92`；Daily cmd `e6029f0da609cb50be20c02f4a6c03f344027bc4490e83806f7bc478cd422bd0`。

## 当前接线事实

- `Start-Daily-Tutor.cmd`真实传入`--text-only --study-ui --learning-surface`，使用固定daily store与原round；不是旧22报告所述的未接线状态。
- `neko_tutor_start.py:735-765`创建port0 Surface，给宿主传URL/token，等待Study就绪后调用`surface.attach_study_store(store)`，随后才启动Native和Chrome。
- `LearningSurface.attach_study_store`设`follow_study=True`并立即refresh。当前课已保存图片存在时选择该图；无图/读失败时active为空，不回退默认Sky充当当前图。`refresh_study`替换旧snapshot、清command并增加revision；页面轮询与revision保护沿用。
- 学习者显式选“参考”材料后`follow_study=False`，页面显示“查看参考材料 · Study当前课程”。这种主动浏览参考不等于当前图同步失败；实际验收需同时核dropdown、course和图identity。
- 页面当前断网会隐藏材料、清指示并将current=null，后续poll恢复会按当前active材料重载；不需要重做已有几何测试来证明本次窗口修复。

## 具体缺口与最小建议

### 可见性：一个新窗口命令携带两个URL

`chrome_command`原本返回`--app=UI_URL`。learning-surface分支在`neko_tutor_start.py:745`移除app参数，附加`[--new-window, UI_URL, surface_url]`，并在782仅执行一次Popen。这请求的是同一个新浏览器窗口中的两页，源码没有请求两个独立可见窗口，也没有要求并排显示。因此即使两个页面均成功，当前材料仍可能藏在另一个tab；不能用Surface HTTP ready、存在两个target或两个页面截图冒充同时可见。

建议Main先在task profile实查窗口数、两个URL所在window/tab及当前前台页，记录原行为。最小交付可明确打开独立材料窗口并提供可重复“显示材料”入口；若采用同profile第二次Chrome启动，它可能转发给已有browser进程，第二个短命Popen的PID不能当新窗口owner。应继续依赖本次已记录browser root的创建时间及其进程树，不把任务扩大为接管个人Chrome。无需制作新图片或重建Surface。

### [P2] 同图加载失败后，“重新载入”不重新请求图片

源码触发链：

1. `neko_learning_surface.html:57`的image.onerror令ready=false并清指示，但保留current和image.src。
2. `:78`的reload按钮调用`/api/reload`后仅apply返回state。
3. `LearningSurface.reload_materials`依据原bytes生成同一material ID；Study相同snapshot也保持同图ID。
4. 页面apply在`:67-68`仅于current不在materials或active ID不同才choose。当前图ID未变时不会重新赋src，ready仍false，浏览器不会因该按钮再请求原失败图片。

这使瞬时图片GET失败后的提示“请重新载入材料”无法由对应按钮完成恢复。它与poll断网恢复时主动current=null的已实现路径不同。

最小修法是在显式reload成功并通过最新revision检查后，按当前state.active_material_id重新choose当前材料，避免使用await前旧current快照；也可让显式reload具备强制重载标记。保持课程/材料身份与旧回调保护，不刷新用户数据或重新提交图片。必要验证是实际DOM中同一图片URL首GET失败、点击按钮后产生第二GET且ready恢复；再加await期间换课/换图时只加载最新active材料的负例。此发现已即时发Main，本Agent未修改实现或运行测试。

### 窗口关闭后的恢复入口

launcher主循环只remember_browser_tree，不检查Surface页是否被关闭；关闭单个材料tab通常不会使整个browser退出。当前可用恢复信息是控制台打印的本次随机port URL，launcher没有用户可见的“重新显示材料”动作。可把明确入口与上述独立窗口交付合并，不应通过自动反复弹窗抢占学习者操作。服务仍在但页已关属于UI恢复问题，不能宣称课程/图片丢失。

## Ownership与验收边界

当前text模式Chrome使用当前store下独立`browser/text-profile`、`--mute-audio`，不使用个人Chrome profile；已有owner文件中相同PID+创建时间仍存活时拒绝重启。浏览器root由remember_browser_tree记录kernel创建时间，stop_owned_tree复核后仅停止该树；cleanup_resources各资源独立attempt，错误不会跳过其余清理。此次没有发现为显示两页而放宽到全系统Chrome清理的代码。

窗口拆分若新增Popen/重开动作，必须沿用本次root ownership并保留失败聚合；不能因第二命令已退出就认定第二窗口不存在或清理完成。实际窗口数、焦点、当前图显示、指示可见、关闭重开及退出无listener仍待Main本次text-only/offline-egress/API0原入口检查。本报告不声称任何模型、音频设备或human体验通过，也不代表整个A/E完成。

本轮只新增此独立报告。初稿冻结；后续仅按Main明确的修复/实际证据任务追加复核。

## 阶段46冻结修复复审与P2关闭

实读四文件SHA与Main冻结值一致：

| 文件 | SHA256 |
|---|---|
| `scripts/neko_tutor_start.py` | `cf4b8965f9ed6a256bcbb880c2e216b5f6f325c9197691eb3188e1125b5282eb` |
| `scripts/neko_learning_surface.html` | `b4aea47ed6a8fd493aadd77e56a334185cb31c2ba53b46f214550096675f8b4a` |
| `scripts/test_neko_material_windows.py` | `a943df8324297c1344f9c60fe714bd0a82ed2eb332c8b76cc519e7d3a1006d30` |
| `scripts/test_neko_surface_image_retry.py` | `8658961e2c8024a005e0b2fcf1eb63635c17ee868f29d1e6c28683b83c13d45a` |

### 独立SOURCE/OFFLINE核对

`browser_window_commands`为Study与Surface分别构建单个`--app=URL`命令，不再拼接两个URL或`--new-window`；共享当前task profile、mute及原Chrome限制参数，没有修改模板。surface-only也会进行Chrome preflight并生成材料窗口命令；原Study-only命令保持。main依次Popen、立即加入task_browsers并尝试记录创建时间，循环继续核各Popen。Chrome可能把第二命令转发给首个profile进程；代码没有把Popen数量当窗口数，已退出的转发进程不会假造root记录。

cleanup_resources可选additional_browsers保持旧调用兼容，对每个Popen独立attempt ownership，再仅调用一次既有stop_owned_browser(record)；某个ownership记录失败会汇总错误且不阻止后续记录/清理。主finally传task_browsers[1:]，不重复加入首个browser。现有kernel创建时间核验、仅自有root树清理和错误退出行为没有被替换。

独立执行现有Source venv的`python -X utf8 -B scripts/test_neko_material_windows.py`：4项PASS，0.002s。覆盖两单URL同profile/mute、surface-only和旧Study-only、两launch记录后一次owned清理、一个identity错误不阻止其余清理。测试只用mock进程/函数，没有启动浏览器、宿主或设备；不能凭这些mock证明实际窗口已可见。

Surface的`apply(next,reloadCurrent=false)`先拒较旧revision，再保存state；force分支使用当时state.active_material_id调用choose。显式reload传true，因此同ID图片确会重设src；旧reload响应在较新图/指示revision之后返回会在choose/clearLocal前被拒。没有捕获await前旧current强行重载。原P2从SOURCE已关闭。

### Main实际共享DOM原件的只读核验

本Agent未运行retry脚本或浏览器，仅读其源码与Main保留的before/after JSON：

- `daily-phase46-image-retry-before.json`，SHA `5fb7554fb1a2e486bbfde515a8729891da4ba80bb1a97a65bd0d49333e7df86c`：桌面/手机均初次错误可见、点击reload仍不ready，各仅1次图片GET，原失败被实际复现。
- `daily-phase46-image-retry-after.json`，SHA `fd318cfb2a2376df7beca11c049643977cb402ec35afd4edb237e19b561c4123`：桌面/手机各5checks全true，各3次图片GET（初次失败、同图重试、换图）。包含重试后ready/几何指示恢复、故意延迟旧reload响应后不恢复旧图且不擦新pointer。

两原件均inspector_exit=0、pageErrors=[]、无horizontalOverflow；唯一consoleError是测试主动注入的首个503。fixture复用原forward/reverse两PNG，前后image_hashes一致；没有Study DB或模型。这个P2具备Main执行的实际DOM关闭证据，不能把注入503说成修后零错误场，也不冒本Agent独立重跑浏览器。

### 原入口54与剩余实际窗口验收

只读`daily-companion-material-window54.json`，SHA `cc75718f8c1d6100fa7e85f368c0fb41ada38a031b361ed75035361876890c4b`。原件visible_browser_windows仅1个可见Study标题窗口（1050×832），与旧命令可隐藏材料的调查一致；它不证明修后两app窗口。实际SDK set_course为daily-window-fixture54-A，提交图片结果degraded=true，符合本场API0的预期，不能当模型解释通过。材料截图正确由Main执行/观察，本Agent此次未重新打开页面或检查屏幕。

原件terminal为exec_exit=0、cleanup_errors=[]、browser_owned_alive=[]、Native不存活、48911/48916/9234无listener；原round与DS835/app78/tech0预算边界保持。以上是对Main原件的只读核对，没有当前进程/端口重查或账本写入。Main报告的text-start9/store8另项通过不冒本Agent执行。

本次冻结修复未发现新的具体P1/P2，可交Main执行唯一55实开窗口验证。尚未保证并排位置、自动重开已关闭窗口或提供完善恢复入口；学习者可自行摆放，原控制台URL仍是恢复线索。这些边界保留，不将命令构建4项或retry DOM通过称为全部A/E完成。无新服务/API/声音/捕获/回环，除本报告追加外未改文件。

## 55原件与Translate最小参数修复复审

只读55原件SHA实核 `96cd47702cb3bf2cb9ed93fb798471ee26ce395b3e844e7e3cce84ccd3ad7307`。底层visible_browser_windows实际为三个：Study与“N.E.K.O · 学习材料”两个1050×832可见主app窗口，另有“Translate this page?”355×101辅助弹窗。原`two_real_visible_app_windows=false`检查完整保留；review将两主窗与一aux分类符合原枚举，不能把false悄改成完整成功。`study_and_learning_material_titles`、same_course_restored、same_saved_png_restored为true；这只支持同54 owned store重启后当前课程/保存图正确的既有callback证据。

actual point status/request均is_error=false、ok=true，active material一致，request返回该material的rect command。其proof范围是实际回调已排入guidance；本次未看到物理窗口渲染该pointer的独立证据，不能从command存在冒称实际显示。原件也明确保留这个范围。

55终态exec_exit=0、cleanup_errors=[]、browser_owned_alive=[]、Native不存活、三端口无listener，原round/DS835/app78/tech0保持，audio/capture/loopback均false。这里只读核Main保存的原件，没有重新运行当前进程/端口检查。

本次两个冻结SHA实核：start `b887796950c65b82adbc70f1dc0c02edbb6dc43bfd8e5053f2c82fb3e81232ce`，windowtest `6ab7b93f9e15f264c62c58437203b607c622a95496beb814c1a9f8f3ce3849bf`。源增量为Chrome task命令的`--disable-features=MediaRouter`扩为`--disable-features=MediaRouter,Translate`；测试相应断言此参数。没有新增profile读取、个人Chrome设置写入、捕获接口、额外窗口控制或owner放宽。两个app命令均从同template继承此参数。HTML与retry测试SHA仍为上节冻结值，没有重跑未变DOM的必要。

Main报告已以本机shared Playwright1.63.0源码对照Translate特性名，并运行window4/text9通过；本Agent只读本轮两行代码与55原件，未import/control浏览器、未执行这些追加测试。参数是对实际翻译弹窗的有界修复，是否在实际任务Chrome上消除该弹窗仍须唯一56验证，不能把SOURCE参数存在当运行通过。

本轮未发现新的具体P1/P2，修法可供Main进行56。55“两个预期材料/Study主窗已实际出现”的窄证据成立，但原all-window-count失败与翻译弹窗UX缺陷保持原记录；没有追改55、没有完成整项A/E、没有模型/设备/human通过。报告再次冻结。

## 最终56只读复核与阶段46审查关闭

原件`daily-companion-material-window56.json` SHA实核 `42f88ed152dcd5d409121b4bc5caf70064ca6f4b6f983fa1b3091ba3f700cedf`。visible_browser_windows确为两个1050×832可见窗口：Study文字模式与“N.E.K.O · 学习材料”；auxiliary_windows=[]，四checks均true。实际status material为study_store_snapshot/image、course=daily-window-fixture54-A，PNG SHA `057d5bac5ae440dfa0d3269f5138f1188fa182bc0fce81435676c6a4caa65dcc`与expected一致。因此本次Main实际原入口支持两个预期app可见、翻译aux未出现、同课同图重启恢复的窄UI证据。

exec_session=33605，terminal exec_exit=0、cleanup_errors=[]、browser_owned_alive=[]、native_alive=false，48911/48916/9234/59748均无listener。原round不变，DS835/app78/tech0保持；外部allowed=[]/direct=[]，社区域名请求被拒。audio/capture/loopback=false，原件post56_source_gate=PASS。这些为只读核Main保存的终态，不是本Agent重新启动/查询服务、设备或账本。

两个最终源指纹再次实核未变：start `b887796950c65b82adbc70f1dc0c02edbb6dc43bfd8e5053f2c82fb3e81232ce`，windowtest `6ab7b93f9e15f264c62c58437203b607c622a95496beb814c1a9f8f3ce3849bf`。本轮无新具体P1/P2，阶段46独立审查关闭并冻结。55原false和翻译弹窗调查历史保留；56没有新增pointer物理渲染、模型、声音或human通过声明，也不替代全部A/E余项。
