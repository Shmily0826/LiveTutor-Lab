# W-A：源码教学工具路由

## 修改

- `study_code` 描述收敛为源码证据查询，口头讲解/行含义/假设改动/再讲讲明确交给 `study_explain(material_source=project_code)`；不再鼓励把整句中文直接交给 explore。
- `study_explain` 描述开头给出中文意图与对象形式 `code_requests` 示例，明确追问可省略请求、由后端重读上一段源码。
- 先写说明契约测试，旧代码 2 项失败；修改后 2 项通过。原有源码教师边界 14 项在独立进程通过。本测试证明 metadata，不证明 provider 必然选择正确工具。

## 实际 Native / 额度

| 场 | 账本前 → 后（DeepSeek / Lanlan.app） | 实际结果 |
|---|---|---|
| 中文原句第 2 步 | 1201/105 → 1209/106 | 触发 `__llm_tool__study_explain`；材料绑定 valid=True、reply=True；收到 454,840 bytes 音频，Native 可见文本说明非 200 抛异常。回答仅一句，没有完整覆盖第 26 行解析不执行，因此完整教学语义仍 PARTIAL。 |
| 带两处 0.9 秒停顿的第 4 步，独立重启场 | 1209/106 → 1212/107 | 无工具、无回复、无音频；不是通过。 |
| 唯一一次有界重试：同会话第 2 步→第 4 步 | 1212/107 → 1223/108 | 首句有音频但没有新教学 trigger；第二轮仍无回复/音频。停止重复这个失败场。 |

原始场次文件分别为 raw/evidence 的 `codex-wa-native-step2-20261016.json`、`codex-wa-native-step4-20261016.json`、`codex-wa-native-chain-retry-20261016.json`。全部固定 WAV/output-only、采集设备禁止、无 loopback、未改音量；cleanup_errors 都为空。第 4 步仍未获得本轮端到端成功证据，不能把“没有出现拒绝句”当作成功。

实时 `GET /api/tools` 已读到新的 study_code/study_explain 描述，保存于 `codex-wa-live-tool-schema-20261016.json`。`benchmarks/raw/daily-phase21-native-tool-schema.py` 是读 API 校验 quiz schema 的脚本，不是另一份 tool 描述缓存。

## 部署与边界

- 改动前 32 个产品文件 source/manifest/deployment 全一致；旧文件与 manifest 在 raw/evidence 独立目录备份。更新 manifest 的旧 SHA 与验证说明，再核验新 SHA；SourceGate PASS，`neko_voice_host_patch.py --check` 全部 patched。
- 没有修改宿主、打断、arbiter 或语音传输。为保护昨晚原日志，测试使用 raw 下的任务专用 launcher/probe 副本，仅固定 ROOT、重定向日志、给本轮设置累计 1401 的内存中请求停止线；原账本全局 2000/轮次/历史不变。连续源码场只在该单一 output-only 任务 store 放行既有 followup WAV 流程；产品 probe 原文件未改。
- 复用 M5 的任务测试数据库一致性快照和原有授权，未对用户日常库操作，不预读本轮所问源码。

## 待 Opus 复核

1. `scripts/neko_desktop_tutor_host.py` 的角色指导前段要求源码教学走 explain，末段仍写“具体源码行使用 study_code file”。这是独立宿主提示，与本轮新说明有竞争；本轮未改。
2. 第 4 步空回合在独立场和唯一重试都出现。下一步应审查 provider 识别/响应与会话状态，而不是继续无界重试或新增语音补丁。需要 Native 实际入站识别、工具参数、响应所有权的关联证据。
3. 首场教师工具已返回有效 reply，但角色口头文本未完整复述两句要求。需要后续审查 Native relay，不能用音频字节数当教学质量通过。

结论：源码/metadata 与一个实际中文 Native 路由通过；完整第 2 步语义和第 4 步语音端到端 PARTIAL/未通过；可听性和真人待用户。
