# 本地 GGUF 模型存放目录

将自训练或下载的量化 `.gguf` 模型放入本目录，即可在 macOS / Windows / Linux 之间直接迁移使用：

| 版本标识 | 适用场景 | 默认文件名 |
|---|---|---|
| `3b` | 轻量高速版（8GB 内存 / 纯 CPU 推荐） | `qwen2.5-3b-instruct-q4_k_m.gguf` |
| `7b` | 均衡答题版（16GB 内存 / ≥8GB 显存推荐） | `qwen2.5-7b-instruct-q4_k_m.gguf` |
| `8b` | 高效推理版（Qwen3-8B，约 5.0GB，16GB 内存多任务首选） | `qwen3-8b-q4_k_m.gguf` |
| `14b` | 高精度推理版（Qwen3-14B，约 9.0GB，MacBook M1 Pro 16GB 推荐） | `qwen3-14b-q4_k_m.gguf` |

启动前可在弹窗中直接切换 `3b` / `7b` / `8b` / `14b` 或浏览选择任意 `.gguf` 文件，也可通过命令行指定：
```bash
python run.py --model 3b
python run.py --model 7b
python run.py --model 8b
python run.py --model 14b
```
