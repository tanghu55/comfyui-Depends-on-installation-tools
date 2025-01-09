# ComfyUI 依赖安装工具

这是一个用于管理 ComfyUI 依赖的图形界面工具。它可以帮助你轻松地安装、卸载和管理 ComfyUI 所需的 Python 包。

## 功能特点

- 图形界面操作，简单易用
- 支持选择 requirements.txt 文件
- 支持选择 Python 环境目录
- 支持选择 pip 镜像源加速下载
- 显示依赖包的安装状态和版本信息
- 支持单个包的安装/卸载
- 支持批量安装/卸载
- 显示安装进度和状态信息

## 使用方法

1. 安装依赖
```bash
pip install -r requirements.txt
```

2. 运行程序
```bash
python comfy_dependency_installer.py
```

3. 使用步骤
   - 点击"选择文件"按钮选择 requirements.txt 文件
   - 点击"选择文件夹"按钮选择 Python 环境目录
   - 选择合适的 pip 镜像源（可选）
   - 使用界面上的按钮进行依赖管理操作

## 注意事项

- 请确保选择正确的 Python 环境目录（包含 python.exe）
- 建议使用国内镜像源以加快下载速度
- 安装/卸载过程中请耐心等待
- 如果遇到错误，请查看错误提示信息 