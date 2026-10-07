# DICK CLI 宣传片

30 秒 / 1920 × 1080 / 30 fps，H.264 + AAC，配原创电子音乐。所有 CLI 演示均由本仓库代码实时计算，使用 seed 42，没有伪造输出。

开头及结尾的制作说明按要求原样显示：

> 软件和本视频均由 GPT 6.1 Sol制作

仓库地址：<https://github.com/az7627/dick-cli>

## 分镜

| 时间 | 内容 |
| --- | --- |
| 0–5.8 秒 | 软件 Logo、大字 DICK CLI、中等字号制作说明及仓库地址 |
| 5.8–11.7 秒 | 真实终端输入 / 输出，强调原意保留与固定 seed |
| 11.7–17.8 秒 | 四级强度的真实输出并排比较 |
| 17.8–24.2 秒 | normal / leet / glitch / terminal / brainrot 五种风格 |
| 24.2–30 秒 | 安装命令、仓库地址和行动号召 |

## 重建

视频制作依赖与 CLI 完全独立。安装 `requirements.txt` 中的制作工具，并确保 FFmpeg / ffprobe 在 PATH 中：

```sh
gh release download v0.1.0 --repo az7627/dick-cli --pattern logo.png --dir promo/.cache
python -m pip install -r promo/requirements.txt
python promo/render.py --preview-only
python promo/render.py
```

Logo 单独从 GitHub Release 获取，缓存到被忽略的 `promo/.cache/`。也可以手动下载，再用 `--logo PATH` 指定本地图片。克隆仓库不会下载任何图片、视频、音频或安装包。

默认读取 Windows 字体目录中的微软雅黑、Bahnschrift、Consolas 和 Segoe UI Emoji。可通过 `--font-root` 指定相同字体文件所在目录；字体不随仓库分发。其他平台可在脚本 `FONT_FILES` 中替换为有授权的同类字体。

输出位于 `promo/output/`，已被 `.gitignore` 排除。图片、视频、音频、字体和安装包也按扩展名忽略；仓库只保留源码与文本。正式 MP4、海报、Logo 和 wheel 通过 GitHub Release 分发。

电子配乐由脚本合成，不使用外部歌曲或采样。透明 Logo 使用内置 imagegen 生成，原始生成图单独保存于本地及 GitHub Release，未修改原始文件。

## Logo 提示词

使用内置 imagegen，透明背景。最终提示词：

```text
Use case: logo-brand. Asset type: transparent software app icon for the DICK CLI open-source command line text corruption tool, Distorted Input Context Keeper. Primary request: one polished, original, bold, vector-friendly app mark, no wordmark. Subject: a stylized capital D formed by a terminal prompt chevron and a sturdy rounded geometric outer shape, with a tiny underscore cursor. Incorporate just two restrained horizontal glitch slices so the symbol looks slightly corrupted but remains recognizable. Style: crisp flat graphic, premium indie developer tool, clean negative space and sharp edges, no 3D, no perspective. Color palette: luminous mint green with small electric purple and coral accents, designed to be clear on a near-black background. Composition: a single centered isolated logo with generous transparent padding, square aspect ratio. Background: truly transparent alpha. Constraints: no additional text, no letters other than the abstract D monogram, no mockup, no watermark, no sexual imagery, no ornamental clutter, strong legibility at small size. Output is the final icon artwork only.
```
