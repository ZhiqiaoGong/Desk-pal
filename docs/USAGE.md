# 使用与开发说明 · v6.0 桌面预览版

小栗是在地球小书店兼职的像素女孩。她用更接近日常微信聊天的节奏回复，并用 SQLite 里的经历延续自己的生活。已记录的经历和想法分别提供给模型。旧对话只作为聊天上下文。

## Mac 桌面版（日常使用）

需要本机安装 Python 3。首次从源码使用时，先按下方命令构建。

本机构建的应用位于 `dist/小栗.app`，双击即可打开。应用读取已有的 Gemini Key 和默认记忆库，自动启动独立的本地服务。尚未保存 Key 时会显示安全输入框。当前使用 3.1 Pro 和 `low`。

- 小栗以透明背景显示在桌面上，按住角色拖动，应用会记住位置。按角色实际边界限制移动，可贴近屏幕边缘。角色周围的空白区域可穿透点击到下面的窗口。
- 点击小栗，在角色旁边打开单层聊天框。优先放左侧，空间不足时调整到屏幕内。可拖动聊天框顶部；关闭后重新打开会跟随小栗当前位置。支持大小切换、草稿和历史浏览。看最新消息时，放大或缩小后保持到底部；阅读旧消息时保留位置。
- 在聊天里发动作演示指令，动作会显示在小栗窗口里。
- 点击聊天框右上角 × 收起聊天，小栗继续留在桌面。
- 菜单栏“小栗”可显示或隐藏角色、打开聊天或退出。
- 勾选“小栗跨桌面置顶”，三指切换桌面或其他应用的全屏空间时，小栗仍留在同一位置；取消勾选后可以被其他窗口遮住。全屏跨应用设置在 macOS 13 及以上启用。
- “角色大小”提供小号（160）、标准（200）、大号（256）三档，数值是角色画布的逻辑像素尺寸。标准为当前默认大小，大号为原来的大小；切换尽量保持脚底位置，自动记住选择。聊天窗口尺寸独立控制。
- 启动时按当前活动挑一句碎碎念，避开最近六句；十分钟内重开不重复冒泡。夜间、安静状态或聊天已打开时不显示开场白，不额外调用 AI。
- 退出应用时，会停止由应用启动的本地服务。
- 使用桌面应用时，建议停止旧终端服务并关闭旧网页，避免两边同时触发生活调用。

角色窗口和聊天框均已去掉系统标题栏。开机启动待后续完善。应用依赖本机 Python 3，当前构建产物面向这台 Mac；尚未进行开发者签名和公证。

在安装了 Xcode 或命令行工具的 Mac 上重新构建：

```zsh
./desktop/build.sh
open dist/小栗.app
```

应用包含构建时的网页和 Python 代码副本。修改源码后，退出应用并重新构建，再打开。

窗口位置、置顶、角色大小和开场白记录保存在 macOS 应用偏好设置中，独立于 SQLite 记忆库。桌面应用使用系统分配的本机端口，不固定占用 8765。

原生代码在 `desktop/`，构建输出 `dist/` 和编译缓存 `.build/` 已加入 Git 忽略。

## 网页版（可选）

需要安装 Python 3。日常使用可在 Finder 中双击 `启动小栗.command`。

1. 首次启动，在终端中粘贴 Gemini API Key，按回车。输入时不显示字符。
2. 启动器将 Key 保存到 `~/Library/Application Support/ChestnutPal/gemini-api-key`，后续启动自动读取。该文件是权限为 `600` 的本机明文文件，仅当前账户可读写。
3. 启动后自动打开 <http://127.0.0.1:8765>，点击小栗开始聊天。使用期间让终端保持运行，可以最小化。
4. 退出时在终端按 **Control+C**。更新 Python 服务代码后也需要先停止，再双击启动器；只修改网页时刷新页面即可。

更换 Key 时，在项目目录执行 `./启动小栗.command --reset-key`。已有服务运行时，先停止服务再更换。密钥、记忆数据库和本地备份位于 Git 跟踪范围之外。

启动器固定使用日常数据库、8765 端口、Gemini 主聊天配置及 `low` 思考设置。需要自定义模型配置或试聊数据库时，可直接运行 `python3 server.py`。直接运行前，需要在该终端配置环境变量；也可读取启动器保存的 Key：

```zsh
IFS= read -r GEMINI_API_KEY < "$HOME/Library/Application Support/ChestnutPal/gemini-api-key"
export GEMINI_API_KEY
```

直接打开 `index.html` 可以离线试玩动作和预设回复。真实聊天使用本地 Python 服务。

## 聊天窗口与历史

- 点击小栗展开聊天，右上角的放大按钮可切换到约 640 × 720 的大窗，尺寸随屏幕调整。切换保留输入草稿和阅读位置。
- Enter 发送，Shift+Enter 换行，支持中文输入法和多行输入。
- 初次读取最近 24 条消息，往上滚到顶部自动加载更早的 40 条，按日期分隔。加载历史时保持阅读位置。
- 查看旧消息时收到回复，可点击“回到最新消息”。历史加载失败时会显示重试入口。
- 历史浏览和模型上下文分别处理。模型通常收到最多 8 条近期消息，间隔达到 4 小时的内容标成较早聊天，再结合当前状态、经历、计划和相关记忆。

## 动作和外观

在聊天里输入 `演示睡觉`、`演示散步`、`演示做饭`、`演示工作`、`演示读书` 或 `演示发呆`，可临时展示约 30 秒。表情可用 `演示开心`、`演示生气`、`演示难过`、`演示困` 等指令。这些演示由本地执行，不调用模型。

当前外观采用左右对称的粗阶梯头顶，统一了各动作的衣服和袖子连接，生气表情使用轻压眉毛、嘟嘴和红脸颊。睡觉演示可以在聊天窗口打开时正常显示。

页面时间使用浏览器本地时间，服务端作息和每日调用统计使用运行 Python 的电脑本地时间。在同一台 Mac 上运行时，两者通常一致。

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

使用网页启动器时，打开 <http://127.0.0.1:8765/api/health> 可查看聊天与自主生活各自的今日请求数、返回数、输入与输出 token，以及按 [Gemini 标准文本费率](https://ai.google.dev/gemini-api/docs/pricing) 计算的美元估算。输出统计包含 Gemini 返回的思考 token。旧用量、未知费率和缺少用量的响应会计入 `unpriced_responses`。实际账单还受免费额度和计费方案影响，Google AI Pro 订阅与 API 计费独立。

默认每日聊天和自主生活请求上限分别是 80 和 8，可通过 `DAILY_CHAT_LIMIT` 与 `DAILY_THOUGHT_LIMIT` 调整。失败的请求也占用次数；备用模型需手动切换。

## 验证

```bash
python3 tests/test_server.py
python3 tests/test_grounded_chat.py
python3 tests/test_life.py
python3 tests/test_api_protocol.py
node tests/test_interaction.cjs
node tests/test_opening.cjs
```

Mac 原生集成测试需要图形登录会话，先构建应用，再运行：

```zsh
./desktop/build.sh
python3 tests/test_desktop.py
```

测试使用临时数据库和模拟模型，不调用付费 AI。覆盖透明面板、贴边、拖动、聊天开关、窗口缩放后的滚动位置、草稿、动作演示和置顶设置。三指切换全屏空间仍需人工验收。开场白测试覆盖活动短句、十分钟冷却与最近句子记录。

真实试聊可先用临时记忆库，让验收对话和原来的记录各自保留。下面的启动方式同时关闭自动生活调用，便于控制试聊用量：

```bash
trial_dir="$(mktemp -d)"
PAL_DB="$trial_dir/chestnut.sqlite3" DAILY_CHAT_LIMIT=12 DAILY_THOUGHT_LIMIT=0 PORT=8766 python3 server.py
```

打开 <http://127.0.0.1:8766>。先聊一段认真话题，例如找工作很久、还要靠家里，然后突然切到日常闲聊。接着问小栗有没有也向父母要过钱、在哪工作、最近做完了什么。观察她是否自然跟上话题、少做例行反问，以及是否把假设或计划说成真的。重启时可用同一份临时数据库切换到备用模型继续试聊。

## 项目目录（仓库根目录）

```text
deskpal/
├── desktop/           # Swift 原生窗口及构建脚本
├── dist/小栗.app      # 本机构建的桌面应用，Git 忽略
├── 启动小栗.command   # 网页版双击启动入口
├── server.py          # 本地服务、模型调用和 SQLite 记忆
├── index.html         # 聊天界面及角色绘制
├── README.md
├── tests/             # 后端、网页交互、原生窗口和视觉测试
├── previews/          # 已保存的角色及界面预览图
└── .backups/          # 本机备份，Git 忽略
```

预览图包含早期版本的截图，供参考；视觉测试运行后会更新对应图片。视觉测试需要额外安装 Playwright 及浏览器，部分脚本仍使用 Linux Chromium 路径。常规回归测试命令见上方“验证”。

日常记忆和 API Key 存在 Mac 的 Application Support 目录中。
