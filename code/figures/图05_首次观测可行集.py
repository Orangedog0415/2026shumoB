"""图 5：一次测向之后，干扰源可能在哪——首次观测的可行集 Ω₁ 与它的外包络多边形 P。

首次返回示向度时，源状态 (G, r) 的可行集是
    Ω₁ = { (G,r) : G ∈ 目标圆盘 ∩ W₁,  1000 ≤ r ≤ 1500,  5 < |G-S₁| ≤ r }。
也就是说，一次观测给出的不只是角度：它还排除了接收距离之外（|G-S₁| > r ≤ 1500）与 near 范围之内（≤5 m）的状态。
算法里用的是它在平面上的外包络多边形 P = W₁ ∩ {|X-S₁| ≤ 1500} ∩ 目标圆盘，
P 是一条长 1500 m、末端才 53 m 宽的细长条——(b) 用横向放大画出这个宽度，说明"1° 很小但不等于没有不确定性"。
运行：python 图05_首次观测可行集.py   输出：figures/图05_首次观测可行集.pdf / .png
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
    fig, axes = plt.subplots(1, 2, figsize=(11.6, 5.2))

    ax = axes[0]; S.field_axes(ax, 1800., pad=200.)
    ax.add_patch(MplPoly(Q.P, closed=True, facecolor=C['orange'], alpha=.75, edgecolor=C['orange'], lw=1.4, zorder=6))
    ax.add_patch(plt.Circle(Q.S1, 1500., facecolor='none', edgecolor=C['blue'], lw=1.2, ls=(0,(5,4)), zorder=4))
    ax.add_patch(plt.Circle(Q.S1, 1000., facecolor='none', edgecolor=C['blue'], lw=1.0, ls=(0,(2,3)), zorder=4))
    ax.plot([Q.S1[0]], [Q.S1[1]], '^', ms=10, mfc=C['white'], mec=C['blue'], mew=1.9, zorder=9)
    S.tag(ax, Q.S1, '$S_1=(0,0)$，示向度 $0°$', color=C['blue'], dy=-20)
    S.tag(ax, (0, 1500), '接收半径上界 1500 m', color=C['blue'], dy=-13)
    S.tag(ax, (0, 1000), '接收半径下界 1000 m', color=C['blue'], dy=-13)
    ax.set_title('(a) 可行集在平面上的外包络 $P$', pad=9)
    ax.set_xlabel('x / m'); ax.set_ylabel('y / m')
    S.note(ax, '$\\Omega_1=\\{(G,r): G\\in\\mathcal{D}\\cap W_1,\\ 1000\\leq r\\leq 1500,\\ 5<|G-S_1|\\leq r\\}$\n'
               '$P$ 的顶点数 %d，面积 %.0f m²，长 1500 m' % (len(Q.P), abs(sum(
                   Q.P[i][0]*Q.P[(i+1)%len(Q.P)][1]-Q.P[(i+1)%len(Q.P)][0]*Q.P[i][1] for i in range(len(Q.P))))/2))

    ax = axes[1]
    ax.add_patch(MplPoly(Q.P, closed=True, facecolor=C['orange'], alpha=.75, edgecolor=C['orange'], lw=1.4, zorder=6))
    for d in (500., 1000., 1500.):
        w = d*math.tan(J.DELTA)
        ax.plot([d, d], [-w, w], '-', color=C['ink'], lw=1.6, zorder=8)
        ax.plot([d, d], [-w, w], '_', ms=7, color=C['ink'], zorder=8)
        S.tag(ax, (d, w), '%.0f m 处宽 %.1f m' % (d, 2*w), color=C['ink'], dy=16, dx=-6)
    ax.plot([0], [0], '^', ms=10, mfc=C['white'], mec=C['blue'], mew=1.9, zorder=9)
    ax.set_xlim(-60, 1620); ax.set_ylim(-84, 84); ax.set_box_aspect(1)
    ax.grid(True, zorder=1); ax.set_axisbelow(True)
    for sp in ('top','right'): ax.spines[sp].set_visible(False)
    ax.set_title('(b) 纵向放大 10 倍：$P$ 的真实宽度', pad=9)
    ax.set_xlabel('沿示向度方向 / m'); ax.set_ylabel('垂直方向 / m')
    S.note(ax, '半宽 $=d\\tan\\delta$，$\\delta=1.005°$\n所以一次观测最多把源锁在一条 53 m 宽的长条里', loc='upper left')

    fig.suptitle('图 5　首次观测给出的可行集：不只是一条方位线', fontsize=13.5, color=C['ink'], y=1.0)
    print('已输出：', S.save(fig, '图05_首次观测可行集'))
