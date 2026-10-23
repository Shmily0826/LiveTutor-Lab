# Phrase collector 第一段：本地尚未发送 PCM 离线交付

日期：2026-10-14。承接已完整读取的 contract/plan/status/blockers 和 `daily-companion-phrase-endpoint-review-2026-10-14.md`。现有长期 Goal 继续，本 prototype 不作为整 Goal 完成。额度/进程仅沿主线接续记录，未访问或调整账本；没有外部调用、host、音频、room mic、供应商或子Agent。

## 自有交付与边界

仅新增 `scripts/neko_phrase_input_buffer.py`、`scripts/test_neko_phrase_input_buffer.py` 和本文。collector 只用标准库，收已由 caller 正常 DSP/VAD/onset 路径处理过的16k mono little-endian PCM16。它不是 ASR 拼接、工具gate、owner提升、网络发送器或新的学习记忆。不修改transport/Core/asr/host/manifest/共享记录，不开启日常选项。

- `PhraseOwnership(session_id, owner_token, connection_generation)` 固定会话、opaque immutable token 与连接。Main可把实际socket、activation、input lease/权限等组成稳定token；collector不查询真实宿主，不能替Main授权。
- `PhraseInputBuffer` 默认 quiet=1.2s、max=20s、640000bytes，内段零停顿保留100ms。限制同时核 **原PCM样本总量**、原输入bytes和capture/clock时间跨度，压缩不换取更长输入预算。超过任一上限状态FAILED、全部缓冲清除、明确错误，绝不淘汰首段再发后半句。
- 仅 `speech_active is False` 且该frame所有字节/sample全零时可暂存并压缩，且须为后面还有保留frame的内部停顿。任何非零帧，即使VAD=false或只有一个值为1的sample，也逐字节原样保留；VAD=true的全零帧也原样保留。leading和terminal静音不压缩。
- quiet只在已有speech之后、确实看到VAD=false frame后开始；900ms pause不seal，达到1.2s才seal。持续speech或者完全没有speech不自动产出。状态OPEN→SEALED→TAKEN，immutable sealed batch只可取一次；后续feed不能重开同phrase。换session/token/conn在feed/tick/take/assert_current处拒绝并清空，close拒绝所有后续使用。
- `local_phrase_id` 前缀 `local_phrase_` 是本collector transaction标签，不是provider utterance/input item/response ID。没有用观察序号映射provider身份。

## Main 接入接口

示例仅说明本地API；**本轮没有把它接入宿主**：

```python
owner = PhraseOwnership(current_session_id, captured_authority_token, connection_generation)
collector = PhraseInputBuffer(owner, clock=the_capture_clock)
collector.feed(pcm16, speech_active=actual_speech_verdict,
               ownership=owner_now(), captured_at=original_capture_start)
collector.tick(ownership=owner_now(), now=the_capture_clock())
if collector.state is PhraseState.SEALED:
    batch = collector.take(ownership=owner_now())
    # Main owns exactly one downstream writer:
    # before/after every await: verify REAL session/socket/activation/lease,
    # then collector.assert_current(owner_now()); write each owned byte once.
```

feed/tick会返回当前 `PhraseState`；违规抛 `PhraseBufferError`，其 `.code` 与 `.failure_reason` 可做诚实UI说明。sample rate固定16k，不自动猜输入率或在collector内跑DSP；48k/22050输入应先沿既有正规路径转16k。所有 captured_at、tick now 和注入clock必须同一时基（当前host捕获wall时应注入对应wall clock）；时间逆行/clock在最新capture end之前明确失败。

`SealedPhrase` 包含pcm16、source/output samples、compressed_zero_samples、captured_start、speech_end_at、sealed_at、固定ownership。`take`只转移本地所有权、不写网络；缓冲后应返回现有LOCAL_ACCEPTED，不可冒称TRANSPORT_WRITTEN。已take的batch无法被collector从外部撤回，但Main必须逐await检查实际authority及 `assert_current`；变更/close后该检查拒绝，防旧worker继续向新conn发音。

每个新phrase新建collector，不隐式重置旧对象或重新取旧batch。partial downstream write/unknown delivery的失败处理由Main做；不能在失败后把take的整个batch重新feed或换conn重放。

## 离线实证

执行一次：

```powershell
& 'benchmarks/raw/neko-product-host/.venv/Scripts/python.exe' -B -m unittest discover -s scripts -p test_neko_phrase_input_buffer.py -v
```

**13 tests PASS，0.151s**。仅模块/PCM chunks/受控clock、原WAV读取，不启动宿主或设备：

1. 500ms speech→900ms false/allzero→500ms speech仍OPEN；terminal 1.2s seal，只把内部900ms变为100ms；speech blocks、terminal tail原样，source/output差精确12800 samples。
2. 900ms微弱非零pause（1/-1/256）即使false也完全保留；20ms帧中只有一个非零sample时整帧不删；speech=true的900ms全零不压缩。
3. clock tick不凭“没有帧”单独推speech结束：必须先观察false；达到quiet后seal一次，取出后重取/feed拒绝。tick不生成额外PCM或假的静音。
4. 恰好20s/640000bytes可暂存，下一sample失败并清空，peak<=640000；capture wall跨度和timer超过20s也拒绝；压缩后的低buffer量仍受原source时长约束。
5. session、opaque owner、connection replacement分别在OPEN/SEALED拒绝；已take后worker可继续查owner，但变化或close后不可使用旧authority；close清空，复取/新feed拒绝。
6. 完全无speech不seal；不完整PCM sample、未知speech verdict、NaN/逆行capture时间fail closed。
7. 原neighbor8刺激 `benchmarks/raw/voice-input/daily-picture-constraints-single-utterance-20261014.wav`，mono PCM16/22050Hz/374369frames，SHA `6b6182d69b2a0ea0e12cb8bae72be5edee5629abe65f600c2201e16242eeb93d`。使用项目隔离环境已有numpy/soxr在内存HQ转16k，按20ms chunk送collector；保守fixture将每个非零frame标speech。输出所有非零int16 sample的值和顺序与normalized源完全相同，峰值不超过上限，前后原文件hash相同。**该verdict不是实际RNNoise，不证明真实ASR/语言学句界**。没有新建/复制WAV或学习材料。

## 未接入部分与必要下一步

| 证据层 | 当前状态 |
| --- | --- |
| 独立collector源码/真实WAV bytes/定向clock边界 | PASS（13项离线） |
| transport/DSP/VAD/onset单writer和LOCAL_ACCEPTED适配 | 未接入 |
| 静音clear、真实handoff/native replacement/prefix一次交接 | 未实现/未验收 |
| free proxy接受burst、最终ASR、完整末尾约束、一次付费tool | 未调用/未知 |
| Native PCM、设备、真人 | 未验收 |

这是保存字节的保守规则，**endpoint quiet仍依赖caller VAD**：弱非零帧不会被剪掉，但若它们持续被错误标false超过1.2s仍可能分段；不会据此宣称解决任意漏检。仅tick封口时，collector保留已经拥有的短tail，不制造1.2s音频；Main应核实际连续采集的quiet tail/运行authority，不能凭local seal宣称raw provider已经收到结束信号。

Main后续按phrase-endpoint研究报告挂在真实DSP/VAD/onset之后、raw append之前，保持原onset/cancel立即运行，不再把drain batch传回stream_audio重跑DSP/onset；协调2s/4s clear、input-open/handoff、收发独立和精确commit计数。offline adapter确认byte一次性交接、每await ownership、partial失败无重放后才值得单场已有刺激的proxy验证。整段缓冲失去流式ASR重叠，不能承诺缩短响应；默认OFF和既有日常线路保持。

冻结：仅三个新自有文件；交接接口和未验收范围明确，继续长期 Goal 的后续适配工作由Main安排。
