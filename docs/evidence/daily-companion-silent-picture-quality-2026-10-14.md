# 静音图片纠正：真实后端逐场质量

仅既有Study vision、deepseek-flash与实际SDK callback/SQLite；没有Native、浏览器、扬声器、麦克风、虚拟输入或回环。复用已有diagram-input-sky-dark.png，不重新生成图。只使用本任务隔离store，原用户历史不碰。raw JSON/host logs/数据库不发布。

## 场景及结果

| 场景 | 实际新增请求 | 事实与限制 |
| --- | --- | --- |
| recheck21 | DS +4、app +0 | 首次提交已有图只定位节点，随后明确current_picture并传错误旧summary。实际SDK/模型/SQLite证明旧summary不作为source，当前材料身份与question保留。逐字读对「天气未命中 / 百科 HTTPS」；但把未命中同时套给百科，教学PARTIAL。两call墙钟5.180/3.803s。 |
| recheck22 | DS +4、app +0 | 新diagram branch qualifier规则后，复用同一已保存图片。中文两句区分天气直接条件与百科缓存未知；随后真正auto裸纠正＋上一轮teacher text＋单次English要求，当前原图再次使用，旧text丢弃，先前interactions/QA不变。但对学习者错误的「都缓存命中」开头说You are right，并混入7个汉字；纠正/严格英文FAIL，不能拿两句英文主体算通过。两call墙钟5.064/3.277s。 |
| recheck23 | DS +2、app +0 | 新挑战极性规则及自然语言标签English规则后，只补一call，跳过已过节点/中文场景。正确明确weather miss而非hit，没有无依据赞同，也保留百科缓存条件未知；仍原样引用7个汉字，严格纯英文FAIL。先前interactions/QA不改、same course、source/identity保留。墙钟4.778s。 |

三份raw均finalized，Python probe terminal/exit0表示后端/来源/保存检查完成，不代表全部教学语义PASS。English的两次FAIL都保留；最新实际store源码与canonical llm_prompts/study_avatar_tools逐bytes匹配，最后input确实包含English标签指令，不能把失败归因于没部署。停止这条仅靠prompt重复尝试，继续其他本地工作；不增加无谓请求。

## 事实复核来源

主Agent事后核对原Sky Scout HTML中upstream-fetch的可见SVG标签为「天气未命中 / 百科 HTTPS」。这条HTML检查没有给模型，也不冒充其PNG视觉证据；PNG模型本场只接已有截图与教学上下文，没有给HTML/SVG属性或源码答案。

为审查推断，CodeGraph按精确授权路径读取当前Sky Scout server/src/weather.js 与 server/routes/star-details.js。weather的cache命中早返、inFlight复用与实际fetch分开；star-details验证name后直接HTTPS fetch Wikipedia，所读route没有cache未命中条件。这是独立源码事实，不等同于图中说明、历史图的全部源码版本或角色自主选CodeGraph。第一次猜错文件名的探索fallback混入同级项目结果，未采用为证据、未发送模型；精确命中后只采用sky_scout/前缀两文件，不更新索引或修改Sky源码。

当前图明确有weather miss文字，而百科缓存条件图中未知；不能因为同一共享箭头就推广所有分支条件。后续通用提示已保留该限定，实际22中文和23英文主体均遵守这处限定。尚未证明所有密集字和相似图都可靠，也没有声音和真人新证明。

## 当前预算与进程

同轮bargein-autocheck-20261012：591/2000、Lanlan.app56/无固定累计上限、Lanlan.tech0/0，不重置，+10 DS不是账单金额。三次宿主已清理；48911/48916实核free。本地task policy audio_allowed=false。

下一步保留严格英文FAIL作为具体待办，优先审查阶段九源码并发布默认关闭的phrase及材料纠正增量，再完成独立narration host权威保护等静音可做工作。声音设备与真人依旧等待新的明确授权。
