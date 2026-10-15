# P4：角色自主指示未通过

工具说明增加明确的“指给我看/标出来”意图、无需桌面窗口标题、先status取得当前材料身份；没有位置证据的PNG不得猜矩形，建议选有语义定位器的对应HTML。测试先红后绿。新增固定WAV用System.Speech直接写文件，无采集/播放；脚本包含后续resume/404/打断固定输入。

| 场 | Study提交图片 / 材料窗口选中 | 账本前→后 DeepSeek/app | 指示结果 |
|---|---|---|---|
| native-a | forward PNG / forward PNG | 1379/118→1388/119 | 调用point status；无高亮，索要窗口名字 |
| native-b（措辞修订后唯一PNG重试） | forward PNG / forward PNG | 1388/119→1397/120 | 发出一个selector指令；material_id用了无关文件名，被服务端拒绝，accepted=false；角色称材料变化，实际两套图身份未换 |
| native-html（不同定位器条件对照） | forward PNG / forward HTML | 1397/120→1406/121 | 两次point工具调用，无guide command、无accepted；角色却说“标出来了”，属于无证据成功宣称 |

材料窗口PNG SHA为057d5bac…，HTML为1b41316b…；Study实际提交的PNG单独保存SHA和material_before/after，不将HTML换图当作Study提交。每场新任务库，未复制学习记录。没有测试程序替角色发指示命令。收到音频/transport exit0不等于指示通过。

三场上限已到，停止Native重复。没有accepted指令，所以未运行材料窗口高亮渲染检查；共享web-inspector仅核对了工具入口。不得用“角色说标好了”作为成功。

离线：新增说明契约1项、材料窗口6项（5通过/1跳过）、原始源码指示10项通过。变更前32项旧SHA三方一致并备份，部署后新SHA核对；本阶段发布使用进入P5之前的精确快照，避免夹带尚未验证的接续摘要实现。产品发布blob/manifest全项校验。

本项状态：**PARTIAL / Native自主指示FAIL**。待复核：实际Native参数/结果转述为什么未遵循status身份；需要可关联、内容最少的工具参数诊断。PNG还缺基于像素证据的区域定位途径。没有修改宿主/arbiter/传输，没有做自动重发或把错误身份替换成当前身份。

新增DeepSeek27、app3；无采集/回环/音量更改，所有场cleanup_errors为空。可听性和真人未验收。
