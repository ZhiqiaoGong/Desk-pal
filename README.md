# 小栗的角落 v5.4

小栗是在地球小书店兼职的像素女孩。她用更接近日常微信聊天的节奏回复，并用 SQLite 里的经历延续自己的生活。已记录的经历和想法分别提供给模型。旧对话只作为聊天上下文。

## 在 Mac 上运行

1. 如果旧版正在运行，在那个 Terminal 里按 Control+C 停止服务。
2. 在新版文件夹打开 Terminal，确保环境里已设置 `GEMINI_API_KEY`。如果原来在这个 Terminal 设置过，可以直接复用。
3. 执行 `python3 server.py`，在 Chrome 打开 <http://127.0.0.1:8765>，点小栗聊天。

直接打开 `index.html` 可以离线试玩动作和预设回复。真实聊天使用本地 Python 服务。

## 切换模型

| 用途 | 默认模型 ID | 模型覆盖变量 | Thinking Level 变量 |
| --- | --- | --- | --- |
| 默认聊天 | `gemini-3.1-pro-preview` | `GEMINI_CHAT_MODEL` | `GEMINI_CHAT_THINKING_LEVEL` |
| 备用聊天 | `gemini-3.8-flash` | `GEMINI_CHAT_BACKUP_MODEL` | `GEMINI_CHAT_BACKUP_THINKING_LEVEL` |
| 自主生活 | `gemini-2.5-flash-lite` | `GEMINI_THOUGHT_MODEL` | `GEMINI_THOUGHT_THINKING_LEVEL` |

备用模型可在重启服务时手动切换，保留同一份聊天记录：

```bash
GEMINI_CHAT_PROFILE=backup python3 server.py
```

3.1 Pro 和 3.8 Flash 默认使用最低的 `low`，也可设为 `medium` 或 `high`。2.5 Flash-Lite 保持默认设置（思考关闭）。若要给生活模型设置 Thinking Level，可以将生活模型切换到支持该参数的 Gemini 3 型号。旧的 `GEMINI_MODEL` 仍可作为生活模型的兼容配置。模型和 Thinking Level 以 [Google 官方文档](https://ai.google.dev/gemini-api/docs/generate-content/thinking) 为准。

## 记忆和费用

Mac 默认继续读取 `~/Library/Application Support/ChestnutPal/chestnut.sqlite3`。如果设置了 `PAL_DB`，服务使用指定文件。SQLite 中会保留现有聊天、经历和目标，并给用量表添加费用估算列。实际调用时，聊天上下文会发送给所配置的云端模型。

打开 <http://127.0.0.1:8765/api/health> 可查看聊天与自主生活各自的今日请求数、返回数、输入与输出 token，以及按 [Gemini 标准文本费率](https://ai.google.dev/gemini-api/docs/pricing) 计算的美元估算。输出统计包含 Gemini 返回的思考 token。旧用量、未知费率和缺少用量的响应会计入 `unpriced_responses`。实际账单还受免费额度和计费方案影响，Google AI Pro 订阅与 API 计费独立。

默认每日聊天和自主生活请求上限分别是 80 和 8，可通过 `DAILY_CHAT_LIMIT` 与 `DAILY_THOUGHT_LIMIT` 调整。失败的请求也占用次数；备用模型需手动切换。

## 验证

```bash
python3 test_server.py
python3 test_grounded_chat.py
python3 test_life.py
python3 test_api_protocol.py
node test_interaction.cjs
```

真实试聊可先用临时记忆库，让验收对话和原来的记录各自保留。下面的启动方式同时关闭自动生活调用，便于控制试聊用量：

```bash
trial_dir="$(mktemp -d)"
PAL_DB="$trial_dir/chestnut.sqlite3" DAILY_CHAT_LIMIT=12 DAILY_THOUGHT_LIMIT=0 PORT=8766 python3 server.py
```

打开 <http://127.0.0.1:8766>。先聊一段认真话题，例如找工作很久、还要靠家里，然后突然切到日常闲聊。接着问小栗有没有也向父母要过钱、在哪工作、最近做完了什么。观察她是否自然跟上话题、少做例行反问，以及是否把假设或计划说成真的。重启时可用同一份临时数据库切换到备用模型继续试聊。
