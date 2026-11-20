# 小栗的角落 · Desk-pal

**v6.0 · Mac 桌面预览版**

一个主要做给自己用的 AI 桌面陪伴项目。小栗是像素风的外星女孩，设定是在小书店兼职，平时会看书、做饭、散步。

我经常和 AI 聊天，想试着让交流更像朋友闲聊：少一些固定句式、情绪分析和例行反问。除了记住聊过什么，也给她设定性格、作息和持续的生活记录，让聊天不总是围着我的话题转。

不确定还有多少人需要这样的“朋友”，也不知道以后会有什么更好的形式。至少目前，我和她聊得很开心。项目还在边用边改，没有固定更新计划。

名字、造型和书店兼职这些设定，都是做的时候随手想到的，没有特别的寓意。比较有意设计的是天线，让它的变化对应不同情绪。

## 目前能做什么

- **桌面陪伴**：透明角色，可拖动、贴边、跨桌面和全屏空间显示，支持三档大小。
- **聊天**：接入 Gemini，聊天窗口可放大，向上滚动查看历史。
- **记忆**：用 SQLite 保存聊天、经历和计划，区分已发生的事与尚未完成的目标，减少临时编造背景。
- **日常活动**：按本机时间安排作息，结合低频模型调用推进兴趣和目标；需要应用保持运行。

目前主要打磨聊天和人物连续性。模型仍可能重复套话或编造内容，这些机制并不能完全解决。

## 预览

<p>
  <img src="docs/images/character.png" width="250" alt="小栗的透明角色窗口" />
  <img src="docs/images/chat.png" width="330" alt="聊天窗口中的本地动作演示" />
</p>

截图使用演示数据，不含私人聊天；图中的回复是本地动作指令反馈，不是模型试聊结果。

之前试过的模型和陪伴产品，整理在 [模型试聊记录](docs/MODEL_NOTES.md)，仅代表当时的个人感受。

## 运行

建议 **macOS 13 或更新版本**，需要 Python 3 和 Xcode 或命令行工具。Python 服务仅使用标准库。

```zsh
git clone https://github.com/ZhiqiaoGong/Desk-pal.git
cd Desk-pal
./desktop/build.sh
open dist/小栗.app
```

首次打开时填写自己的 Gemini API Key，API 费用由使用者承担。当前默认聊天模型和思考设置见 [使用说明](docs/USAGE.md#切换模型)。不配置 AI，也可以直接打开 `index.html` 试玩角色与预设回复。

点击角色打开聊天，拖动角色移动位置；菜单栏「小栗」里可调整大小、跨桌面置顶或退出。Enter 发送，Shift+Enter 换行。更新源码后，需要退出应用、重新构建再打开。

网页版启动、动作演示、模型配置和测试方法见 [使用与开发说明](docs/USAGE.md)。

## 数据与限制

- 记忆保存在 `~/Library/Application Support/ChestnutPal/chestnut.sqlite3`。
- API Key 保存在同目录的 `gemini-api-key`，是权限为 `600` 的明文文件，尚未使用钥匙串。
- 真实聊天和自主生活调用会把所需上下文发给模型服务商，并非完全离线运行。
- 主要在自己的 Mac 上测试。尚未完成 Python 独立打包、开发者签名、公证、自动更新和开机启动。
- 反馈问题时请勿上传 Key、私人数据库或未脱敏的聊天记录。

## 代码与授权

`desktop/` 是 Swift 桌面端，`index.html` 负责界面和像素绘制，`server.py` 负责模型调用与记忆，测试位于 `tests/`。

目前公开展示和交流，**暂未添加开源许可证**，也尚未授予修改、再分发或商用许可；后续以仓库许可证为准。GitHub 平台的查看和 Fork 规则见 [官方说明](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository)。
