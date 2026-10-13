# Native 材料更新与旧音频退役：阶段五源码 / 离线

原完整contract继续适用，Goal active。上一阶段5369c90是已发布基线，本阶段源增量尚未commit/push。真实模型/跨进程控制/DOM取消/设备换图/真人均待新场验证；不借continuity10正常语音路线声称这次取消已通过。

## 生产端与宿主

四产品文件沿用既有Store/state lock：真实保存接受后产生before/after course/session/image+OCR identity，boot_id本plugin实例随机hex、change_seq递增。通知精确已绑定角色、blind/visibility=[]/非空控制marker，经原SDK push通路，独立于默认off/节流的叙述EventBus。接受相同材料、invalid/wrong course/store拒绝不发；明确source text只绑定course/session，image-only变化不取消该输出。end/start是独立事件；A→B通知未提交后，B→C仍对旧A输出target发最新sequence纠正。仅正常current非degraded native explain返回binding，SDK submitted不等于host取消完成。失败/unknown/cancel记录真实状态，不删学习历史。生产端11真实wrapper/entry/session/freshSQLite/push-stub通过，报告见material-control。

新 `neko_material_audio_patch.py` 重放到四宿主文件：ToolCallingMixin、character_runtime事件入口、_tools.note_user_turn_started、tts_lifecycle交付守卫。可信注册来源plugin:study_companion、精确target/blind/source/channel核对；模型文字或其他来源不能当控制。绑定复用actual batch entry owner，保持未announce响应原fence，不重猜provider response。Host-only binding从provider输出剥离。事件先于tool return时保存小型runtime control cache；seq/boot/new output拒绝旧事件，最新after可纠正丢失中间事件。

只有当前source/provider/scope/connection/socket/activation的旧教学输出能退役。独立task负责有界swap，scope退役取消正在绑定的tool也不会取消swap；不伪造真人speech onset、不replay PCM，不引入response alias。正常close/connect均会advance工具scope，故另在现有note_user同步计user epoch，保护锁等待期间新input，不改原onset/advance时机。专属native output hold只暂停旧connection/epoch交付，不给新input或TTS安装fatal。

精确cancel在frame锁内，不拆header/blob；cancel完成后、close、listener drain、connect、listener restart、cleanup status等await边界重新核owner，connect只允许原generation+1，不采用更晚胜出的连接。最多一次正常connect得新physical output token，失败不重试、明确停止。cancel已不可逆而同旧连接只有新input到达时，旧token不能恢复：明确待手动重启语音；真实新connection接管则不close/disconnect它。仍需实际设备确认旧声音停止及新材料恢复。

## 证据

22项actual patched host/event/delivery methods + owned fake provider/socket通过，非线上模型：trusted/failed/malformed来源，原batch owner，control-before-result，missed/late event，immutable source，scope/socket/connection/activation/barge替换，header/frame锁，新input接管，连接错误/单次重连，swap timeout，listener晚完成，generation在drain/connect/cancel/status await变化，工具自身取消不伤独立swap，native-only交付hold，以及不可逆cancel后显式重启状态。

受影响原课程记忆6、image guard4、failure guard5、native material guard9通过。旧AST fixture需显式绑定新增3个material helper，已补；没有为了延长工作重复旧真人/图像出题验收。四个新宿主目标fresh git LF原文件→generator重放，与两runtime字节相同，第二次重放不变、AST过；两个本地已部署draft只允许精确helper SHA升级，未知改动拒绝保留，不重复插入helper。双runtime fingerprint及固定daily产品23文件匹配封存，启动校验覆盖新文件。

## 尚待

- 一场必要真实原生/设备：旧回答正在播放→更换既有另一图→准确旧token cancel→回环旧声停止→新token/新材料回复。SDK提交、controller控制、DOM停止、设备声音和真人分别判定。
- 成功binding目前覆盖native explain；quiz/grade输出、已安排communication general/solution narration还需材料provenance和真正交付时核对，不把此路径称全部教学声音取消。
- 材料cancel未submitted/unknown状态已有API字段和日志，前端直观提醒仍需补齐；不能只保存状态却让用户误以为停止成功。
- continuity10细字『未命中』漏字仍需纠正后重新查当前材料；和取消独立。普通真人基础教学/打断继承原验收，新增能力仍待集中体验。

本阶段外部请求0、CONNECT0，无房间麦克风/音量变更/活动宿主。账本仍bargein-autocheck-20261012，458/2000 DS、47 app/null、tech0/0；不重置。局部未验收不阻塞其他A–F，Goal不标完成。

## 后续实测与修正（覆盖上文旧计数及尚待状态）

replacement11/12 都已结束，正确新材料解释/实际播放与旧音频取消是两件事。两场 `material_control_submission=[]`、0精确cancel/0stop/同旧token，取消FAIL_OR_PARTIAL。12的路由日志native/core、trusted/current/free=True、tts=False，不能将旧输入lease假定当确认根因。累积账本501/2000、app49/null、tech0，同round未重置。

UI14检查已通过并提供unknown/unsubmitted提示；初始化browser200/无错误不足以称实际warning已显示。27宿主方法守卫已通过：可信current角色路由现独立于Native输出捕获，仍拒绝stale/absent invoking source及其他plugin；复制args不改模型原参数。结构日志只记role长度/captured/结果种类/record合法性，不录问题、图片、角色全文或密钥。输出捕获增加native_class/takeover/token/abandoned/call_matches可观测项，实际捕获失败原因尚不能断言。

真实SDK/producer探针material-sdk1（2本地HTTP桩请求）证明显式_ctx和binding保留、指定target提交；SDK审查同时确认v2 facade无当前角色fallback，缺ctx会空target。进一步material-core-sdk2从patched actual core，经真实ToolRegistry和actual `_remote_dispatch` 代码、真实SDK/producer/local stub，四项Core检查过：binding到达、当前owner绑定、provider剥离、原args未变，SDK指定角色提交也过。该Core fixture仅输出owner是假provider/socket，未连接Native、未播放，不能当设备cancel证据。两次均外部egress拒绝、无voice/房间麦克风、global ledger保持501/49/0，owned host finally清理。

四host fresh LF重放、部署双副本/二次重放/AST匹配，未知helper修改拒绝，manifest新27/11/UI14 source-offline封存、23产品匹配。本阶段仍未发布；下一次实际设备仅在这些具体修正后做必要补证，不复跑未修改场景。quiz/grade/narration provenance、细字纠正、真人新能力仍分别待验，Goal active。

replacement12语义更正：两个native_reply都是旧forward；新图API才是reverse，不能称角色更新正确。scope3实际text=WEX→NUD→REZ，原wrapper把text看成immutable literal source、不发图且不绑定图identity，所以image-only change可返回空submission；这不证明target未注册。首轮args未知保留unknown。现明确current-picture request覆盖native stale text摘要，改schema冲突、保留literal源码独立语义；missing picture诚实degraded。nativeguard12（新3项含模型await替换）及生产11/语言4/记忆6/image4/failure5通过，23部署再次匹配，仍非设备证据。不要为绕开此真失败构造paid image预置，下一场既有reverse→forward/WAV补证。

阶段实测已完成：13 exact旧token/native stop/WASAPI静音过但无input20秒关闭、整体partial；14 fresh输入新Native token22PCM/正确REZ→NUD→WEX/全WAV51响声bins和cancel后静音/正常terminal过，537/53/0，无活动宿主。详见material-replacement-device报告，不升级真人/长quiet/其他输出。最新source guard13/host28和review finalized/末轮terminal/newNative前缀加固通过，负例只offline；14当前图正例/cancel算法未改。阶段五仍在审查发布，Goal active。
