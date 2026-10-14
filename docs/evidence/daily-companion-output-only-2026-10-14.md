# 阶段十一：允许扬声器，拒绝捕获

当前Goal继续active。原contract、用户后续音频授权和四份接续记录仍是执行依据。用户现在允许必要扬声器约4%，仍禁止麦克风；Main没有调整系统音量，没有房间/物理/虚拟输入设备，也没有回环。原静音阶段事实保留。

## 实现和证据

增加source HTML bootstrap：原HTML保持为inert JSON，capture policy安装成功且receipt/readonly成功标记一致后才加载原应用。拒绝现代getUserMedia/getDisplayMedia/enumerateDevices、legacy getUserMedia和独立SpeechRecognition两个构造器。安装失败可见拒绝，原应用不执行；异常编码/超界HTML返回503。输出API保持可用，但本段检查没有调用输出构造器。

host --source --output-only与Native --output-only使用独立speaker权限，旧mixed音频权限不被放开。Native先验证host headers和当前JS SHA，再用fresh UUID userdata避免旧无保护缓存；禁止任何audio_input、不带fake capture flags。source replay只接受已知preimage或精确自身补丁，两实际树同步并有manifest指纹。没有全系统禁用麦克风的声明，保护范围是本任务受控source/Native页面。

双读内容/SHA的P2审查问题改为一次bytes快照。Main实际部署ASGI单快照回归6通过，前面ASGI/权限与旧静音9通过、Node capture14通过；真实shared web-inspector Chrome成功/失败DOM/title/截图通过。当前连接发送JS和closed拒绝已运行Node表达式、NativeTelemetry相关3通过。窄审报告已确认双读P2关闭。这些是源码/离线/浏览器证据。

## 两次有界实际启动

复用原单条中文0.9s停顿WAV与recheck21既有Sky图，不重新制作图、不给原用户DB写入，不重复paid图片准备。WAV SHA 6b6182d69b2a0ea0e12cb8bae72be5edee5629abe65f600c2201e16242eeb93d。

25：Native实际出现一个窗口，capture receipt installed且readonly flag true，无fake input。在显式start_session前旧Python控制连接被Native接管关闭，停止并清理；DS594/app56不变，没有提交输入/PCM。未绕过旧控制权。随后修probe仅在output-only使用Native自身当前socket，未修改server旧连接检查。

26：新Native仍capture receipt installed，八捕获入口阻断且readonly；当前Native socket显式start_session成功，app56→57，DS仍594。固定WAV按原节奏经21秒内存/WS发送，输入结束墙钟1791951133.486、末语音估计1791951130.465。最终wire只有三次session.update，没有audio.append/ASR/教学工具或PCM；有界等待后turn_timeout=true，正常清理。实际截图显示角色加载；不能把角色加载或session_started当输入已被provider接受。当前研究捕获缺席时的server输入lease准入，不把超时说成自然停顿修复成功。

26：**NATIVE CAPTURE GUARD PASS；PROVIDER CONNECT PASS；FIXED-INPUT TEACHING FAIL/PARTIAL；自然停顿未验；物理播放/真人PENDING。** 本次没有音频输出事件，不认领已使用扬声器/声音通过。原physical/loopback checks仍失败，另有output_only_native_acceptance分层字段，不删除物理检查来制造PASS。

私有证据在benchmarks/raw/evidence/daily-companion-20261014-output-phrase25/26.json、对应console/host logs及26.native.png；不发布录音、历史、DB、本地权限policy。ledger round仍bargein-autocheck-20261012，DS594/2000、app57/null、tech0/0，不重置、不跨供应商。两场自有进程已经结束，48911/48916当前空闲，不凭旧PID清复用进程。

## 下一步与范围

只读核实际lease准入，准备符合当前controller协议的固定输入方案并先离线验证，不伪造麦克风采集、不放宽server身份围栏、不无限CONNECT。失败局部记录后继续其他A–F。phrase仍default OFF；无ASR场不够证明phrase正向或普通打断回归。

独立主动narration仍关闭；它是后置增强，不应阻止现有Study工具角色教学的日常交付。仅输出入口尚非整套日常版本或最终真人验收通过，集中体验仍等用户明确准备好了。
