# 本地 GGUF 模型存放目录

将自训练或下载的量化 `.gguf` 模型放入本目录，即可在 macOS / Windows / Linux 之间直接迁移使用：

| 版本标识 | 适用场景 | 默认文件名 |
|---|---|---|
| `3b` | 轻量高速版（8GB 内存 / 纯 CPU 推荐） | `qwen2.5-3b-instruct-q4_k_m.gguf` |
| `7b` | 高精度答题版（16GB 内存 / ≥8GB 显存推荐） | `qwen2.5-7b-instruct-q4_k_m.gguf` |

启动前可在弹窗中直接切换 `3b` / `7b` 或浏览选择任意 `.gguf` 文件，也可通过命令行指定：
```bash
python run.py --model 3b
python run.py --model 7b
```
