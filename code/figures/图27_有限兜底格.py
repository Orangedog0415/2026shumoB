"""图 27：75×3 有限兜底——当补测都失败时，最坏情况下的 225 次试清。

保证链的最后一环：若局部补测都没能把可能区域压到可以逐格清除，就沿"首条方位线"铺一张 75×3 的 20 m 方格网
（沿方位方向 75 格 × 垂直方向 3 格，覆盖 0~1500 m 距离、±30 m 横向偏差），逐格试清。
由于源一定落在首条楔形内、且距首个检测点不超过 1500 m，这张网必然覆盖它；每格边长 20 m，
格心到格内任一点不超过 14.1 m < 20 m，所以命中即成功。最坏 225 次试清，每次失败 3 s，
构成了"一定能清掉"的最后上界——实测这一分支几乎不触发（方案四时间线里只占 196 s / 8623 s）。
运行：python 图27_有限兜底格.py   输出：figures/图27_有限兜底格.pdf / .png
"""
import math, importlib.util
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPoly
from matplotlib import font_manager
HERE = Path(__file__).resolve().parent
try: font_manager.fontManager.addfont('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
except Exception: pass
def _m(n, f):
    s = importlib.util.spec_from_file_location(n, str(f)); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
S = _m('S', HERE/'_绘图样式.py'); C = S.C
L = _m('L', HERE.parent/'experiments'/'方案四_实验台.py'); J = L.J

if __name__ == '__main__':
    S.use_style()
    anchor = (0., 0.); theta = math.radians(22.)
    cells = J.fallback_cells(None, anchor, theta)
    fig, axes = plt.subplots(1, 2, figsize=(12.6, 5.0), gridspec_kw=dict(width_ratios=[1.5, 1], wspace=.24))

    ax = axes[0]
    for c, cell in cells:
        ax.add_patch(MplPoly(cell, closed=True, facecolor='#e9f3ea', edgecolor='#9bc3a4', lw=.35, zorder=3))
    u = (math.cos(theta), math.sin(theta))
    ax.plot([0, 1560*u[0]], [0, 1560*u[1]], ls=(0,(5,4)), color=C['orange'], lw=1.4, zorder=5)
    ax.plot([anchor[0]], [anchor[1]], '^', ms=10, mfc=C['white'], mec=C['blue'], mew=1.9, zorder=8)
    S.tag(ax, anchor, '首个检测点', color=C['blue'], dy=-18)
    S.tag(ax, (1000*u[0], 1000*u[1]), '首条示向度方向', color=C['orange'], dx=10, dy=24)
    ax.set_aspect('equal'); ax.set_xlim(-120, 1560); ax.set_ylim(-320, 780)
    ax.grid(True, zorder=1); ax.set_axisbelow(True)
    for sp in ('top','right'): ax.spines[sp].set_visible(False)
    ax.set_xlabel('x / m'); ax.set_ylabel('y / m')
    ax.set_title('(a) 75×3 共 %d 格，覆盖 0~1500 m' % len(cells), pad=9)

    ax = axes[1]
    for c, cell in cells[:12]:
        ax.add_patch(MplPoly(cell, closed=True, facecolor='#e9f3ea', edgecolor='#3f8a50', lw=1.0, zorder=3))
        ax.plot([c[0]], [c[1]], 'P', ms=7, color='#3f8a50', zorder=6)
    c0 = cells[4][0]
    ax.add_patch(plt.Circle(c0, 20., facecolor='#9bc3a4', alpha=.25, edgecolor='#3f8a50', lw=1.4, ls=(0,(4,3)), zorder=4))
    S.tag(ax, c0, '清除半径 20 m\n格心到格内最远点 14.1 m', color='#3f8a50', dy=34)
    ax.set_aspect('equal')
    ax.set_xlim(c0[0]-58, c0[0]+58); ax.set_ylim(c0[1]-58, c0[1]+58)
    ax.grid(True, zorder=1); ax.set_axisbelow(True)
    for sp in ('top','right'): ax.spines[sp].set_visible(False)
    ax.set_xlabel('x / m')
    ax.set_title('(b) 放大：20 m 方格与 20 m 清除半径', pad=9)
    S.note(ax, '最坏 %d 次试清，失败 3 s / 次\n上界 %.0f s，实测几乎不触发' % (len(cells), 3*len(cells)), loc='lower left')

    fig.suptitle('图 27　保证链的最后一环：75×3 有限兜底格', fontsize=13.5, color=C['ink'], y=1.0)
    print('已输出：', S.save(fig, '图27_有限兜底格'))
