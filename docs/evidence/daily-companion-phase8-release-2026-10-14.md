# 阶段八：总结接续与真实源码纠正

承接已发布阶段七，不重新验证普通真人打断或已过三工具设备路线。完整任务 contract 与现有 active Goal 继续生效；当前阶段结束不代表 Goal 完成。

本阶段解决重启后总结没有使用已有错题的问题：复用现有按课程过滤的互动，将此前会话与当前会话分开；出题材料请求不当作学习者完成讲解。已有评分及下一步保留。再从已查询的 recent_answers 投影最多三条公开评分记录，使旧错题被后续老师消息挤出八行窗口后仍可取用；不新增数据库、SQL 或修改原历史。明确题目焦点优先相关答案，省去无关旧讲解。纠错规则区分反向关系与遗漏细节。

| 证据 | 结论与边界 |
| --- | --- |
| quality18 实际 Study/SDK/model/SQLite | 总结接续失败保留；当前 Sky Scout 第14–19行两句正确说明交换经纬度取值不会使固定 lat/lon 键缺失。没有新增 Native/设备/真人证据 |
| quality19 summary-only | 先前八条互动投影后的真实后端通过：明确此前错答、REZ→NUD→WEX 和下一步，原记录不变；不扩张为新评分锚点的真实模型通过 |
| 最新 summary 定向离线10 + 原 summary1 | 实际 prompt/SQLite/两课程/重启、旧题被12条消息挤出、范围/隐私/去重/0分/当前题保持通过；评分锚点及聚焦规则仅此层通过 |
| 部署指纹 | 26产品 source 与固定 daily plugin-code 全部匹配；host 无修改，仍为阶段七；无需为 prompt 重装或换 supplier |

本阶段没有新增音频会话；累计 ledger 实核 DeepSeek581/2000、Lanlan.app56/无固定累计上限、tech0/0，沿用 bargein-autocheck-20261012，不重置。quality18/19 均终态且自有宿主已退出，没有活动 Native/录音/在线模型任务。原始 JSON、录音、用户学习 DB、密钥与无关脏改动均不发布。

相关报告：summary-interaction-roles、summary-continuity、summary-grade-anchor、phase8-backend-quality（均为 docs/evidence 下 2026-10-14 文件）。启动、支持范围及一次10–20分钟集中体验见 daily-companion-use。真人必须等用户明确“准备好了”，不夜间采房间麦克风，不提高系统音量。

下一步继续自然停顿实际 transport/Core 接入及离线权限/发送计数检查；未发送 phrase helper 尚为默认关闭的实验原型，不在本次产品发布范围。独立叙述宿主保护、细字纠正、严格英文/术语、首次长静默及真人听感继续待验，局部阻塞推进其他 A–F。

发布候选验证补充：隔离 worktree 首次直接运行因被忽略的基础插件 constants 缺失未到断言，不作通过证据。随后只借原工作树基础插件源码，SOURCE 与测试路径仍为候选，11项实际检查通过；没有复制用户数据、配置、录音或启动宿主。26产品 canonical LF 字节匹配 manifest；Windows checkout 的既有 static/main.js 换行转换与 Git blob 指纹分别核对，不把 checkout 换行当产品改动。根工作树 index 保持空、原脏修改保留。
