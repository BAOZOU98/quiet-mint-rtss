# 构建

所有产物都输出到 `build/` 和 `dist/`，这两个目录不进入 Git。

## 准备

- Windows，已安装 RTSS 7.3.7
- Python 3.10+：`python -m pip install -r requirements.txt`
- 桥接插件另需 MSVC Build Tools（x86 / x64）和 NVIDIA FrameView SDK
- 皮肤文字使用 [Noto Sans SC](https://fonts.google.com/noto/specimen/Noto+Sans+SC)（可变字重版本）

脚本默认 RTSS 位于 `C:\Program Files (x86)\RivaTuner Statistics Server`，可用 `--rtss` 指定其他位置。

## 桥接插件

```powershell
scripts\build_bridge.cmd
```

输出 `build/bridge/FrameViewBridge.dll` 与 `FrameViewBridge64.exe`。
路径可用环境变量 `RTSS_DIR`、`FRAMEVIEW_SDK_DIR`、`VS_VCVARS` 覆盖。

## 皮肤

```powershell
python scripts/render_skin.py --compile
```

脚本绘制全部位图、生成 `header`，再调用 RTSS 内置的编译器得到 `build/Skins/QuietMintCN.usf`。
编译在 `build/rtss-tool/` 中的 RTSS 副本里进行，以当前用户身份运行，不需要管理员权限，也不会改动已安装的 RTSS。

- `--sync-src`：把生成结果同步到 `src/skin/`，提交前使用。
- `--cn-font`：指定 Noto Sans SC 的路径。

布局、配色和控件尺寸都定义在 `render_skin.py` 顶部；改动后重新运行即可。
控件 ID 与 header 语法参照 RTSS SDK 中的《USF skin format reference》。

## 语言包

`src/localization/CHN/` 就是最终的语言包（GBK 编码、CRLF 换行，这是 RTSS 的要求）。
翻译工作在 UTF-8 的工作文件里进行，再由脚本转换：

```powershell
python scripts/localization.py extract   # 从 RTSS 提取英文原文 → build/l10n-work/
python scripts/localization.py build     # 工作文件 → src/localization/CHN/
python scripts/localization.py check     # 与本机 RTSS 比对：缺失、过时条目和占位符
```

- `extract` 以 RTSS 自带的俄语示例包为条目结构的基准（官方会保持它与程序同步），英文帮助取自 RTSS 的 `Help/` 目录；已有译文会一并带出，只需补译新增条目。
- 界面条目在 `build/l10n-work/ui/**.json` 中填写 `dst`，帮助在 `build/l10n-work/help-zh/` 中逐行对应英文。
- `build` 会拒绝空译文和顺序不一致的格式占位符（`%s`、`%d`、`\n` 等）。
- 术语与文风见 [`docs/TRANSLATION.md`](TRANSLATION.md)。

RTSS 升级后，先运行 `check` 查看差异，再 `extract` → 补译 → `build`。

## 打包

```powershell
python scripts/package_release.py
```

需要先完成桥接插件和皮肤的构建。产物为 `dist/QuietMint-RTSS-patch.zip`，用于上传 GitHub Release。
`dist/QuietMint-RTSS/` 已存在时脚本会停止，请先移走旧产物。

## 测试安装器

```powershell
python tests/test_installer.py
```

在 `build/` 下建立模拟的 RTSS 目录，验证首次安装、重复安装、还原和复制失败时的回滚，不会触碰真实安装。
需要先完成打包。
