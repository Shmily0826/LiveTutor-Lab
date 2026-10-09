# 桌面文字 Tutor 快速开始（2026-10-09）

面向"打开就能用"的一份说明：不需要理解测试脚本、端口或内部配置。
验收细节与证据在 `neko-safe-screen-desktop-tutor-2026-10-09.md`。

## 1. 准备（只做一次）

1. 一个 DeepSeek API key，单独写在一行里，存到 `D:\CODE\API\new api.txt`（以 `sk-` 开头）。
2. Python 3 和 Node 在 PATH 里即可；不需要装 N.E.K.O，仓库里带着一份被冻结的宿主副本。

> 这个 key 只会被写进仓库内的一次性目录 `benchmarks/raw/neko-appdata/`（已被 Git 忽略），
> 不会写进你自己的 `%LOCALAPPDATA%\N.E.K.O`。

## 2. 启动

在仓库根目录执行一条命令：

```powershell
python scripts/neko_tutor_start.py
```

它会：启动一次性宿主（关闭语音合成/麦克风/主动提醒，出口只允许 `api.deepseek.com`）→
自动打开 Study UI → 等你用完。**用完按 Enter**，脚本会把宿主停掉并打印本次出口审计。

- 不想让它开浏览器：`python scripts/neko_tutor_start.py --no-browser`（它会打印地址）。
- 想开久一点：`--minutes 90`。
- 只想看界面能不能起来（不产生任何模型调用）：
  `python scripts/neko_desktop_tutor_host.py --hold 300` 起宿主，然后
  `node scripts/neko_desktop_study_ui.mjs --up-to-mode`，最后 `python scripts/neko_desktop_tutor_host.py --stop`。

## 3. 怎么用（原生 Study UI）

1. 第一次打开会有一个"选学习阶段"的卡片，选一个或直接按 Skip；如果弹出记忆卡组对话，按
   "Skip and use default" 即可。
2. 顶部模式选 **Teaching**（教学模式）。
3. 把课本/题目的文字粘进输入框，按 **Explain**。
4. 同一个页面继续追问；想让它带着上一次讲解的上下文，勾上"使用上一次解释"。
5. 展开下方折叠面板：可以出题、提交答案看判分、点 **Summarize** 生成本次学习小结。
6. 学习记录写进这个一次性目录里的学习数据库，重开宿主还在；不会碰你真实的学习数据。

时延参考（宿主实测，thinking 关闭）：首答约 10 s，追问约 12 s，小结约 12 s；
复杂题的讲解 15–20 s 也属正常。目前是整段返回，没有流式输出。

## 4. 指定窗口采集（可选，安全采集屏幕内容）

`study_ocr_snapshot` 的 `capture_mode="target_window"` 只会截你**点名的那个窗口**，
并且要求：窗口标题精确匹配、该窗口当前在前台、抓到的文字里必须出现你预期的内容关键词；
任何一条不满足就直接拒绝，**不会**改成全屏、也不会把内容传给模型。

```powershell
# 只验采集来源（零模型调用）：会自己开一个合成课文窗口
python scripts/neko_desktop_tutor_session.py --window --capture-only

# 采集 + 完整文字教学（约 10 次真实调用）
python scripts/neko_desktop_tutor_session.py --window
```

用你自己的窗口当目标时，把 `window_title` 换成你窗口的**完整标题**，`expected_markers`
填几段只有那份材料里才有的文字，并让该窗口保持在前台。
如果前台被别的应用抢走（例如你去点了浏览器），采集会被拒绝——这是设计行为。

## 5. 关闭之后

- 宿主由启动脚本负责停止；`python scripts/neko_desktop_tutor_host.py --stop` 是兜底命令。
- 一次性数据：`benchmarks/raw/neko-appdata/`（约 10 MB，含明文 key）。想彻底清掉就删这个目录，
  下次启动会自动重建；不删就能沿用上次学习记录。
- 每次运行的证据 JSON 落在 `benchmarks/raw/evidence/`（Git 忽略）。

## 6. 第一次实际体验建议验证什么

1. 首次运行弹窗能否按 Skip 过去，Teaching 模式按钮变亮；
2. 粘贴一段**你自己课程**的正文，Explain 出来的语言与内容是否对得上（不是模板化敷衍）；
3. 连续追问两次，看它是否记得上一轮讲的内容；
4. 出一题 → 故意答错 → 看判分是否指出**具体那一步**错在哪；
5. Summarize 是否把"你答错的那一步"写进小结；
6. 重启宿主后重开 Study UI，之前的 session 记录还在；
7. 全程没有声音（TTS 已禁用）、没有其他外网连接（审计里只有 `api.deepseek.com`）。

## 7. 现在还不要期待的东西

- **语音输入 / 朗读 / 打断**：没有开放，也不要用正式版 N.E.K.O 试——二进制的音频出口没有
  fail-closed 闸门，判定标准见 `neko-host-tts-gate-plan-2026-10-09.md`。
- Study UI 上的 **OCR 按钮**仍走"用户手选区域"的 interactive 模式；指定窗口采集目前只能从
  插件入口/脚本调用，还没接到那个按钮上。
- 长会话的总结偶尔会补造例题细节；宿主路径时延比隔离夹具慢 3–5 倍，原因未定位。
