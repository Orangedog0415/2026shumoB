"""图 13：问题四覆盖网的四次迭代——点数、巡回长度与最终的每源平均时间。

四个版本用的都是同一条三角网证书（与圆盘相交的三角形三边 ≤1000 m + 凸包含圆），只是构造方式越来越自由：
  方案三  h=990 m 规则三角格　　27 点，26 679 m
  方案四  h=950 m 偏移优化格网　27 点，25 111 m
  方案六  模拟退火得到的非规则三角网　27 点，17 830 m
  方案七  同心环枚举给起点再退火　25 点，17 547 m
左图是"网本身有多贵"（点数 × 每点检测 + 巡回 / 5 的粗探代价估计），右图是接进完整求解器后真实的每源平均时间。
两张分开画，而不是画双纵轴——双纵轴会制造并不存在的相关性。
运行：python 图13_覆盖网演化.py   输出：figures/图13_覆盖网演化.pdf / .png
"""
import math, importlib.util
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import font_manager
HERE = Path(__file__).resolve().parent
try: font_manager.fontManager.addfont('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
except Exception: pass
def _m(n, f):
    s = importlib.util.spec_from_file_location(n, str(f)); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
S = _m('S', HERE/'_绘图样式.py'); C = S.C
L = _m('L', HERE.parent/'experiments'/'方案四_实验台.py')

def tl(net):
    T = L.tour_nn2opt([tuple(p) for p in net])
    return L.dist((0,0), T[0]) + sum(L.dist(T[i], T[i+1]) for i in range(len(T)-1))

# 每源平均时间（问题四训练集，来自 results/ 下各版本的运行输出）
T4 = {'方案三': 745.0, '方案四': 688.9, '方案六': 553.3, '方案七': 529.1}

if __name__ == '__main__':
    S.use_style()
    NETS = [('方案三\nh=990 格网', L.NET4_V3()), ('方案四\nh=950 格网', L.NET4_V4()),
            ('方案六\n退火三角网', L.NET4_V6()), ('方案七\n环起点+退火', L.NET4_V7())]
    names = [n for n, _ in NETS]
    ks = np.array([len(p) for _, p in NETS], float)
    ls = np.array([tl(p) for _, p in NETS])
    cost = ls/5 + ks*20*5      # 粗探代价估计：巡回 / 5 + 每点 20 个频道 × 5 s

    fig, axes = plt.subplots(1, 3, figsize=(13.6, 4.8))
    x = np.arange(4)
    shades = ['#bcd6f2', '#8fbaea', '#5d9ae1', C['blue']]

    ax = axes[0]
    ax.bar(x, ls, color=shades, width=.62)
    for i, v in enumerate(ls): ax.text(i, v+400, format(round(v), ','), ha='center', fontsize=9, color=C['ink2'])
    ax.set_xticks(x); ax.set_xticklabels(names, fontsize=9.0)
    ax.set_ylabel('巡回长度 / m'); ax.set_ylim(0, ls.max()*1.18)
    ax.grid(True, axis='y'); ax.set_axisbelow(True)
    for sp in ('top','right'): ax.spines[sp].set_visible(False)
    ax.set_title('(a) 巡回长度：26.7 km → 17.5 km', pad=9)

    ax = axes[1]
    ax.bar(x, cost, color=shades, width=.62)
    for i, v in enumerate(cost): ax.text(i, v+90, '%.0f s' % v, ha='center', fontsize=9, color=C['ink2'])
    for i, k in enumerate(ks): ax.text(i, cost[i]*.5, '%d 点' % k, ha='center', fontsize=9.5, color=C['white'])
    ax.set_xticks(x); ax.set_xticklabels(names, fontsize=9.0)
    ax.set_ylabel('粗探代价估计 / s'); ax.set_ylim(0, cost.max()*1.18)
    ax.grid(True, axis='y'); ax.set_axisbelow(True)
    for sp in ('top','right'): ax.spines[sp].set_visible(False)
    ax.set_title('(b) 粗探代价 = 巡回/5 + 点数×20×5 s', pad=9)

    ax = axes[2]
    vals = np.array([T4[n.split('\n')[0]] for n in names])
    ax.bar(x, vals, color=shades, width=.62)
    for i, v in enumerate(vals): ax.text(i, v+9, '%.1f' % v, ha='center', fontsize=9, color=C['ink2'])
    ax.set_xticks(x); ax.set_xticklabels(names, fontsize=9.0)
    ax.set_ylabel('每源平均定位清除时间 / s'); ax.set_ylim(0, vals.max()*1.18)
    ax.grid(True, axis='y'); ax.set_axisbelow(True)
    for sp in ('top','right'): ax.spines[sp].set_visible(False)
    ax.set_title('(c) 接进求解器后的实际时间（问题四训练集）', pad=9)
    S.note(ax, '相对方案三 -29.0%', loc='upper right')

    fig.suptitle('图 13　问题四覆盖网的四次迭代：证书不变，代价逐步下降', fontsize=13.5, color=C['ink'], y=1.0)
    print('已输出：', S.save(fig, '图13_覆盖网演化'))
