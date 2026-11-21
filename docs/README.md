# 私有资料库目录

将需要检索的资料放入本目录（支持 `.pdf`、`.md`、`.markdown`、`.txt`）。

放入资料后，运行以下命令或直接启动主程序即可完成切片（512 token / 重叠 50 token）并写入 `./vector_store`：

```bash
python ingest.py
```
