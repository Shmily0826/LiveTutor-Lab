# 阶段52：数学与代码中的竖线输出

完整[contract](../daily-companion-contract-2026-10-14.md)优先；全部A–F/Goal active。

阶段52开始：上轮为progress，51源码5c78e711+metadata39715ae已发布，当前无live场，原ledger854/78/0。删除实际source _streaming两个无条件竖线计数分支及其状态；保留既有_match_name_prefix、长度/重复/取消/DSML过滤，先离线验证真实stream_text与flush路径。该旧计数只有“围栏”注释，没有表格判定；未找到额外明确定义，不能把它当可靠安全边界。candidate _streaming SHA5cbbe7…与source4b86…仅旧discard-notice差异，保留该历史差异，本次只部署实际source入口，不覆写候选。原件独占备份phase52-before；不读Sky新材料/不开音频、不改账本。

阶段52冻结：现9不同离线case PASS；只保留实际source的已知4b86…基线并重放至63041b29993f92632ded27393aa67b54ad99eb89d09d4882c2b0de7574039137，candidate旧5cbbe7…保留。修掉两处全局第二竖线截断、逐token whitespace丢失，prefix缓冲等待首个非空白并在已知姓名检查中计入前置空白，防空白绕过；纯blank不记有效AI。保留长度恢复只保存已显示句子、generation取消尾部抑制/现DSML过滤。初始新测试确实发现原空白丢失，后续新blank保护用例发现候选空白入history已在部署前修；长度case原discard回调预期不符已有恢复路径，改为检查真实显示/history/单次请求，不修改长度实现。首轮SDK夹具曾读取旧benchmark neko-store配置，随后强制全新task临时store默认资源迁移，不启动host/provider/音频/capture、不拷用户历史。源入口helper接续及host manifest SHA5e5e385e16b064ab9e537eee3cfbd8c00d34c6ddd74b9681336ef84896b22c2a、SourceGate PASS。部署后同9通过不重复计数；raw offline SHA16ef49e2f8ab8b03b7ceff290dfa514ed0ecc5ca35dd4d1bfe7e235ef153d3c7。

阶段52唯一静音真实61启动准备：现有量具在本进程只选CONTRASTS[1:]，仅两个上轮截断问题，不重做map行序/结构/图材料。strict contrast_only、新独占61任务store、授权only、text-only/TASK_SILENT、原round2000/32事件间停止/380s；DeepSeek854/78/0起，无Native/浏览器/声音/mic/capture/loopback。preGate已PASS，目标路径不存在/三端口空；未终态不冒通过。量具就绪日志改为bounded questions避免固定three字样，未改执行/ownership/预算逻辑；首次日志缩进错误在import即拒绝，未创建61场，已修并核AST后启动。

阶段52唯一61实际已启动exec65863；此前import失败不是一次在线场。只poll该handle，不因观察超时重启，尚未终态不冒清理/模型通过。

52当前：已移除实际source流的第二竖线误截，并修独立空格/换行丢失；9不同实际stream_text离线case PASS（流/flush/历史、角色前缀/前置空白、length恢复、取消尾部、纯blank），源码/SourceGate已部署通过。唯一静音真实61只两轮：数学竖线后回复完整、空白保留，输出修复窄PASS；教学仍PARTIAL，30/100交换误判及无条件“值交换过校验”仍错。controller exit0/host forced-stop1、owned/三端口清空，无音频/捕获。账本DS862/2000、app78/null、tech0/0；下一53查现有教学/推理和校验路径，不盲重复同场，不要求human，全部A–F/Goal active。

阶段52终态：61原raw SHA ccb4335f82ec0e205c4e4b859870518c82b9e19c102ff21e06edaef8cd94f897，terminal另件 SHA92ae32c632d7e87c6eac6e3b4c1edc3b6685398afacceb594683ddfb5d5b70b4。exec65863终态0，host_exit1为已记录owned forced-stop，非自然0；cleanup/tracker无错/owned_alive[]/48911、48916、9234无listener/post61 SourceGate PASS。两轮7.485/7.018s，真实角色4 receipts、DeepSeek854→862恰8，app78不变，tech0，无Native/浏览器/音频/mic/capture/loopback。原report semantics=PENDING保留，Main另件判输出窄PASS/整体教学PARTIAL。

61独立问题分析：为了不重复已过行序，fresh store中本进程只选原CONTRASTS[1:]，没有显式带前一轮文件名上下文；角色先explore误给location_storage，再查坐标guard/route，另查未被问的stars。该量具上下文边界不能和60三轮连续场等同，后续定向问题须自带材料范围，不重跑61。实际source commit7aae20f，已shown coordinates与weather route：前者要求有限数字且abs(lat)<=90、abs(lon)<=180，后者不合法早400/下游异常502。首答保留键不缺值与范围条件方向有证，但把30/100对调说成仍通过（对调后lat100>90，反例错误），又称真正纬度120也无合法输入前提；末句route未shown时标推断可保留边界。第二答缺lon→undefined→NaN→400核心链有证，却把上次值交换一律说成过校验且多出stars相邻case。两答均越过 |lat| 完整结束，不再是竖线丢尾；第一答约两长句、第二三句且过长，不冒简短自然通过。下一53优先核现有role源码教学与推理开关/证据校验，而非反复添同义guidance、硬编码Sky答案或盲付费复测。

冻结文件SHA256：
- scripts/neko_pipe_output_patch.py: 9e8319533925710bd8687e9b1ae986de3126cf63a2609a17d5f9bb619452a981
- scripts/test_neko_pipe_output.py: 05c81b93d45e5e78d68f85a9c9e4fda0e2335a51ebc3421f5c0c88a4559e84a6
- scripts/neko_desktop_tutor_host.py: e7baa17fbd2cd462bbd4fecf79fe332dac7835a375aa35f2ff019154919a666a
- scripts/neko_daily_code_dialogue_probe.py: 005afc08cbaf41dde390e4c0f91da8faa66cebab67d4687f86e00b8d1198be3d
- patches/neko-study-2026-10-10-host/manifest.json: 5e5e385e16b064ab9e537eee3cfbd8c00d34c6ddd74b9681336ef84896b22c2a

阶段52十文件精确发布已核：commit/push 8d9bf21aaceed89c23fb9d0313e144e23be2b822 到codex/daily-learning-companion，remote exact/master仍f1e8f3f5605659f0526e43bc3b85c60ae46c85fb不变/publisher clean/Root index空，原contract SHA保持；无raw/DB/密钥/录音/备份发布。无live宿主/自有端口，原ledger862/78/0，全部A–F/Goal active。

三份工作记录按角色精简，全部精简前原bytes另存through-phase52归档并绑定SHA，不改contract/原证据。下一53已定位现有Focus/stream_text与Study教学模板，未变模型/推理开关或开新调用。
