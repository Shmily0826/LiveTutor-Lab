# 阶段46：独立材料窗口与同图加载失败恢复

完整任务以 [contract](../daily-companion-contract-2026-10-14.md) 为准。Goal active，上一45有改码/部署/模型53/发布，属progress；本轮先完整读四记录，原round实核835/78/0，未新增付费请求。Main实现/运行，独立Agent仅 [material-window review](daily-companion-material-window-review-2026-10-15.md)。

## 当前入口实际基线54

不能沿阶段22旧报告说当前尚未接store：现 `Start-Daily-Tutor.cmd` 已含 `--study-ui --learning-surface`，launcher Ready后确实 `attach_study_store(store)`。本轮复现的是窗口呈现和恢复行为。

- 实际原launcher exec24720，fresh store `neko-daily-material-window-20261015-54`，`--minutes3 --text-only --offline-egress --api-budget0`，原round/egress2000。没有重置账本、修改用户日常store或使用任何音频输入。
- Native pid56604实际1个可见窗口；task Chrome profile按已记录creation-time核所有权，**只有1个可见顶层窗口**，标题是Study文字模式。原命令一个 `--new-window` 后接Study与surface两URL，材料可能在另一tab，不能保证看见当前图。
- 实际SDK设测试课程A、提交原forward PNG。API0按预期返回degraded/agent_quota_exceeded，无付费请求；图片仍已通过正式entry落库。不能把这场说成模型教学通过。
- 共享web-inspector查看实际surface http://127.0.0.1:53695，DOM跟随本课A、实际PNG可见、无console/page/request失败或横向溢出。已观察截图 `C:/Users/Shmily/AppData/Local/Temp/web-inspector-GjPBZX/desktop.png`。这证明图/课程接线正确，且与前台Study单窗口缺口分开，不冒本人当时看到。
- exec24720按原3min界限 **terminal exit0**，cleanup_errors[]；browser owned IDs[]，Native56604已死，48911/48916/9234无listener，ledger835/78/0不变。一次Enter尝试因exec未用tty而stdin closed，无重启/绕过，仅等待同live handle至原定时清理。
- 基线原raw `daily-companion-material-window54.json` SHA `cc75718f8c1d6100fa7e85f368c0fb41ada38a031b361ed75035361876890c4b`。API提交测试内容/降级不当正常模型验收。

## 两处实际修复

1. `neko_tutor_start.browser_window_commands` 给Study和学习材料分别一个 `--app=`命令，同一专用profile、mute及既有flags。材料独立窗口最后打开，surface-only也会检查Chrome并开窗。没有强制摆放或宣称窗口永不遮挡，学习者可并排摆放。
2. 每个Popen都存入task_browsers并尝试记录creation-time；Chrome可能把第二次命令转发给第一profile进程，不能把Popen数当窗口数。cleanup_resources兼容旧参数，额外启动记录逐项尝试、单项失败不阻其它记录，最终仍只调用既有已核身份的owned profile树清理。
3. `neko_learning_surface.html` 的reload在既有revision早拒之后，对当下active材料重新choose。此前img.onerror保留相同ID，旧apply不会重设src，按钮无效；现在确实重发同图请求。较早reload response仍先被revision拒绝，不能强行重选旧图或擦掉较新材料的指示。

没有改材料文件、Study/CodeGraph数据、角色音频、共享模型/供应商/额度或新造指示系统。关闭材料窗后从Study UI一键重开尚未交付，目前控制台URL仍可重开；作为剩余入口工作记录，不冒已解决。

## 冻结与离线/浏览器证据

| 文件 | SHA256 |
|---|---|
| scripts/neko_tutor_start.py | cf4b8965f9ed6a256bcbb880c2e216b5f6f325c9197691eb3188e1125b5282eb |
| scripts/neko_learning_surface.html | b4aea47ed6a8fd493aadd77e56a334185cb31c2ba53b46f214550096675f8b4a |
| scripts/test_neko_material_windows.py | a943df8324297c1344f9c60fe714bd0a82ed2eb332c8b76cc519e7d3a1006d30 |
| scripts/test_neko_surface_image_retry.py | 8658961e2c8024a005e0b2fcf1eb63635c17ee868f29d1e6c28683b83c13d45a |

原两源码独占备份 `benchmarks/raw/evidence/phase46-before`，原launcher fe03fe…671cb4、原HTML1cffcd…07a92。没有清库或改原raw。launcher直接用当前script/source，HTML由surface直接serve；product/host manifest不需要虚改为别的文件指纹。

- 窄新window命令/多资源清理 **4 PASS/.002s**。
- 现有text bootstrap/拒混合输入/保护页/创建时间所有权 **9 PASS/.648s**。
- 现有实际temp SQLite current-material projection **8 PASS/.267s**，没有重跑已过Sky/全几何批次。
- 新shared-browser故障负例：首图片GET故意503，未修桌面/手机各仅1 GET，按钮后仍不ready；`daily-phase46-image-retry-before.json`保留，明确叫known bug，不当修复PASS。
- 修后同一fixture桌/手机各 **5实际DOM checks PASS**、3图片GET：初始错误可见且禁指示→同图重试ready→指示恢复→晚旧reload不恢复旧图→不清新图pointer。`daily-phase46-image-retry-after.json`。唯一允许console错误为注入的503；pageErrors/横向溢出无，原两PNG SHA不变。
- 已观察修后desktop/mobile截图，原dark界面和布局保持，最新pointer可见。按web-testing+全局规则，仅共享web-inspector，无项目Playwright安装/个人Chrome读取。impeccable用于窄harden，context无PRODUCT/DESIGN不阻既有修复，未擅建新设计；一次detector仍是原white-background推断的contrast警告和初始化无src警告，实际CSS深底/图片ready加载和空态均已核，未据其误报改版。

## 下一步 / 证据范围

独立实现复核pending → 唯一修后55实际text-only/offline重启同一测试store，核任务Chrome两个真实可见窗、继承当前课程PNG、实际surface指示与清理 → 精确allowlist发布。

SOURCE/OFFLINE与真实浏览器DOM不等于真人看见/听见。用户human验收继续待核心成熟后集中一次；麦克风/capture/loopback/音量均未操作。B多ASR/尾约束、D源码版本引用、剩余A/E入口与F集成继续，Goal不结束。


阶段46修后唯一55已实际启动：exec74811(tty)，复用54自有store neko-daily-material-window-20261015-54 保留课程PNG/历史，surface http://127.0.0.1:58781；--text-only/offline-egress/API0/3min/原round，账本835/78/0。独立freeze已闭合source+DOM；本场尚未就绪终态，不冒双窗PASS。只poll同handle，待核2实际任务Chrome窗/重启继承与pointer，再Enter正常清理；不因观察超时重开，不mic/capture/loopback/音量。


## 55复测及新暴露的翻译提示

阶段46修后55终态：exec74811 tty Enter正常exit0/cleanup[]，已复用54store恢复同课程/同原PNG；实际任务Chrome有2个学习app窗口，但多1个Translate this page? popup，原total-visible==2 false保留，不改写原始检查成功。raw55 SHA96cd47702cb3bf2cb9ed93fb798471ee26ce395b3e844e7e3cce84ccd3ad7307；已分2main+1aux，工具指示只证queued，截图/DOM独立分层。全部owned/端口死，ledger835/78/0。根据新观察仅给任务Chrome加disabled Translate（本机shared Playwright1.63.0实际代码已有该feature用法，未动个人Chrome设置），start新b887796950c65b82adbc70f1dc0c02edbb6dc43bfd8e5053f2c82fb3e81232ce/windowtest新6ab7b93f9e15f264c62c58437203b607c622a95496beb814c1a9f8f3ce3849bf，必要4+text9再PASS，HTML/DOM bytes未改不重复。独立delta复核pending，56未开，所有A–F/Goal active。

55两app标题和课程PNG检查均支持最初窗口修复，但翻译气泡是新的实际UX问题，故不把总窗数false当PASS。Main未再次截图/修改HTML，不增加旧测试计数；上文4+9+8为21不同离线cases，桌/手机各5 DOM，不把重跑4+9累计成新增测试。56只验证新Translate启动参数及同store窗口/清理，不重复模型/图片教学。


阶段46最终Translate参数复核56运行：exec33605 tty，复用54任务store/同课程PNG，surface59748，Native26236；text-only/offline-egress/API0/3min/原round，不采mic/capture/loopback，不发声。只poll原handle，终态前不声称清理或完整通过；56原raw独占保存，独立delta已闭合。全部A–F/Goal active。

## 最终56实际复核与终态

最终Translate参数冻结：launcher SHA b887796950c65b82adbc70f1dc0c02edbb6dc43bfd8e5053f2c82fb3e81232ce，windowtest SHA6ab7b93f9e15f264c62c58437203b607c622a95496beb814c1a9f8f3ce3849bf；HTML与retry测试仍为上表值。上表launcher/test是55以前的中间冻结，最终发布使用本段值。

56 exec33605复用54任务store，surface59748，Native26236，text-only/offline-egress/API0/原round。按任务profile已记录creation-time枚举，实际可见窗恰为Study与学习材料2个，无Translate或其它aux；actual study_point status恢复同课A及原PNG SHA057d5bac5ae440dfa0d3269f5138f1188fa182bc0fce81435676c6a4caa65dcc。四项checks全true。本次未新发pointer命令，不冒物理指示渲染/模型/声音/human。

Enter正常exit0/cleanup_errors[]，egress allowed[]、direct[]，仅community.project-neko.cn被离线规则拒绝；全部owned browser与Native26236已死，48911/48916/9234/59748无listener。post56 SourceGate PASS，原ledger835/78/0不变。raw daily-companion-material-window56.json SHA42f88ed152dcd5d409121b4bc5caf70064ca6f4b6f983fa1b3091ba3f700cedf已冻结；55原false与翻译popup原件继续保留。

源码/离线、共享DOM故障恢复、任务实际窗口及同课图重启恢复已具备；本阶段没有新真实模型/实际设备播放/真人通过。下一为材料关闭后的主动重开入口及全部A–F余项。独立56原件复核/发布正在收尾，Goal active。
