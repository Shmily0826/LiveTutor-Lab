# 阶段61：固定语音离线分析与最小诊断补齐（SOURCE/OFFLINE通过，自然停顿仍待）

上一Goal turn已发布ba309dc并取得真实计时/失败证据，属于进展。先读完整四记录及60报告后继续；不重试模型线路、不启动任何宿主/设备/Native，不mic/capture/loopback/播放。原账本890/2000、app79/null、tech0不变。

复用原daily-continuous-followup47.wav（voice-input目录按原SHA定位），不重新合成/修改音频。离线重建现控制器48k重采样+1秒前垫/3秒后垫，其有效speech end与51原报告精确一致。原WAV22050Hz单声道PCM16、199028frames、9.026213秒；内幅度<=300连续至少150ms段为0.932500/0.474458/0.477958秒，另有首尾。阈值标签不是RNNoise或provider VAD。

51真实第三delivery：source154046/output138294/written138294，差15752样本=0.9845秒；现buffer只压缩有后续保留帧的exact-zero内部段，不压缩前导/末尾，不删除非零弱音。原报告没有记录实际RNNoise后PCM或压缩位置，不能把源WAV冒送出PCM，也不能靠原ASR到达时间唯一判断provider端点。

待补仅诊断：原source样本坐标的压缩区间（有界）、batch digest、每块本地socket写入计数/时间及captured_start估计。不改PCM字节、门限、节奏、路由、分轮或普通打断；phrase/AUTO仍默认OFF。本地写入成功不是provider ACK。源码与部署旧版本已核并独占备份phase61-before，原51 FAIL不重判。

## 本轮实际交付

SealedPhrase追加源样本坐标压缩区间，最多32段并明确truncated；transport日志追加输出batch SHA256、采集起点估计及每块本地写入样本数/时间，写入最多保留32项、总计数不截断。元数据不是音频、正文、权限token或provider ACK。源PCM、门限、节奏、默认phrase/AUTO开关及打断处理均未改。

现日志解析器保留这些有界元数据并验证hash格式、区间范围/排序、计数守恒、嵌套写入字段白名单；旧日志仍可读。非grading的phrase probe也会导出该诊断，避免为取得协议证据强迫跑评分链。旧51原件未回写补字段，没有伪造历史压缩位置或ACK。

两helper部署先核旧SHA并备份，更新host manifest后SourceGate PASS。首次35项运行中有1项读取的是旧部署transport而缺新字段；部署后52项通过。扩展60项中只有旧打包清单测试失败：其硬编码10项，而当前已发布patch.TARGETS为17项、全部在host manifest固定。只更新该显式清单到现有17项并单项复核通过，不改任何runtime patch目标/打断逻辑，不因测试删既有功能。

分组去重为95个不同SOURCE/OFFLINE case（新4：压缩坐标字节重建、有界压缩位置、富诊断/隐私、无效诊断拒绝；其余原回归）。52组与60组重叠17项；没有将重复重跑计数为新增通过。后续只为新跨层日志断言重跑18项、写入32上限断言1项、旧清单修复1项。初始FAIL保留，全部最终相关断言通过；不声称95在一个命令中一次全跑。

## 原场进一步事实与边界

离线数据raw SHA256 ceebf52e444b1b283439c5ef81b99f8f2926d01a1aa6493c6b5af9bfc9c36df7（不发布）。原第三ASR分别在868.209/873.461到达，两个response.done为不同ID，但没有response.created或speech_started/stopped记录；不能把response.done直接当用户端点，工具调用也可能形成响应生命周期。旧51严格失败及连续学习PARTIAL不变，不能由本轮分析改成自然停顿通过。

原9.026213秒源WAV，按现控制器前1/后3秒静音拼接为13.026208秒，阈值speech end9.215104166666666与原报告精确一致。这只核输入刺激/组装，不是历史RNNoise后PCM重建。已有送出sample数量相等，不证明代理已完整接收或用作同一逻辑轮。

## 当前状态与下一步

本轮无外部调用、服务/Native/浏览器/设备/扬声器/麦克风启动；账本原890/2000、app79/null、tech0保持。原WAV/51 raw SHA仍原值；未修改学习DB、Sky源码/索引或原图。SOURCE/OFFLINE通过，provider自然停顿、实际发音及真人体验未通过。

下一62优先推进A/E/F：受控材料窗/指示的实际UI操作、材料切换及恢复，不因模型线路暂时失败停Goal。B新诊断可供以后有必要的有界场使用，不为补日志立刻重复51或放松验收；完整A–F/Goal active。
