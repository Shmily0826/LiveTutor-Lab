# 阶段七：三工具设备链通过，教学质量部分通过

完整任务contract与现有active Goal继续生效。voice16首题失声、summary无tool的失败原文保留。voice17为source变化后的必要验证，不重跑普通真人打断或已有503验收。

## 已核事实

复用既有隔离store/反向图/三个固定WAV。Native假静音输入，固定PCM经正常RNNoise/ASR，room mic=false，volume_changed=false。一个CONNECT；三轮均有实际Core/SDK/Study工具和Native/扬声器输出。311秒完整WASAPI录音覆盖末轮观测终点，JSON finalized=true、无failure/timeout。本任务host launcher39604/source59244/Native28220已结束，48911/48916无listener。

| 轮次 | 实际工具 | Native PCM / WASAPI响声区间 | 语音结束到首PCM |
| --- | --- | --- | --- |
| 当前图题 | study_quiz | 9 / 18 | 8.043秒 |
| 明确错答纠正 | study_answer | 17 / 34 | 6.103秒 |
| 会话总结 | study_summary | 26 / 64 | 6.592秒 |

首轮工具参数完成在固定语音结束后2.182秒，ASR又迟130ms；本次待执行交接没有造成首题失声。首ASR到达为语音结束后2.312秒；实际设备首响为结束后8.668秒。这个限定轨迹不是所有自然停顿/opaque输入身份的证明。后两轮ASR分别迟于参数完成115ms/34ms，均在同一连接gen1完成。

新题与三轮数据库qid相同，attempt相同；错答只新增一条answer_evaluate及QA，wrong/10分。评分给“单向连接”这个rubric相关正确事实少量分，不能把原先voice16的0分套到本场。summary真实保存到同一session，Native朗读与保存summary一致。材料ID前后不变，偏好未变；同session只有question_generate、answer_evaluate、summarize_session三条交互。

## 教学质量仍有实际缺口

纠错给出了正确REZ→NUD→WEX，但把明确“从左到右、没有从右到左”的错误主要描述为缺少具体模块顺序，没有直接解释反向的证据。总结真实调用了工具，且不再将调用箭头说成数据反向回传；仍漏掉学习者请求的下一步。

总结声称学习者“先简要说明图中箭头关系”。实际当前session只有出题、错答、总结，没有一次独立的正确解释。question_generate记录的input是材料准备时的“新当前材料…简短说明…不出题”请求；请求文字不是学习者已经完成的讲解。后续需要按interaction kind区别出题材料/指令和真实学习者答案，避免把请求当作完成进度。原历史不删除或重写。

分层结论：本场三工具真实模型→SQLite→Native→实际设备路线通过；纠错和总结教学质量PARTIAL；独立叙述默认OFF且宿主准入未实现；后续自然停顿、严格英文、细字、源码纠正及真人听感仍待。没有真人体验通过声明。

本场DeepSeek新增25、app新增1，终态577/2000、56/null、tech0/0，round bargein-autocheck-20261012保留。原始JSON、311秒WAV、final-review JSON和隔离DB只在raw本地，不发布。下一步修有证据的反馈/summary语义与下一步口语，再继续其余A–F；不因小阶段结束整个Goal。
