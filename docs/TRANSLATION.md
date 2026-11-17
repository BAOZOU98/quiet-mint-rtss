# 翻译规范

简体中文语言包的文风与术语约定。新增或修改译文时请遵循，保持全包一致。
译文只依据 RTSS 自带的英文原文，不引用其他中文翻译。

## 风格

- 准确、简洁、自然的简体中文技术文档语气；不逐词硬译，也不添油加醋。不用“您”，直接陈述（“可以……”“启用后……”）。
- 中文与英文、数字之间加一个半角空格：`OSD 缩放`、`64 位`、`1% Low`。中文标点用全角（，。：；？！“”（））。
  但紧贴英文或数字的括号内全是英文时可用半角。
- 界面字符串（ui）尽量短：按钮/复选框/菜单通常 2–8 个汉字；原文没有句号就不加句号。
- 帮助文件第一行是标题，保持为短标题；后续段落、空行、列表结构（`- `）与英文原文一一对应，不合并、不拆分段落。
- `<User interface> tab` 这类界面引用译为 `“用户界面”选项卡`；尖括号包裹的界面名称一律改成中文引号。
- 原文笔误（acheiving、postiong 等）按正确含义翻译。
- 只能使用 GBK 可编码的字符：不要用 emoji、特殊箭头（→ 可以用“到”代替）、全角空格以外的特殊空白。≥ ≤ × ÷ … — · 可以使用。

## 必须原样保留

- 格式占位符及其顺序：`%s %d %u %x %I64u %.1f %%` 等，以及 `%PRODUCTNAME%`；字面量 `\n`、`\t`。占位符**顺序不能变**，必要时调整中文语序来适配。
- 产品名、商标、API 名：RTSS、RivaTuner Statistics Server、MSI Afterburner、NVIDIA、AMD、Intel、Reflex、PresentMon、FrameView、FCAT、Direct3D、DirectX、OpenGL、Vulkan、DXGI、Detours、NVENC、QSV、VCE、AMF、HAL、HwInfo、CPU、GPU、VRAM、API、FPS、ms、MB 等。
- 快捷键名（Ctrl、Alt、Shift、Pause、F1…）、文件名、注册表/配置项名、命令行参数。
- 宏/标签语法，如 `<FR>`、`<FT>`、`<C=...>`、`%CPU%` 等嵌入标签，保持原样。

## 术语表（必须统一）

| English | 中文 |
|---|---|
| On-Screen Display (OSD) | 首次出现于帮助正文可写“屏幕显示（OSD）”，其余一律 `OSD` |
| Show On-Screen Display | 显示 OSD |
| profile / application profile | 配置文件 / 应用程序配置文件 |
| Global profile | 全局配置文件 |
| pre-created profiles | 预置配置文件 |
| Application detection level | 应用程序检测级别 |
| None / Low / Medium / High（检测级别） | 关闭 / 低 / 中 / 高 |
| Stealth mode | 隐身模式 |
| Custom Direct3D support | 自定义 Direct3D 支持 |
| framerate / frametime | 帧率 / 帧时间 |
| Framerate limit / frametime limit | 帧率上限 / 帧时间上限 |
| framerate limiter | 帧率限制器 |
| Scanline sync | 扫描线同步 |
| tearline | 撕裂线 |
| framepacing | 帧节奏 |
| async / front edge sync / back edge sync（限制模式） | 异步 / 前沿同步 / 后沿同步 |
| VSync | 垂直同步 |
| vertical blanking interval (VBlank) | 垂直消隐区间 |
| refresh rate / refresh period | 刷新率 / 刷新周期 |
| rendering mode | 渲染模式 |
| Vector 2D / Vector 3D / Raster 3D | 矢量 2D / 矢量 3D / 光栅 3D |
| coordinate space | 坐标空间 |
| Viewport / Framebuffer | 视口 / 帧缓冲 |
| On-Screen Display shadow | OSD 阴影 |
| background fill | 背景填充 |
| On-Screen Display palette / color | OSD 调色板 / 颜色 |
| zoom | 缩放 |
| Show own statistics | 显示 RTSS 自身统计 |
| benchmark | 基准测试 |
| statistics | 统计 |
| 1% low / 0.1% low framerate | 1% Low 帧率 / 0.1% Low 帧率 |
| percentile | 百分位 |
| averaging interval | 平均间隔 |
| peak framerate | 峰值帧率 |
| frametime history / graph | 帧时间历史 / 图表 |
| hotkey | 热键 |
| screenshot | 截图 |
| video capture / prerecord | 视频录制 / 预录制 |
| encoder / encoder server | 编码器 / 编码服务器 |
| plugin | 插件 |
| Overlay editor | 叠加层编辑器 |
| overlay / layer | 叠加层 / 图层 |
| data source | 数据源 |
| sensor | 传感器 |
| embedded image / animated image | 嵌入图像 / 动画图像 |
| sprite | 精灵图 |
| macro / tag | 宏 / 标签 |
| injection / injection delay | 注入 / 注入延迟 |
| hook / hooking | 挂钩 |
| passive waiting | 被动等待 |
| skin / skinned | 皮肤 / 皮肤化 |
| tooltip | 工具提示 |
| traditional / layered with colorkey / layered with alpha | 传统 / 分层（颜色键） / 分层（Alpha） |
| graph / diagram / barchart（图表样式） | 折线图 / 面积图 / 柱状图 |
| advanced properties / Setup | 高级设置 / 设置 |
| layered window | 分层窗口 |
| scale factor | 缩放比例 |
| update checking | 更新检查 |
| beta version | 测试版 |
| cache | 缓存 |
| latency / latency markers | 延迟 / 延迟标记 |
| PC latency | PC 延迟 |
| Desktop Overlay Host | 桌面叠加层宿主（DesktopOverlayHost） |
| tray icon / system tray | 托盘图标 / 系统托盘 |
| Add / Remove / Defaults（主窗口按钮） | 添加 / 移除 / 默认 |
| Start with Windows | 随 Windows 启动 |
| enable / disable | 启用 / 禁用 |
| on / off（开关状态） | 开启 / 关闭 |
| nameless | 未命名 |
| N/A | 不可用 |
