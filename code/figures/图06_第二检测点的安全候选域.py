"""图 6：第二检测点的安全候选域——"保证一定能收到信号"的充分条件长什么样。

精确条件 C_exact = { S : sup_{(G,r)∈Ω₁} (|S-G| - r) ≤ 0 } 不好直接算，
实现里用更保守、可认证的充分条件
    C_safe = { S : max_{V∈vert(P)} |S-V| ≤ 1000 m }，
即 S 到外包络多边形 P 的每个顶点都不超过 1000 m。因为 P 一定包含真实源位置，
而距离是凸函数、在凸多边形上的最大值必在顶点取到，所以这个条件足以保证接收。
几何上 C_safe 就是"以 P 的各顶点为心、1000 m 为半径的圆盘之交"，图中用深色标出。
叠加题目口径的 50 m 网格（x∈[0,1500]、y∈[-1000,1000]，共 1271 个格点），其中 169 个落在 C_safe 内。
运行：python 图06_第二检测点的安全候选域.py   输出：figures/图06_第二检测点的安全候选域.pdf / .png
"""
import math, importlib.util
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPoly
from matplotlib import font_manager
HERE = Path(__file__).resolve().parent
try: font_manager.fontManager.addfont('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
except Exception: pass
def _m(n, f):
    s = importlib.util.spec_from_file_location(n, str(f)); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
S = _m('S', HERE/'_绘图样式.py'); Q = _m('Q', HERE/'_问题二数据.py'); J = Q.J; C = S.C

if __name__ == '__main__':
    S.use_style()
    fig, ax = plt.subplots(figsize=(8.4, 6.4))
    # C_safe 的稠密判定（画成填色区域）
    xs = np.arange(-1300, 1801, 10.); ys = np.arange(-1300, 1301, 10.)
    XX, YY = np.meshgrid(xs, ys)
    M = np.ones_like(XX, bool)
    for v in Q.P: M &= ((XX-v[0])**2 + (YY-v[1])**2) <= 999.**2
    ax.contourf(XX, YY, M.astype(float), levels=[.5, 1.5], colors=[C['blue']], alpha=.16, zorder=2)
    ax.contour(XX, YY, M.astype(float), levels=[.5], colors=[C['blue']], linewidths=1.6, zorder=3)
    for v in Q.P:
        ax.add_patch(plt.Circle(v, 999., facecolor='none', edgecolor=C['blue'], lw=.9, ls=(0,(3,3)), alpha=.55, zorder=3))
        ax.plot([v[0]], [v[1]], 'o', ms=6, mfc=C['white'], mec=C['orange'], mew=1.8, zorder=8)
    ax.add_patch(MplPoly(Q.P, closed=True, facecolor=C['orange'], alpha=.85, edgecolor=C['orange'], lw=1.6, zorder=7))
    # 题目口径的 50 m 网格
    gx = np.arange(0, 1501, 50.); gy = np.arange(-1000, 1001, 50.)
    ok = [(x, y) for y in gy for x in gx if Q.feasible((x, y))]
    no = [(x, y) for y in gy for x in gx if not Q.feasible((x, y))]
    ax.plot([p[0] for p in no], [p[1] for p in no], '.', ms=2.2, color='#c9c8c3', zorder=4)
    ax.plot([p[0] for p in ok], [p[1] for p in ok], 'o', ms=3.4, color=C['blue'], zorder=6)
    ax.plot([0], [0], '^', ms=10, mfc=C['white'], mec=C['blue'], mew=1.9, zorder=9)
    S.tag(ax, (0, 0), '$S_1$', color=C['blue'], dy=-16)
    S.tag(ax, (1500., 0.), '$P$ 的远端两个顶点', color=C['orange'], dx=0, dy=-26)
    ax.set_aspect('equal'); ax.set_xlim(-1400, 1750); ax.set_ylim(-1350, 1350)
    ax.grid(True, zorder=1); ax.set_axisbelow(True)
    for sp in ('top','right'): ax.spines[sp].set_visible(False)
    ax.set_xlabel('x / m'); ax.set_ylabel('y / m')
    ax.set_title('图 6　第二检测点的安全候选域 $C_{safe}=\\{S:\\max_{V\\in vert(P)}|S-V|\\leq 1000\\ \\mathrm{m}\\}$',
                 fontsize=13, pad=12)
    S.note(ax, '浅蓝区域 = 三个顶点的 1000 m 圆盘之交（充分条件，偏保守）\n'
               '蓝点 = 50 m 网格里可行的 %d 个候选，灰点 = 不可行的 %d 个\n'
               '橙色细长条 = 首次观测的外包络 $P$' % (len(ok), len(no)), loc='lower left')
    print('已输出：', S.save(fig, '图06_第二检测点的安全候选域'), '可行 %d 个' % len(ok))
