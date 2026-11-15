# 小栗的角落 v5.3 — 自然对话与有依据的记忆

**v5.3 沿用 v5.2 的人物动作和长期数据库，不重置记忆。** 这版的重点是将“既定事实 / 未知背景 / 想法与计划 / 已发生经历”分开，让小栗不再为了回答问题临时编身世。她现在固定在**地球一家小书店兼职**；具体店名、收入、母星、家庭、来地球的原因都**未设定**。还没记录的经历不应被当作事实。

## 更新内容

- 更真实的日常聊天风格：去傲娇、中二、频繁外星梗和机械安慰；认真倾诉时优先理解问题，不强行幽默。
- “小栗的事实”与“她想做的事情”分开。聊天只能使用固定设定、当前状态、已记录的事件和目标；未知背景允许直接回避。旧版带括号、外星梗的助手回复保留在 SQLite，但会从**发送给模型的上下文中筛除部分典型示例**，减少模仿旧风格。
- 语言和动作分离：模型请求返回 JSON 形式的 `reply / emotion / gesture`。聊天框只显示 `reply`；表情和小动作由前端呈现；可能仍出现不完美的模型输出，程序会过滤常见括号动作文字。**不能保证模型绝对不会编造事实**，这版加入了约束和防护，仍需要实际体验评估。
- 聊天时如果她原本在睡觉，会短暂醒来交谈，不改真实时间作息。
- 聊天输入框可自动扩展成多行（最多约五行，然后在框内滚动）；**Enter 发送、Shift+Enter 换行**，中文输入法组合输入时不会触发发送；长消息在历史中按原文换行。
- 发色统一为自然栗棕色，去掉发顶的深色帽子感；保留既定长发、天线、做饭、散步、整体旋转的睡姿。
- 延续每日 AI 请求次数限制和固定 SQLite 数据目录。

## Mac 升级（建议用你之前已能成功使用的 Gemini）

1. 解压 `desk_pal_v5_3.zip`。
2. 在旧版运行的 Terminal 里按 **Control+C** 结束原服务。
3. 新开 Terminal，输入 `cd `，然后将新版文件夹拖到 Terminal 后按回车。
4. 如果是新开的 Terminal，需要重新配置 Gemini API Key（不要把 Key 发给别人或放在 HTML 里）。选择你已在 v5.2 成功使用的模型名称：

```bash
export GEMINI_API_KEY='你的密钥'
export GEMINI_MODEL='你已经成功使用的模型名称'
export CHAT_PROVIDER=gemini
export THOUGHT_PROVIDER=gemini
python3 server.py
```

5. 在 Chrome 打开 **http://127.0.0.1:8765**，点击小栗开始对话。**不要用 ChatGPT 内置 HTML 预览测试按钮交互。**

如果还在旧 Terminal 且环境变量已经设置，通常只需进入新版目录并运行 `python3 server.py`。

### 记忆与隐私

Mac 数据库默认在：

`~/Library/Application Support/ChestnutPal/chestnut.sqlite3`

**v5.2 → v5.3 使用同一份数据库。** 程序不会自动删除旧消息，既有目标和经历仍在。升级前可以先退出服务，然后用 Finder 复制这份数据库做备份。数据库只保存到本机；相关上下文会在实际 AI 请求时发送给你配置的云端模型。若此前设置了 `PAL_DB`，仍以它指定的路径为准。旧版 v5.0/v5.1 中的数据库不会被自动导入。

### 运行模式

- 直接打开 `index.html`：离线试玩，可以演示人物动作，但回答是预设文字，不是真正的 AI。
- 通过 Python 服务：在浏览器与本地服务连接后，才会请求真实 API。
- 人物的生活是虚拟模拟；她不会真正去实体书店工作，也无法访问你的屏幕或麦克风。
- 默认每天最多 80 次聊天请求、8 次自主思考请求。上限是次数，不是美元上限。

## 测试情况

无需 API Key 的回归测试：

```bash
python3 test_server.py
python3 test_grounded_chat.py
python3 test_life.py
python3 test_api_protocol.py
node test_interaction.cjs
```

`test_browser.py`、`test_ui_v53.py`、`test_visual.py`、`test_emotions.py` 使用 Playwright/Chromium，面向有开发环境的用户。已检查模拟 AI 情绪动作、离线回复、输入框多行、Enter/Shift+Enter、数据库与缓存隔离、跨天生活。

**尚未完成**：在本环境使用你自己的 Gemini API Key 做端到端真实对话测试，或对几十轮真实模型回复做量化风格评测。由于模型生成存在不确定性，“不编造经历”仍需要对真实对话继续观察和完善。
