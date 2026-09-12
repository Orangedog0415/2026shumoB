"""图 26：可能区域怎么变成"一定能清掉"的几个动作——28 m 方格与服务簇。

清除的规则是"在距源 ≤20 m 处执行清除即成功"。于是：
  · 若可能区域的外接半径 ≤19.5 m，直接到区域中心清一次就一定成功（图中绿色圆）；
  · 否则把区域沿长轴切成边长 28 m 的方格（28 < 20√2 ≈ 28.28，保证每格的外接半径 < 20 m），
    对每个与区域相交的方格取中心，逐个试清——只要源在区域里，就一定有一格命中。
  · 方格数 ≤ cover_k（标定值 6）时直接逐格清；超过就先补测把区域压小。
路线规划里把这 ≤6 个清除点整体当作一个"服务簇"，取离当前位置最近的那个作为路线节点（5.3a）。
运行：python 图26_服务簇与清除方格.py   输出：figures/图26_服务簇与清除方格.pdf / .png
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

def region(sts, errs, G):
    p = J.initial_poly()
    for s, e in zip(sts, errs):
        p = J.update(p, s, math.atan2(G[1]-s[1], G[0]-s[0]) + math.radians(e))
    return p

if __name__ == '__main__':
    S.use_style()
    G = (410., 180.)
    CASE = [([(0., 0.), (-372., -858.)], [0.9, -0.8], '(a) 两次观测：区域直径 138 m，逐格清除'),
            ([(0., 0.), (-372., -858.), (300., 780.), (-250., -120.)], [0.9, -0.8, 0.5, -0.95],
             '(b) 再补两次后：外接半径 ≤19.5 m，一次清除即可')]
    fig, axes = plt.subplots(1, 2, figsize=(12.2, 5.6))
    for ax, (sts, errs, title) in zip(axes, CASE):
        P = region(sts, errs, G)
        c = J.centroid(P); r = J.radius(P, c)
        ax.add_patch(MplPoly(P, closed=True, facecolor=C['orange'], alpha=.45, edgecolor=C['orange'], lw=1.6, zorder=5))
        if r <= 19.5:
            ax.add_patch(plt.Circle(c, 20., facecolor='#9bc3a4', alpha=.30, edgecolor='#3f8a50', lw=1.6, zorder=4))
            ax.plot([c[0]], [c[1]], 'P', ms=11, color='#3f8a50', zorder=8)
            S.tag(ax, c, '区域外接半径 %.1f m ≤ 19.5 m\n到区域中心清除一次即保证成功' % r, color='#3f8a50', dy=32)
            pts = [c]
        else:
            pts = L.cover_centers(P)
            _, ang = L.axis(P); u = (math.cos(ang), math.sin(ang)); w = (-u[1], u[0])
            for q in pts:
                sq = [(q[0]+14*(a*u[0]+b*w[0]), q[1]+14*(a*u[1]+b*w[1])) for a, b in ((-1,-1),(1,-1),(1,1),(-1,1))]
                ax.add_patch(MplPoly(sq, closed=True, facecolor='none', edgecolor='#3f8a50', lw=1.1, ls=(0,(3,2)), zorder=6))
                ax.add_patch(plt.Circle(q, 20., facecolor='#9bc3a4', alpha=.16, edgecolor='none', zorder=3))
                ax.plot([q[0]], [q[1]], 'P', ms=8, color='#3f8a50', zorder=8)
            S.tag(ax, pts[0], '28 m 方格中心 = 一次清除动作\n共 %d 个（≤ cover_k = 6 才直接逐格清）' % len(pts),
                  color='#3f8a50', dy=34)
        ax.plot([G[0]], [G[1]], '*', ms=14, color=C['red'], zorder=9)
        S.tag(ax, G, '真实源位置', color=C['red'], dy=-20)
        half = max(r*1.45, 40.)
        ax.set_xlim(c[0]-half, c[0]+half); ax.set_ylim(c[1]-half, c[1]+half); ax.set_aspect('equal')
        ax.grid(True, zorder=1); ax.set_axisbelow(True)
        for sp in ('top','right'): ax.spines[sp].set_visible(False)
        ax.set_title(title, pad=9); ax.set_xlabel('x / m')
        S.note(ax, '观测 %d 次　区域直径 %.1f m　外接半径 %.1f m' % (len(sts), J.diameter(P)[0], r), loc='lower left')
    axes[0].set_ylabel('y / m')
    fig.suptitle('图 26　从可能区域到"一定能清掉"：28 m 方格与服务簇', fontsize=13.5, color=C['ink'], y=1.0)
    print('已输出：', S.save(fig, '图26_服务簇与清除方格'))
