# DICK

**Distorted Input Context Keeper.**

Make your text worse. Keep it recognizable.

把正常文本的精神状态搞坏一点，但保留原词、顺序和可辨识度。一个轻量的 CLI 娱乐工具：Python 标准库实现，运行时零依赖，不联网，不调用 AI，不需要配置文件。

## 安装

需要 Python 3.10 或更新版本。在项目目录执行：

```sh
python -m pip install .
dick "hello world"
```

也支持 `pip install .`。建议使用虚拟环境：

```sh
python -m venv .venv
```

Windows PowerShell 激活：`.\.venv\Scripts\Activate.ps1`；Linux / macOS 激活：`source .venv/bin/activate`。激活后执行上面的安装命令。

不安装也可以在项目目录运行 `python -m dick "hello world"`。安装构建可能需要获取 setuptools；文本处理本身完全离线。

## 用法

```text
dick [OPTIONS] [TEXT]
```

| 参数 | 作用 |
| --- | --- |
| `-l, --level 1-4` | 破坏强度，默认 `2` |
| `-m, --mode MODE` | 破坏风格，默认 `normal` |
| `-r, --random` | 随机选择风格，忽略 `--mode` |
| `--seed NUMBER` | 固定所有随机行为，包括随机模式选择 |
| `--plain` | 只输出结果，适合管道和脚本 |
| `-h, --help` | 显示帮助 |
| `-V, --version` | 显示 `DICK v0.1.0` |

默认输出包含原文、结果、实际模式和等级。`--plain` 不包含标题、状态或颜色转义；原文没有末尾换行时，输出补一个换行方便终端使用。

```sh
dick "hello world"
dick -l 4 -m terminal "I forgot to backup the database"
dick -m leet --plain "this program works"
dick -m glitch -l 3 "hello world"
dick -m brainrot -l 4 "this program works"
dick --plain -- "--this is text, not an option"
```

## Level

| 等级 | 效果 |
| --- | --- |
| 1 | 轻微大小写、空格和标点变化，极少重复；所有模式都不使用 leet、Unicode 污染或长装饰 |
| 2 | 加入少量 leet 和更多分隔符；terminal / brainrot 增加短装饰；推荐默认等级 |
| 3 | 更多字符替换、扩展名或模式装饰；glitch 可以添加少量 Unicode |
| 4 | 更强的可辨认替换，错误码、integrity、checksum 或 meme 装饰；依然保留原句 |

## Mode

| 模式 | 风格 |
| --- | --- |
| `normal` | 大小写、leet、分隔符和少量装饰的综合效果 |
| `leet` | 以 `a→4 e→3 i→1 o→0 s→5 t→7` 为主，少加额外文字 |
| `glitch` | 轻度故障效果；每行最多三个新组合标记，不会疯狂叠 Unicode |
| `terminal` | shell / debug / 错误信息包装 |
| `brainrot` | `bro`、`fr`、`skill issue` 等装饰，每行最多一个额外 Emoji |

Level 1 始终保持轻微；模式特色从 Level 2 开始增强。

## Seed

```sh
dick --seed 42 --plain "hello world"
dick --random --seed 123 --plain "hello world"
```

例如，`dick --plain --seed 42 "hello world"` 输出：

```text
h3lL0_woRLd
```

相同输入、等级、模式和 seed 在同一版本中得到相同结果。使用 `--random` 时，实际选中的模式也固定。无 seed 时，每次调用创建一个新的随机源，不改变 Python 全局 RNG。

## stdin 和多行

```sh
echo "hello world" | dick --plain
cat file.txt | dick --plain
```

PowerShell 读取 UTF-8 文件：

```powershell
Get-Content -Raw -Encoding utf8 .\file.txt | dick --plain
```

显式 `TEXT` 参数优先于 stdin。无参数且终端未提供 stdin 时直接报错，不等待输入；空白输入也报错。输入和输出使用 UTF-8，保留换行种类、空行、缩进和已有末尾换行。旧版 shell 的管道编码也应设置为 UTF-8。

```powershell
dick --plain --seed 42 "Hello world`nThis is a test`nGoodbye"
```

输出仍然是三行，每行独立处理。

## 保留什么

原词不删除、不换成无关词，也不重新排序。只对 ASCII 字母做可辨认的字符替换；中文保持原字，可以插入少量分隔符。已有 Emoji（包括变体选择符、肤色和 ZWJ 序列）保留。

数字、IP、URL、邮箱，以及常见的绝对路径、相对路径和文件名会按原文保护。包含空格的路径请在文本里保留内层引号，例如：

```sh
dick --plain -l 4 'open "C:\Program Files\app\data.txt" port 8080'
```

这些是简单的文本启发式规则，不是 NLP 或完整的路径解析器。不带引号的含空格路径无法可靠判断边界。即使 Level 4，也不会把 `database backup` 换成一段无关 meme。

## 开发和测试

```sh
python -m unittest discover -s tests -v
```

测试使用标准库 `unittest`，覆盖 seed、所有等级和模式、原词保留、受保护内容、UTF-8 / Emoji、多行、stdin、plain、帮助和错误退出码。

MIT License.
