# 最新声音边界：只允许需要时的扬声器输出

用户在阶段十发布后明确更新：

> 现在什么情况了，现在可以让你用扬声器了，麦克风你还是别用，因为这边比较吵，但是可以用扬声器如果需要的话，我给你打开4%你需要的话可以用，然后继续吧

本指令优先于此前全部严格静音。需要时可用用户设置约4%的扬声器；Main不读取/修改系统音量，不自行调高。仍不打开房间麦克风或任何麦克风捕获路径，不初始化物理/虚拟捕获设备；固定WAV可在内存读取并发送。真人麦克风继续等明确“准备好了”。输出回环此前被严格静音禁止，本次只新增扬声器授权，暂不恢复回环。

先核输入/输出分离，再恢复声音测试。既有Native/voice probe会创建fake input并允许renderer getUserMedia，不直接按这个路径启动。它虽不采房间声音，仍有捕获API初始化，不能借“无房间mic”冒称符合当前完全不用麦克风的边界。先交付受审查的输出专用入口，在任何getUserMedia/设备枚举之前拒绝捕获，只允许网络PCM到扬声器，固定输入由内存/WS注入。未证明这个入口前，保留混合Native/voice/common startup的audio_allowed=false拒绝。

本地policy区分speaker_output_allowed=true、microphone_allowed=false、capture_devices_allowed=false、loopback_allowed=false；audio_allowed=false目前表示未审查的通用混合入口仍拒绝，不表示用户没有授权扬声器。新的输出专用路径须读speaker权限并强制禁捕获，不能简单把通用开关改true。

已有阶段九/十静音和无设备证据为历史事实。之后实际扬声器播放、PCM收到、模型/SDK通过、真人评价分别记证据；输出设备播放不等于人耳评价。只有Main安排在线与共享ledger。沿用bargein-autocheck-20261012不重置，DS594/2000、app56/null、tech0/0为本指令开始时实核；局部阻塞继续其他任务，实际完整交付才完成Goal。
