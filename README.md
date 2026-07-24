# PC 摄像头工具

一款使用 Python 开发的 Windows 桌面摄像头预览工具，可自由选择并显示接入电脑的一路或多路摄像头。

## 功能特点

- 自动扫描当前实际可打开的摄像头；
- 默认使用单路显示，可随时切换摄像头；
- 多路模式可自由勾选任意设备；
- 根据视频路数自动生成合理宫格；
- 软件窗口可自由放大或缩小，视频始终自动等比例适配；
- 多路设置采用可隐藏抽屉，确认选择后自动收起；
- Windows 下优先使用 MSMF，必要时回退到 DSHOW；
- 摄像头无法打开或视频流中断时提供弹窗提示；
- 切换设备或退出程序时自动释放摄像头资源。

## 使用 EXE

已经打包时，程序位于：

```text
dist\CameraTool.exe
```

使用步骤：

1. 将需要使用的摄像头连接到电脑。
2. 双击 `CameraTool.exe`，无需另外安装 Python。
3. 等待程序扫描摄像头，默认显示第一路可用设备。
4. 如果 Windows 显示安全提醒，请确认文件来源为本项目后再运行。

## 从源码运行

### 环境要求

- Windows 10 或 Windows 11
- Python 3.11 或更高版本（当前 EXE 使用 conda base 的 Python 3.13 构建）
- Tkinter
- OpenCV
- Pillow

建议在项目指定的 conda base 环境中执行：

```powershell
python -m pip install -r requirements.txt
python main.py
```

## 软件使用说明

### 单路显示

程序启动后默认进入“单路显示”：

1. 右上角“选择设备”列表只显示扫描到的可用摄像头。
2. 从列表选择其他设备后，程序会释放原设备并显示新设备。
3. 最大化、还原或自由缩小窗口时，视频会自动缩放并保持宽高比，不受摄像头原始分辨率限制。

### 多路显示

1. 点击顶部“多路显示”按钮。
2. “多路设置”按钮随即出现，摄像头选择抽屉自动展开。
3. 勾选需要同时显示的摄像头。
4. 点击“应用选择”，抽屉自动收起并显示所选视频。
5. 如需更改，点击“多路设置”重新展开抽屉；再次点击可手动收起。
6. 一路、两路、三路或更多设备会按照数量自动重新规划宫格。

### 重新扫描

接入或拔出摄像头后，点击右上角“重新扫描”。扫描会停止当前预览、重新检测设备，并刷新候选列表。

### 异常提示

- 没有检测到摄像头：检查 USB 连接、设备驱动和系统相机权限。
- 摄像头无法打开：关闭可能占用摄像头的会议或录像软件后重试。
- 视频流中断：检查设备是否被拔出；多路模式下其他正常视频会继续显示。

## 运行测试

自动化测试不需要连接真实摄像头：

```powershell
python -m unittest discover -s tests -v
```

手动验收建议：

1. 验证单路设备切换，并将软件窗口持续缩小，确认视频视图同步适配。
2. 验证单路和多路模式反复切换。
3. 验证多路设置抽屉自动展开、确认后收起和手动开关。
4. 验证三路、两路、一路之间切换时宫格不会抖动或残留空行。
5. 关闭程序后确认所有摄像头指示灯熄灭。

## 打包为 EXE

首次打包先安装构建依赖：

```powershell
python -m pip install -r requirements-build.txt
```

执行项目提供的打包脚本：

```powershell
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
```

打包完成后生成：

```text
dist\CameraTool.exe
```

该 EXE 使用 PyInstaller 单文件、无控制台窗口模式构建。`build` 是中间目录，`dist` 是输出目录；两者均已加入 `.gitignore`。

## 项目结构

```text
CameraTool/
├── camera_tool/
│   ├── app.py             # 应用启动
│   ├── camera.py          # 摄像头扫描与视频流管理
│   ├── layout.py          # 宫格及缩放计算
│   └── ui.py              # Tkinter 用户界面
├── tests/                 # 自动化测试
├── main.py                # 程序入口
├── CameraTool.spec        # PyInstaller 配置
├── build_exe.ps1          # Windows 打包脚本
├── requirements.txt       # 运行依赖
└── requirements-build.txt # 打包依赖
```
