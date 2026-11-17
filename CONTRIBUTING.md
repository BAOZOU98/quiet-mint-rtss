# 贡献指南

欢迎提交问题和改进。为了让每个改动都容易审阅：

- **一个 PR 只解决一件事**，说明触发条件、改动效果和验证方法。
- **皮肤**：修改 `scripts/render_skin.py`，运行 `--sync-src` 后一起提交生成的 `src/skin/`，不要直接编辑 PNG 或 header。附上改动前后的截图。
- **性能面板**：附改动前后截图，注明分辨率、缩放比例和字体。
- **翻译**：遵循 [翻译规范](docs/TRANSLATION.md)，通过 `scripts/localization.py` 构建，提交前运行 `check`。只依据 RTSS 的英文原文翻译，不要搬运其他汉化包的译文。
- **新增素材**：只提交自己创作或许可允许再分发的内容，并在 [第三方声明](THIRD_PARTY_NOTICES.md) 中注明来源。

## 文件格式

| 文件 | 编码与换行 |
|---|---|
| `src/localization/`、`src/skin/header` | GBK，CRLF（RTSS 要求） |
| Markdown、Python | UTF-8，LF |
| PowerShell 脚本 | UTF-8 with BOM，CRLF |

## 不要提交

本机配置、日志、录屏、备份、账号与 Token、SDK 文件、RTSS 安装包，以及 `build/`、`dist/` 下的产物。
