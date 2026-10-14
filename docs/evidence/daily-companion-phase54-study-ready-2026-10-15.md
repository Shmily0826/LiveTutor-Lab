# 阶段54：Study入口就绪与UI测试维护

完整[contract](../daily-companion-contract-2026-10-14.md)优先；完整A–F/Goal active。

阶段54开始：53源码c7dcec4+metadataffc8db5已发布为progress，原ledger868/78/0/无live场。先维护原NodeVM product-ui夹具当前函数依赖，真实函数仍从当前main.js截取，不能填假产品状态冒通过；再用共享web-inspector测正式Study完整异步Ready。CLI当前DOMContentLoaded即取样，47Refreshing快照不能推持续故障；需要任务表面内等待真实状态的观察量具，保留protected_html/CSP/录音防护。暂不调用模型、不做真人，不重跑62数值场，短答/Native桥接继续待办。

54开发冻结：原product-ui NodeVM更新到当前真实状态/函数依赖后PASS，保留既有授权OCR/无fallback/换课清理/输入出题/串行action断言，并加字段先展开不捕获。仅mock Plugin调用与DOM，无实际OCR。新只读relay/observer边界5离线case PASS，固定127后端、只允许4个读取entry及locale/status参数、拒模型/捕获/清图/改课/大body/外部绝对URL；不改产品CSP/防录音策略、不伪造API结果。实际63将复用已存在54任务store，不复制/重置DB；host text-only/offline-egress/API0，同round2000，采用deepseek避免free线路初始化，退出只恢复原coreApi字段。复用creationtime/remember_children/stop_owned_tree，记录host+inspector+新Chrome子树，锁保护tracker；只用全局web-inspector，不装浏览器依赖或查个人Chrome。relay仅捕获bootstrap promise，完整生产函数/SDK运行，等待结果gate后DOMContentLoaded截图；该观察副本不冒未修改字节的真实用户Chrome/Native/语音/模型/human。原868/78/0，无live场，随后唯一63。

冻结SHA：
patches/neko-study-2026-10-10-product/static/product-ui.test.cjs e85fa494f6e0a04a23e17eaa3f387e61a3f31b7990736cbf1be380a951322a14
scripts/neko_study_ready_probe.py 64a3e65ff536efb3c44410f37c75b2a65f07407097be6c94c612976cb8a792f4
scripts/test_neko_study_ready_probe.py 085f8b9c09cdeee650287a3fbccecdeed6b52e88e4c1f09070723a8ebf548e9a

63终态FAIL保留原JSON：浏览器POST /runs HTTP403；reading_entries仅study_status，未完成bootstrap，不认Ready。已核源码mutation_auth仅信任明确来源，随机relay不在默认白名单；不是正式页面故障证据。修量具使用后端现有NEKO_PLUGIN_MUTATION_ALLOWED_ORIGINS，仅本场子进程精确绑定relay origin，不改默认/全局配置，不剥离/伪造Origin或凭据，追加来源头保真检查。6不同relay case PASS，旧UI夹具仍PASS；计划唯一64验证变化。63原868/78/0未变，owned已退出/四端口无listener，原QA与现只读快照一致；没有音频/麦克风/模型。
64终态PARTIAL：9个DOM checks全通过，真实bootstrap/刷新/课程可见/文字防护成立，但两个study_memory_list_decks读取被量具拒绝导致console403，不冒整场PASS。已核现有entry仅list_decks读取，无模型/写入；量具新增仅limit100/整数offset0–10000/locale边界，7不同离线case PASS。原63 SHA dff49f37f1fb3a794ef0c6da66fcc2979da88ff66dcb4c4c1101e1d53e7f2498；64 SHA 90d6a5e5f161a8d30f8a44d8b87680b224fcce26c8c5202f5c72f581fb77da03。64 QA前后同SHA/原868/78/0、owned退出/四端口空。截图实见页头右侧按钮被裁，列入下一阶段55修复；不据horizontalOverflow=false冒视觉通过。唯一65补全已核只读入口后再检，仍不调用模型/音频。

65终态PASS，完整观察副本bootstrap/SDK与真实refresh9 DOM checks通过；8个真实读取run全部succeeded，5种只读entry，无拒绝/console/page/network错误。selected course前后daily-window-fixture54-A，status=Ready / Companion，文字capture保护安装成立。原启动前/运行中/退出后QA均0条、SHA4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945；不冒整库所有字段不变。原ledger868/2000、app78/null、tech0/0完整dict相同。65 raw SHA cffc7ac176ae6fc4c69267f6f443b93289feb1a6fa6a86d059aaee7d01be6803；63/64原失败不改。仅观察副本捕获bootstrap promise，原main SHA add5f2c643e41e11654b9929429e6da82d55eab61fc30c5d876a043cb3c13beb已匹配当前source，不冒未改字节用户Chrome。未重做62模型/设备/human。

exec8562终态0；owned host forced-stop1，非自然退出0；creationtime实核全部owned已死，48911/48916/9234/54008无listener，config provider恢复，SourceGate无异常。当前无live场。全局inspector实际PNG已查看：虽horizontalOverflow=false，页头被overflow:hidden裁切，视觉仍PARTIAL。下一55修页头适应真实可用宽度，保留身份和功能，不以DOM Ready掩盖可用性问题；之后继续D教师/角色语音桥接及B短答。54生产main/index/manifest未改，只有测试/量具/记录；发布不含raw、截图、DB、密钥、音频或备份。完整A–F与Goal active。
