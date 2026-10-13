# 阶段六连续教学设备验证：部分通过

原 Goal active；完整 contract 及四关键边界继续生效。不采房间麦克风、不调系统音量；实际账本沿用不重置。阶段六仍未发布。

## voice15：量具选错输入路由

固定文字由创建语音会话的控制连接发送；Native 窗口打开后该连接仍有语音输入权，但没有新窗口的文字控制权。实际回执 `CHARACTER_SWITCHING_TERMINAL`，工具/PCM/设备响声均0，量具最终未发现新题而停止，原证据保留失败。没有为了测试绕过或弱化已有权限保护。

终态539/54/0，exec74250已结束，Native48836/host55300清理。文字实验选项现在在启动前明确拒绝，不让同一路径再次消耗连接。

## voice16：三固定 WAV，经正常语音入口

只复用已有隔离store `neko-daily-speech-acceptance-20261014` 和当前reverse图。新增输入是Windows本地慧慧语音写出的WAV，没有播放合成声到房间；音频经既有RNNoise/Native ASR入口。Native自身输入设备为假静音文件；实际输出由WASAPI回环记录。

一个CONNECT，三轮：请求当前图方向题 → 明确错误答案“所有箭头从左往右” → 总结错误及下一步。

| 轮次 | 真实结果 | Native PCM / 完整回环 |
| --- | --- | --- |
| 图题 | 保存正确图题、参考 REZ→NUD→WEX、full材料origin与题ID；Native工具scope被后来ASR撤销，未念出题 | 0 / 0响声bins，未通过 |
| 错答纠正 | study_answer真实调用；同原题唯一grade/QA，wrong、0分，纠正 REZ→NUD→WEX | 15 / 40响声bins，本场评分路线通过；回复只有一句，没有满足两句 |
| 总结 | 角色确实提到错答，但没有调用study_summary；自行说“数据反向回传”，不能用它证明图中的调用语义/存储总结取用 | 18 / 37响声bins，音频实际有，但教学/绑定未通过 |

图题内容为“根据图中关系对照图，三个模块之间的箭头连接方向是什么？”。题目与评分的qid一致，SQLite已有wrong_questions/mastery/FSRS各1条；原历史保留，没有清数据库。首轮输出被撤销不能因SQL有题而声称学习者听到了题。

首轮日志在09:49:43同时出现quiz dispatch与 `realtime tool work dropped stage=scope_retired reason=user_turn_replaced count=2`，原scope1/current2；ASR随后抵达。真实问题是工具早于识别完成进入原scope，不能随意把过期owner重新认领为新owner。还需定向offline输入时序修复；speech gate仍opt-in默认OFF，普通真人打断保护保留。

整场三轮未重连，第二、第三轮可在静默后继续得到新声音；本地代理的20秒读取deadline已移除。完整245秒回环覆盖本场末轮观测终点，总77响声bins。它不替代material reconnect gen2首次输入前长quiet的精确重新验收，也不保证远端供应商所有idle情况。

## 新审查修复与后续

独立host审查发现量具固定245秒不覆盖所有允许的三轮上界，并非本场已截断。Main在本场terminal后改为三WAV总时长+每轮padding/75秒deadline/收尾/DB读+余量计算，输入总长最多120秒，host/communicate也有对应有界期限；保存完整WAV结束时间并核覆盖末轮。相关离线4checks过，未为量具修复重复paid本场。

角色guidance补强：图题省略伪造topic；评分调用study_answer；错误/进度回顾先调用study_summary；调用箭头不自动等于反向回传。这个修正仅source/启动时应用，尚未模型复验，不把guidance等同可靠路由。

当前终态 DeepSeek552/2000、app55/null、tech0/0，round `bargein-autocheck-20261012`不变。exec52499结束，host launcher14032/Native2584不在，48911/48916无listener。没有活动音频/online。

原始证据仅本地：voice15/16 JSON、完整voice16 WAV、`daily-companion-20261014-teaching-voice16-final-review.json`、实际host日志、对应隔离Store。总体 **PARTIAL**；grade实际模型/Native/设备通过限定本场，quiz朗读/summary工具/语义仍待，真人体验未做。

下一步source/offline先修同条语音的ASR/工具epoch时序和summary实际证据路由，再必要定向验证；局部失败继续queue/细字/源码纠正等，不结束整个Goal，不为重复已有成功或耗额度安排测试。
