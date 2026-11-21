# NetHelper 部署与运行教程

基于本地 RAG（ChromaDB + `bge-small-zh-v1.5`）与本地 GGUF 模型（`llama.cpp` / `Qwen2.5-3B` 或 `7B`）的左下角悬浮问答助手，支持 macOS / Windows / Linux。

---

## 1. 目录结构

```text
net-helper/
├── config.yaml          # 核心配置文件（模型版本、快捷键、窗口透明度与尺寸）
├── run.py               # 跨平台一键启动脚本
├── run.sh               # macOS / Linux 启动脚本
├── run.bat              # Windows 启动脚本
├── build.py             # 三平台独立可执行程序打包脚本
├── ingest.py            # 私有资料切片入库脚本
├── main.py              # 桌面程序入口
├── docs/                # 【用户放置】私有资料（支持 PDF / MD / TXT）
├── models/              # 【用户放置】GGUF 模型文件
└── vector_store/        # 自动生成的 ChromaDB 向量数据库
```

---

## 2. 准备工作（必做）

### 第一步：放入私有资料
将你的 `.pdf`、`.md` 或 `.txt` 资料放入 `docs/` 目录。

### 第二步：准备模型与离线组件（首次联网一键补全，后续永久断网运行）
- **推荐方式（开箱即用）**：直接启动程序，在启动设置弹窗中选择 `3B` 或 `7B` 版本，点击 **「一键下载离线组件」**，程序会自动将以下组件断点续传至本地目录，之后即可**永久断网运行**：
  - 本地大模型：`models/qwen2.5-3b-instruct-q4_k_m.gguf`（~2.0 GB）或 `models/qwen2.5-7b-instruct-q4_k_m.gguf`（~4.7 GB）
  - 本地嵌入模型：`models/bge-small-zh-v1.5/`（~95 MB）
  - 本地公式渲染：`assets/mathjax/es5/tex-mml-chtml.js`
- **手动迁移方式**：也可直接将自训练或已下载的 `.gguf` 模型放入 `models/` 目录（若文件名不同，点击弹窗「选择 GGUF」指定即可）。

---

## 3. 方式一：源码一键运行（推荐开发/自用）

前置条件：已安装 **Python 3.10+**。

### macOS / Linux
```bash
chmod +x run.sh
./run.sh
```

### Windows
双击运行 `run.bat`，或在命令行执行：
```bat
run.bat
```

### 常用启动参数
```bash
# 指定使用 7B 或 3B 模型启动
python run.py --model 7b
python run.py --model 3b

# 资料库有更新时，强制重建向量索引
python run.py --ingest

# 仅执行资料入库，不启动界面
python run.py --ingest-only
```

---

## 4. 方式二：打包为独立程序分发（macOS / Windows / Linux）

### 本地打包
在目标操作系统上运行（会自动安装 PyInstaller 并生成独立目录与压缩包）：
```bash
# 打包并生成对应系统的 .zip / .tar.gz 分发包（输出在 dist/ 目录）
python build.py --archive
```

### GitHub Actions 三平台自动打包
仓库已内置 `.github/workflows/release.yml`。推送版本标签即可同时构建 macOS、Windows、Linux 三平台产物：
```bash
git tag v1.0.0
git push origin v1.0.0
```
构建完成后在 GitHub 仓库的 **Actions** 页面下载对应系统的压缩包。

### 分发包使用步骤
1. 解压分发包后，将资料放入同级 `docs/`，将 `.gguf` 模型放入同级 `models/`。
2. 首次运行前可执行入库（或直接双击启动程序，在提示弹窗中点击「是」自动入库）：
   - Windows：`NetHelper.exe --ingest-only`
   - Linux：`./NetHelper --ingest-only`
   - macOS：`./NetHelper.app/Contents/MacOS/NetHelper --ingest-only`
3. 双击 `NetHelper.exe` / `NetHelper.app` / `./NetHelper` 启动。

---

## 5. 操作说明

1. **启动设置弹窗**：每次启动前可选择 `3B` / `7B` 模型版本，并按下自定义全局隐藏/显示快捷键（默认 `Ctrl+Shift+H`）。
2. **提问**：左下角弹出半透明输入框，输入问题后按 `Enter` 提交。
3. **等待生成**：生成期间界面不输出任何流式文字，仅显示底部细进度条。
4. **查看答案与继续提问**：生成结束后一次性弹出完整答案（支持 Markdown、代码高亮与 LaTeX 公式）；点击右上角 **`Restart`** 即可清空并返回输入框。
5. **隐藏 / 呼出**：随时按设定的全局快捷键或 `Esc` 隐藏/恢复窗口；系统托盘右键可修改快捷键或退出程序。

---

## 6. 常见问题排查

1. **macOS 全局快捷键无效**
   - 打开「系统设置 → 隐私与安全性 → 辅助功能」，勾选运行该程序的终端或 `NetHelper.app`，重启软件即可。
2. **Windows / Linux 安装 `llama-cpp-python` 失败或想启用 NVIDIA GPU 加速**
   - 执行 `pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu124` 安装预编译 CUDA 版本（纯 CPU 可直接 `pip install llama-cpp-python`）。
3. **跨电脑迁移**
   - 直接复制整个项目文件夹（或解压后的分发目录）连同 `models/`、`docs/`、`vector_store/`、`config.yaml` 到另一台电脑即可使用；若目标电脑为不同操作系统，仅需使用对应平台的源码环境或打包程序即可，模型与向量库完全通用。
4. **改用 Ollama**
   - 将 `config.yaml` 中 `llm.provider` 改为 `"ollama"`，并启动 Ollama 与对应模型（如 `ollama run qwen2.5:3b`）。
