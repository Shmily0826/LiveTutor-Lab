# 阶段35：fresh voice 配置与 healthy-empty clear 独立窄审

日期：2026-10-15。审查范围限 `neko_desktop_tutor_host.py`、`test_neko_first_voice_start.py`、`neko_native_grade_patch.py`、`test_neko_native_grade_route.py` 本阶段增量及其精确 callee。已接续 contract/plan/status/blockers。未修改实现、共享记录或 manifest，未部署、启动宿主、联网、调用模型或接触声音/捕获设备；未读用户学习数据库、修改账本。

## 结论

本范围未发现新增 P1/P2 阻断。两项修复有源码及独立离线证据，可以交由 Main 按旧 SHA 门禁继续部署。该结论不是修后真实连续学习、Native PCM、实际可听或真人验收通过；原场47 FAIL 保留。

## Fresh 配置来源与时序

- `apply_free_voice_route`（host 第366行起）仅在任务 store 的 `N.E.K.O/config/characters.json` 不存在时，调用指定 `SOURCE_PYTHON`，cwd 为指定 SourceApp；20秒 timeout、`check=True`，失败不继续冒称配置完成。
- 子进程执行的是官方 `config.get_localized_default_characters('zh-CN')`，没有复制用户角色卡。官方 `config/character_defaults.py:232` 在明确传入语言时不进入 Steam language 查询分支；简体中文路径 deepcopy 官方常量并设置官方 prompt，未读取学习历史。
- 子进程将 APPDATA/LOCALAPPDATA 指向此任务 store，三个 `NEKO_STORAGE_*_ROOT` 均指向其 `N.E.K.O` runtime，并设置 task silent、dev text-only 和 do-not-track。官方 `config/network.py` 的 import-time port 配置读取使用已隔离 APPDATA，未回落真实用户 roaming 路径。这是定向源码核查，并非全文件系统访问审计。
- 写初始文件使用 `open(..., 'x')`；已有文件不被初始 seed 覆盖。随后沿用原 voice 字段选择 yui、原 tutor guidance 保留规则。已有坏 JSON 直接失败，原 bytes 不变，不重建覆盖。
- host source 启动分支第1085–1089行先 voice seed，再 `ensure_character_models`，再 role guidance；均在 launcher 建立角色前完成。未因本次修改把 text-only 启动改成 voice。

## Clear 例外的精确范围

- DAILY_UPGRADES 仅替换实际 `_audio.clear_audio_buffer` 的 pin poisoning 行；原 `_native_phrase_protects_input()` 前置早退、wire clear、route observation reset 和 resampler reset 保留。
- 仅 AUTO_GRADE 环境值严格为 `1`，且 `_rearm_empty_study_question_pin(pin)` 成立时，clear 不把原空槽置 invalid。此时不读取新题，不改 scope、connection、authority、driver 或 delivery，也不把 pin 直接改成新题。
- 现有 rearm helper 要求已确证 empty_question、未 invalid、scoped literal True、原 provider/socket/generation/token/scope 和同步 Core authority 均当前；必须是原 driver、原 sealed delivery 对象、同 epoch，且 `_current_study_grade_phrase` 核实完整已写入样本、本地 input sequence 和 current snapshot，waiting 必须已清。它没有把一次普通 clear 当作 provider boundary。
- buffer/writer/waiting 未退休时继续受原保护；非空题、未知/失败 pin、foreign authority/provider/token/scope、epoch 改变和 feature OFF 仍 poison。后续真正正 speech frame才可重新读当前题；旧/相同 delivery 或不递增 sequence 无法通过下一 ASR 的新题绑定。
- 精确核对实际 `_reset_input_route_identity_stream` 仅清 route observation 的 armed/owner 两字段；NativePhraseUplink 的 current snapshot 经独立 Core authority callback 加实际 ws 比对。因此该 reset 本身没有退休或重认 grade authority。测试中这两个 reset seam 使用 Mock，不能据此声称完整真实 transport 回归；此点另有源码依据。

## 独立离线执行

使用已有 Source venv，无安装依赖：

```powershell
.\benchmarks\raw\neko-product-host\.venv\Scripts\python.exe -X utf8 -B scripts/test_neko_first_voice_start.py
.\benchmarks\raw\neko-product-host\.venv\Scripts\python.exe -X utf8 -B scripts/test_neko_native_grade_route.py
```

- Fresh：**3 PASS**（0.127s）。实际官方 child 生成临时卡并确认 yui/guidance，重复调用 bytes 不变；已有卡自定义字段/个人 guidance 保留；坏 JSON 原 bytes 保留。
- Route：**38 PASS**（6.440s）。包含 canonical 临时回放/幂等、实际 clear/protect AST、healthy-empty → 实际 boundary → clear → 同连接不同新 sealed delivery → 正式 SDK/临时 SQLite 一次 grade，以及上述拒绝负例。模型、外层 transport、socket 等 seam 是替身；不是 provider ACK、模型评分质量或设备播放证据。

## 场47归因边界与后续

前一报告已独立核到场47 `tts=True`，Core pin reader/start claim 因 use_tts 拒绝；DB healthy-empty 不等于 transport 已有健康空槽。独立离线也复现了原 clear 无条件 poison 的另一问题。本阶段分别修两处，不能宣称 clear 是场47唯一原因。修后真实首次 fresh 启动以及出题→同连接回答→追问仍待 Main 有界验证；无需修改原47 raw、重写历史或放宽所有 poisoned pin。

## 审查指纹（SHA256）

| 文件 | SHA256 |
|---|---|
| scripts/neko_desktop_tutor_host.py | `4b3a4eba40908eae61f57d274d9cec229ac52ccccbd80aeea0370f2f681889ba` |
| scripts/test_neko_first_voice_start.py | `0b7bfd1e042e5f19cb14e831a816a3dfd3979fc276d79f5a5ed0667692983322` |
| scripts/neko_native_grade_patch.py | `0e9a8054860690ec3675b567507453d07c2c93fb150fde492db94cc987afec99` |
| scripts/test_neko_native_grade_route.py | `a013f81210d0f35e0edba7ff1ffd18f1708b1b4604cabcc3bc7b968522e9e15d` |

本报告冻结；未启动任何需要清理的服务、浏览器、Native 或音频进程。
