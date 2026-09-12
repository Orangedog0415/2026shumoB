"""图 10：全向源与定向源的可检测域，以及问题四"零漏测"的两条等价判据。

(a) 全向源：可检测域是以源为心、半径 r∈[1000,1500] 的完整圆盘，所以"离得够近就一定能收到"。
(b) 定向源：只在朝向半平面内辐射，可检测域是半圆盘；背向半平面里一个信号也收不到——
    于是"某点没收到信号"再也不能推出"这里没有源"，问题三的覆盖网直接搬过来会大面积漏测。
(c) 零漏测判据：只要落在 G 的 1000 m 邻域内的观测点在方位上把 G 围住，就一定有一个点位于朝向半平面内。
    两种写法等价：凸包写法 G ∈ conv(Q ∩ B(G,1000))；方位写法 这些点对 G 的最大方位间隔 < 180°。
    左半是判据成立（围住），右半是判据不成立（存在一段 >180° 的空隙，落在这段里的朝向必然漏测）。
运行：python 图10_可检测域与零漏测判据.py   输出：figures/图10_可检测域与零漏测判据.pdf / .png
"""
import math, importlib.util
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge, Polygon as MplPoly
from matplotlib import font_manager
HERE = Path(__file__).resolve().parent
try: font_manager.fontManager.addfont('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
except Exception: pass
def _m(n, f):
    s = importlib.util.spec_from_file_location(n, str(f)); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
S = _m('S', HERE/'_绘图样式.py'); C = S.C
R = 1000.

def base(ax, title):
    ax.set_aspect('equal'); ax.set_xlim(-1500, 1500); ax.set_ylim(-1400, 1500)
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values(): sp.set_visible(False)
    ax.set_title(title, pad=9); ax.set_anchor('N')

def probes(ax, pts, res):
    for p, ok in zip(pts, res):
        col = C['blue'] if ok else C['red']
        ax.plot([p[0]], [p[1]], 'o' if ok else 'x', ms=8 if ok else 9,
                mfc=C['white'] if ok else col, mec=col, mew=2.0, color=col, zorder=8)

if __name__ == '__main__':
    S.use_style()
    fig, axs = plt.subplots(2, 2, figsize=(10.6, 9.4)); axes = axs.ravel()

    # (a) 全向源
    ax = axes[0]; base(ax, '(a) 全向源：可检测域是整张圆盘')
    ax.add_patch(plt.Circle((0,0), R, facecolor=C['blue'], alpha=.13, edgecolor=C['blue'], lw=1.4, ls=(0,(5,4))))
    P = [(700, 420), (-760, 300), (-200, -820), (620, -560)]
    probes(ax, P, [True]*4)
    ax.plot([0],[0],'*',ms=15,color=C['red'],zorder=9)
    S.tag(ax, (0,0), '干扰源 $G$', color=C['red'], dy=-18)
    S.tag(ax, (0, R), '接收半径 $r\\geq1000$ m', color=C['blue'], dy=14)
    S.note(ax, '圆内任一点都能收到 ⇒ 覆盖判据只需"距离 ≤1000 m"', loc='lower left')

    # (b) 定向源
    ax = axes[1]; base(ax, '(b) 定向源：只有朝向半平面能收到')
    psi = 35.
    ax.add_patch(Wedge((0,0), R, psi-90, psi+90, facecolor=C['blue'], alpha=.13, edgecolor=C['blue'], lw=1.4))
    ax.add_patch(Wedge((0,0), R, psi+90, psi+270, facecolor=C['red'], alpha=.07, edgecolor='none'))
    ax.add_patch(Wedge((0,0), R, psi+90, psi+270, facecolor='none', edgecolor=C['red'], lw=1.2, ls=(0,(3,3))))
    ax.annotate('', xy=(620*math.cos(math.radians(psi)), 620*math.sin(math.radians(psi))), xytext=(0,0),
                arrowprops=dict(arrowstyle='-|>', color=C['ink'], lw=1.8), zorder=9)
    S.tag(ax, (330*math.cos(math.radians(psi)), 330*math.sin(math.radians(psi))),
          '定向方向 $\\psi$', color=C['ink'], dx=40, dy=18)
    probes(ax, P, [True, False, False, True])
    ax.plot([0],[0],'*',ms=15,color=C['red'],zorder=9)
    S.tag(ax, (-820, -700), '背向半平面：一个信号也收不到', color=C['red'], dx=120, dy=0)
    S.note(ax, '"没收到"不再等于"没有源" ⇒ 距离覆盖不足以保证不漏测', loc='lower left')

    # (c) 零漏测判据
    ax = axes[2]; base(ax, '(c) 判据成立：观测点在方位上围住了 $G$')
    ax.add_patch(plt.Circle((0,0), R, facecolor='none', edgecolor=C['edge'], lw=1.2, ls=(0,(5,4))))
    good = [(760, 300), (-560, 640), (-420, -760), (600, -560)]
    ax.add_patch(MplPoly(good, closed=True, facecolor=C['blue'], alpha=.14, edgecolor=C['blue'], lw=1.5, zorder=3))
    for p in good: ax.plot([0,p[0]],[0,p[1]], ls=(0,(2,3)), color=C['blue'], lw=.9, zorder=4)
    probes(ax, good, [True]*4)
    ax.plot([0],[0],'*',ms=15,color=C['red'],zorder=9)
    ga = sorted(math.degrees(math.atan2(p[1],p[0])) % 360 for p in good)
    gap = max([ga[i+1]-ga[i] for i in range(len(ga)-1)]+[ga[0]+360-ga[-1]])
    S.note(ax, '$G\\in conv(Q\\cap B(G,1000))$，最大方位间隔 %.0f° < 180°\n'
               '⇒ 不论定向方向如何，至少一个观测点位于朝向半平面内' % gap, loc='lower left')

    ax = axes[3]; base(ax, '(d) 判据不成立：存在一段 $\\geq180°$ 的方位空隙')
    ax.add_patch(plt.Circle((0,0), R, facecolor='none', edgecolor=C['edge'], lw=1.2, ls=(0,(5,4))))
    ang = [math.radians(a) for a in (-70, -20, 25)]
    bad = [(820*math.cos(a), 820*math.sin(a)) for a in ang]
    ax.add_patch(Wedge((0,0), 1180, 25, 290, facecolor=C['red'], alpha=.11, edgecolor='none', zorder=2))
    for p in bad: ax.plot([0,p[0]],[0,p[1]], ls=(0,(2,3)), color=C['blue'], lw=.9, zorder=4)
    probes(ax, bad, [True]*3)
    ax.plot([0],[0],'*',ms=15,color=C['red'],zorder=9)
    pm = math.radians((25+290)/2)
    ax.annotate('', xy=(560*math.cos(pm), 560*math.sin(pm)), xytext=(0,0),
                arrowprops=dict(arrowstyle='-|>', color=C['red'], lw=1.8), zorder=9)
    S.tag(ax, (1000*math.cos(pm), 1000*math.sin(pm)), '落在空隙里的朝向：三点全部漏测', color=C['red'], dx=30, dy=26)
    S.note(ax, '三个观测点都挤在一侧，最大方位间隔 265° $\\geq$ 180°\n'
               '⇒ 存在一整段定向方向，任何一点都收不到信号', loc='lower left')

    fig.suptitle('图 10　全向源与定向源的可检测域，以及零漏测判据', fontsize=13.5, color=C['ink'], y=1.0)
    print('已输出：', S.save(fig, '图10_可检测域与零漏测判据'))
