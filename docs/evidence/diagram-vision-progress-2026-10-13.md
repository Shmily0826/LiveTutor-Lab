# 架构图理解 Goal：已开始，现有链路源码核对完成

前置发布完成：GitHub分支`codex/tutor-teaching-closure`，提交`1fa40f408354fed6822bd48b27326ce2e4dc43cc`，父提交为已发布的`c558c679`。远端ref已重新读取核对；远端master仍为f1e8f3f，原本地master仍为2c54175，受保护.workbuddy文件字节不变。独立发布工作树已归档，运行时借用的两个junction已先行解除。代码依赖、公开精简证据、Git LF规范和发布payload20文件指纹已检查。

本Goal沿用同一bargein-autocheck-20261012账本：DeepSeek累计300、Lanlan.app30 CONNECT、Lanlan.tech0；开始已用173/19/0。本轮链路核对0新增出站请求，没有启动宿主、模型、麦克风或扬声器。后续图像改动先保留在工作树，不自动重复提交/推送。

## 当前源码事实

- 当前Native Realtime客户端用api_type识别free线路，_supports_native_image包含_is_free_provider；_is_free_proxy只是VAD/lifecycle判断，不能据它否定图片能力。
- _transport.stream_image的free分支发送input_image_buffer.append，包含image_b64；发送成功后用实际事件内容发布provider frame（可能已重压缩），有generation和图片缓存机制。它是现成的像素路径，不是OCR文本替代。
- Core.streaming现有screen/camera/user_image处理会把图像交给当前会话，也有独立ASR、视觉模式、raw-frame拒绝和session变更检查。必须按实际已用native语音路径验证，不能靠跳过这些门禁获得一个虚假的PASS。
- 两个已有教学测试部署的llm_vision_enabled=false；Study_submit_image在此状态会明确拒绝。Study gateway已经根据请求是否有图片选择vision或agent模型组，并能报告vision_not_supported。视觉组的当前可用配置尚未验证。
- 当前study_read_window主要依赖OCR，不能证明识别模块连线/箭头方向。没有调用视觉模型，本Goal没有图像理解PASS。

## 下一步与验收门槛

1. 制作标签相同但箭头/连接不同的固定图，以及关系不明确的负例；答案不能仅由OCR标签推断。先核对本地图像、方向真值和输入格式。
2. 优先通过既有Lanlan.app native图像路径进行一场有界验证，记录实际发送帧指纹、被接收/拒绝的事件和模型对关系的具体答案；验证同会话换图后使用新图。需要外放则先告知；固定输入不采集房间麦克风。
3. 根据真实结果选择最小现有入口，接续图像解释/追问/相关出题/判题/纠错与课程记录；若必须使用未授权域名/视觉provider，先准备具体方案，不私自扩域名或费用。
4. 本地回归保护既有教学/打断/课程隔离，按源码、离线、真实模型和用户体验分别验收。只有准备充分时才安排一次用户实际材料的体验。

实现未改动，Goal active，继续朝完整图像教学闭环推进。源码“有发送路径”只是下一步选择的依据，不代表当前免费代理已经接受原图或模型已经理解架构关系。
