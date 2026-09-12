# 外部对照方案：li2396803/cumcm2026 的 B 题解法

来源：https://github.com/li2396803/cumcm2026 ，`b-radio-interference-localization/outputs/code/`
许可：MIT License（见同目录 `LICENSE`），版权 © 2026 Ada (GitHub: li2396803)。
本目录只收录其 MIT 覆盖的原创代码与结果数据，未收录其 `data/` 下的赛题材料。

收录的文件（原样拷贝，未做任何修改）：

| 文件 | 作用 |
|---|---|
| `lib/geom.py` | 他们的几何引擎（楔形半平面、凸多边形、覆盖点生成等） |
| `lib/sim.py` | 他们的本地模拟器（时间常数与题面一致） |
| `lib/strategy.py` | v1 策略（自适应插序 + 交会追踪 + 清除扫描） |
| `lib/strategy2.py` | v2 策略（滚动时域重优化 + 朝向贝叶斯信念 + 风险可控自适应侦察） |
| `cover_points.json` | 他们求解出的侦察点集：问题三 8 点、问题四 19 点（间距 1000 m 那一档） |

对照实验脚本是我们自己写的：`code/experiments/方案七_7.1_外部方案对照.py`，
它把两边的策略放到**同一套案例、同一套误差场、同一套时间常数**下跑，结论见
`docs/review/外部方案对照_li2396803.md`。
