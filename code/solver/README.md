# 2026 国赛 B 题定位清除代码

本项目实现问题一至问题四的计算、离线仿真、图表、动作日志和官方 HTTP 客户端。问题三、四默认采用方案四（策略 B）；原方案一（策略 A）保留为可显式选择的回退版本。默认模式始终是离线仿真；只有显式写出 `--mode official` 并提供参赛队号时才会连接模拟器。本项目不会自动开始演练或正式测试。

## 安装

在 Windows PowerShell 中执行：

```powershell
Set-Location "E:\QQ Files\数模\2026shumoB\code\solver"
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

若 `py -3.11` 不存在，可将它替换为任意 Python 3.11 以上解释器的完整路径。

## 自测和回归

```powershell
.\.venv\Scripts\python.exe -m bsolver selftest
.\.venv\Scripts\python.exe scripts\run_acceptance.py
.\.venv\Scripts\python.exe scripts\run_scheme4_stress.py
```

`selftest` 会把交接验证脚本复制到 `outputs\offline\selftest\baseline_reproduction` 后运行，不覆盖上级目录的原始证据；pytest 输出保存为 `outputs\offline\selftest\pytest.txt`。第二条命令运行 N=10、13、16 的多种子矩阵和同配置、同误差场的快速层/直接兜底配对对照。第三条命令运行方案四的 240 局离线压力矩阵（问题三/四、5 种误差、随机/最小接收半径、圆内均匀/边界朝外布局、N=10/13/16），证据写入 `outputs\offline\scheme4-stress\offline_stress.json`。

`mocksim\` 是仓库原有的独立协议模拟器与 88 项一致性测试；`bsolver\simulator.py` 是正式策略单元测试使用的轻量本地仿真，两者都不会连接官方程序或消耗测试次数。

## 问题一与问题二

```powershell
.\.venv\Scripts\python.exe -m bsolver q1 --input examples\q1_input.json --output-dir outputs\offline\q1
.\.venv\Scripts\python.exe -m bsolver q2 --input examples\q2_input.json --output-dir outputs\offline\q2
```

问题一的 `result.json` 分开保存纯示向半平面交与在线保守外包络。问题二输出完整评分网格、名义测点、安全候选圆和距离余量；其中有限采样结果不表示连续全局最优或连续严格最坏误差证明。

## 问题三与问题四离线运行

```powershell
.\.venv\Scripts\python.exe -m bsolver q3 --mode offline --strategy b --seed 20260911 --count 13 --output-dir outputs\offline\q3
.\.venv\Scripts\python.exe -m bsolver q4 --mode offline --strategy b --seed 20260911 --count 13 --output-dir outputs\offline\q4
```

输出包括 `summary.json`、`config_snapshot.json`、`actions.jsonl`、`channel_states.json`、轨迹图、时间分解图及三行正式结果表模板。离线输出均标记为“本地仿真”，不能填入官方成绩表。

方案四参数固定为：Q3 正八边形 8 点（半径 974 m、无中心点），Q4 为边长 950 m、偏移 `(475, 411.4)`、旋转 30° 的 27 点三角格网；覆盖点批量扫完未知频道，并在夹角不少于 12° 时补测已发现源；当可能区域半径不超过 130 m 且额外绕行不超过 530 m 时顺路清除，覆盖完成后用 ALNS 排序集中清除。局部控制最多补测 2 次，距离上限 540 m，可直接尝试至多 6 个覆盖清除点。需要回退到原方案一时加 `--strategy a`。

## 官方模式

正式测试的数据登记和官方日志保管清单见 [`FORMAL_TEST_LOG_GUIDE.md`](FORMAL_TEST_LOG_GUIDE.md)。

先在官方模拟器中登录、进入相应测试页面并等待接口就绪，再手工执行：

```powershell
.\.venv\Scripts\python.exe -m bsolver q3 --mode official --strategy b --robot-id "实际参赛队号" --base-url "http://127.0.0.1:2026" --output-dir outputs\official\q3-独立局名
.\.venv\Scripts\python.exe -m bsolver q4 --mode official --strategy b --robot-id "实际参赛队号" --base-url "http://127.0.0.1:2026" --output-dir outputs\official\q4-独立局名
```

每次只运行一条命令，并为每局更换唯一目录名。官方模式不提供 `--output-dir` 会拒绝启动，以防覆盖上一局。客户端在 `transport\pending_request.json` 中保存未决动作；超时或响应丢失只重发原请求和原 `request_id`。若程序报告通信异常且该文件仍存在，不要发送新动作或 `/exit`，先保留目录用于复查。动作日志中的队号会被替换为 `<redacted>`，但未决恢复文件含有完成重放所需的原始请求，应妥善保存且不要放入论文附件。

## 日志与结果表

- `actions.jsonl`：请求顺序、位置、频道、业务响应和提交后的客户端状态。
- `transport_attempts.jsonl`：仅官方模式生成，逐次保存 HTTP 状态、发送/接收单调时刻、重试序号、原始业务响应或连接异常；与动作提交日志分离。
- `channel_states.json`：逐频道覆盖证据、方位历史、定位外包络和失败清除中心。
- `summary.json`：结束类型、清除数、虚拟时间、时间分解和本地仿真真值摘要。
- `formal_results_template.csv`：官方三次正式测试后人工填写案例编码、清除数、平均时间、程序运行时间和官方原名日志。

正式测试加密日志必须从模拟器导出并保持原文件名。本项目不修改、上传或替代官方日志。
