# 运行产物目录

- `offline/`：本地仿真、自测、验收和压力测试，可由脚本重新生成。
- `official/`：官方模拟器演练或正式测试的逐局记录，不可与离线结果混放。

`offline/legacy-scheme3/` 保存旧 `B题/solver` 的方案三离线证据；`official/legacy-scheme3-*` 保存从旧目录迁入的两局官方演练记录。

两类运行产物默认均不提交到 Git；目录中的 README 除外。
