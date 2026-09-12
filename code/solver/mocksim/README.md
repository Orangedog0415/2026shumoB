# 本地 mock 模拟器（`code/solver/mocksim`）

按 `docs/problem/附件2.docx` 实现的**本地假模拟器**，在没有官方模拟器、或不想占用演练时段的
情况下，把官方 HTTP 客户端和问题三/四的策略完整跑通，并注入通信故障检验客户端的幂等与重试。

**这不是官方模拟器**，不联网、不登录、不消耗正式测试机会、不产生官方加密日志。
官方模拟器的下载与登录见 `docs/problem/附件1.docx` §4。

只用 Python 3 标准库。

## 文件

| 文件 | 作用 |
|---|---|
| `world.py` | 真值世界：源生成、5 种误差模型、按微秒累计的虚拟时钟、`measure`/`clear` 物理规则 |
| `protocol.py` | 附件2 §5 的请求校验：头部、BOM、重复键、嵌套深度、65536 字节、字段类型与范围、未知字段、标识符 |
| `server.py` | HTTP 服务与一局测试的状态机、`request_id` 幂等、并发检测、故障注入、JSONL 行为日志 |
| `demo_client.py` | 附件2 §11 的官方示例客户端，可指定地址与队号 |
| `conformance_test.py` | 协议一致性自测，88 项 |

真实源数据只在模拟器进程里。策略只能通过 HTTP 拿到 `measure_result` / `svd_deg` / `clear_result`，
拿不到源坐标、数量、接收半径、类型、朝向和清除状态——和官方模拟器的信息边界一致。

## 运行（Windows PowerShell，仓库根目录）

```powershell
# 1) 协议一致性自测（约 25 s，全部通过时退出码 0）
python code\solver\mocksim\conformance_test.py

# 2) 起一局问题三（全向源），默认 http://127.0.0.1:2026
python code\solver\mocksim\server.py --problem 3 --n 13 --seed 1 --robot-id TEST-TEAM

# 3) 另开一个 PowerShell 窗口，用附件2 §11 的示例客户端打一遍
python code\solver\mocksim\demo_client.py --base http://127.0.0.1:2026 --robot-id TEST-TEAM

# 4) 问题四最难场景：源全在边界、定向且朝外、接收半径全取下限、每点 ±1° 极端误差
python code\solver\mocksim\server.py --problem 4 --n 16 --seed 42 --layout outward `
    --radius min --error iid_pm1 --log run.jsonl --truth-out truth.json

# 5) 客户端故障注入：第 3 个请求已执行但响应丢失，第 5 个返回非 JSON，第 7 个执行前断连
python code\solver\mocksim\server.py --problem 3 --seed 1 `
    --fault "3:drop,5:badjson,7:close,9:delay=2000,11:http500,13:http429"

# 调试时跳过 5 秒倒计时、关掉逐条打印
python code\solver\mocksim\server.py --countdown 0 --quiet
```

`server.py` 在本局全部清除时退出码 0，否则 1，方便脚本批量跑。

## 主要参数

**案例**

| 参数 | 默认 | 说明 |
|---|---|---|
| `--problem {3,4}` | 3 | 3 = 全部全向源；4 = 混合（含定向源） |
| `--n` | 随机 10–16 | 干扰源数量 |
| `--seed` | 随机 | 案例种子；同种子同布局可复现 |
| `--layout {uniform,boundary,outward}` | uniform | 均匀 / 贴边界 / 贴边界且定向源朝外（问题四最难） |
| `--radius {rand,min}` | rand | 有效接收半径 U(1000,1500) 或全取下限 1000 |
| `--pd` | 0.65 | 问题四中定向源比例 |
| `--error` | orig_sin | `orig_sin`（交接版空间正弦场）、`iid_uniform`、`const_+1`、`const_-1`、`iid_pm1`、`zero` |
| `--salt` | 0 | 只换误差场、不换源布局，用于配对对照 |

五种误差模型与 `code/experiments/方案一_压力测试.py` 的 `ERR` 表一一对应，
全部满足"同一点、同一频道误差固定"——原地重复测量拿到的是同一个值，不能靠重测降噪。

**服务**

| 参数 | 默认 | 说明 |
|---|---|---|
| `--port` | 2026 | 官方默认端口 |
| `--robot-id` | TEST-TEAM | 模拟"当前登录参赛队号"，请求里的 `robot_id` 必须逐字节相同 |
| `--countdown` | 5 | 开放接口前的倒计时秒数，此期间连接直接关闭 |
| `--window` | 1500 | 25 分钟测试窗口 |
| `--enter-limit` | 1200 | `/enter` 成功后的 20 分钟程序运行时间 |
| `--idem-limit` | 20000 | 本局幂等记录上限，超出返回 429 |

**输出与故障注入**

| 参数 | 说明 |
|---|---|
| `--log run.jsonl` | 每条请求/响应、执行后位置与频道、分项虚拟时间 |
| `--truth-out truth.json` | 结束后写出本局真值（**测试期间不要让策略读它**） |
| `--mode {drill,formal}` | drill 结束时显示源数量统计；formal 不显示，模拟正式测试 |
| `--reveal` | 开局就打印真值，仅调试用 |
| `--fault "N:kind"` | 见下 |

故障注入按"到达执行阶段的请求"计数（`/enter` 是第 1 个）：

| kind | 行为 | 用来测什么 |
|---|---|---|
| `drop` | **执行后**丢弃响应、关闭连接 | 服务端已执行但响应丢失：客户端必须用同 ID、同内容重发，且不能重复计时 |
| `close` | 执行前关闭连接 | 连接中断、状态不明 |
| `badjson` | 执行后返回非 JSON 体 | 客户端必须同时处理"收到 JSON"和"收到别的东西" |
| `delay=MS` | 执行后延迟 MS 毫秒再响应 | 超时与重试预算；也用来构造并发 409 |
| `http429` / `http500` | 不执行，返回该状态码 | 429 等待重试、500 按状态不明同 ID 重试 |

## 已实现并自测通过的行为（88 项，`conformance_test.py`）

- **路径与方法**：`/measures`、`/measure/`、`/Measure`、带查询参数 → 404；GET/PUT/DELETE/PATCH → 405
- **头部**：`text/plain`、`application/json; boundary=x`、`Content-Encoding: gzip` → 415；`charset=utf-8` 接受；体 >65536 字节 → 413
- **请求体 400**：非法 JSON、重复键、BOM、顶层非对象、缺字段、`arena_id` 非字符串、`robot_id` 为空、`request_id` 含控制字符或超 128 字节、缺 `position.y`、`NaN`、坐标超 2e6、`channel` 为 1.5 / 0 / 21 / `"1"` / `true`、`position` 非对象；`channel: 1.0` 接受
- **200 + accepted=false**：未 `/enter` 就动作、重复 `/enter`、`arena_id` 或 `robot_id` 不匹配、顶层或 `position` 含未声明字段；此时响应只含 3 个公共字段且 `virtual_time_s` 为 0；这些拒绝**不占用** `request_id`，修正后可复用
- **幂等**：同 ID 同内容重放返回首次完整响应且不重复推进时钟；同 ID 改位置/频道/路径 → 409；未决动作期间发不同动作 → 409；幂等记录达上限 → 429
- **计时**：附件2 §10 示例逐步复现 105 / 111 / 194 / 199；思路 §2.3 的 measure→clear→measure = 215 s；`/clear` 的 `channel` 不切换测向机频道也不计切换耗时
- **物理**：接收半径外 → `no_signal`；≤5 m 且在覆盖角内 → `near` 且不返回 `svd_deg`；定向源 180° 覆盖含边界、背面 `no_signal`；清除半径 20 m 含边界、与朝向无关；重复清除 → `no_target_in_range`；已清除频道 → `no_signal`；同一点示向度恒定、误差 ≤1°、两位小数
- **结束**：`/exit` 返回 `user_exit` 且不推进时钟；接口未开放、`/exit` 之后、现实时间截止、虚拟时间超 360000 s → 连接直接关闭，没有 JSON 体
- **故障注入**：drop / close / badjson / delay / 429 / 500，以及丢响应后的同 ID 重放与同 ID 改内容 409

## 与官方模拟器的差异与限制

本模块按附件1、附件2的文字实现，以下几点文档没有写死，这里做了选择，**联调时以官方行为为准**：

1. **检查顺序**：同时存在结构错误（400 类）和未知字段（accepted=false 类）时，本模拟器先报 400。
2. **状态类拒绝是否占用 `request_id`**：附件2 只写明"业务上已被接受的动作占用"，因此本模拟器规定
   只有 `accepted=true` 才占用；未 `/enter` 等状态拒绝不占用。
3. **429**：只实现了"幂等记录达上限"和故障注入两种触发，没有实现官方的连接/无效流量保护。
4. **`Transfer-Encoding`**：不支持，返回 400。官方文档未说明。
5. **虚拟时钟取整**：每个动作的耗时各自四舍五入到微秒后累加。官方只说"内部按微秒累计"。
6. **`/exit` 后接口立即关闭**，同附件2；因此 `/exit` 响应丢失后无法重放确认，这与官方一致。
7. 不做登录、不校验服务器时间、不生成官方加密日志、不显示测试案例编码之外的官方界面信息。
   这里的 `MOCK-xxxxxxxx` 案例编码只是本地配置的哈希。

## 下一步

`code/solver/` 的官方 HTTP 客户端和策略 A/B 还没写（见 `docs/handover/交接材料.md` 第二、四节）。
写好后应先对这个 mock 跑通，包括带 `--fault` 的故障注入，再去连官方模拟器做演练。
