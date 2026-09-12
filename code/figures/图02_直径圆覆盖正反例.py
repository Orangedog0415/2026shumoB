"""图 2：以定位区域直径为直径的圆，能不能覆盖这个区域？——正例与反例。

问题一问的是"以定位区域直径为直径的圆能否覆盖此定位区域"。答案是**不一定**：
记直径端点为 U、V，直径圆即以 M=(U+V)/2 为心、D/2 为半径的圆；由于距离在凸多边形上的最大值在顶点取到，
覆盖 ⟺ 所有顶点到 M 的距离 ≤ D/2。本图给出两个由真实观测生成的算例：
(a) 覆盖成立；(b) 覆盖不成立，有顶点落在圆外（超出 43.7%）。
两个算例都用 δ=1.005° 的三次观测生成，规模也和实际定位区域相当（直径 25~29 m）。
运行：python 图02_直径圆覆盖正反例.py   输出：figures/图02_直径圆覆盖正反例.pdf / .png
"""
import math, json, importlib.util
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPoly
from matplotlib import font_manager

HERE = Path(__file__).resolve().parent
try: font_manager.fontManager.addfont('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
except Exception: pass
_s = importlib.util.spec_from_file_location('S', str(HERE/'_绘图样式.py')); S = importlib.util.module_from_spec(_s); _s.loader.exec_module(S)
_j = importlib.util.spec_from_file_location('J', str(HERE.parent/'baseline'/'方案一_最终方案验证.py')); J = importlib.util.module_from_spec(_j); _j.loader.exec_module(J)
C = S.C

# 两个算例的检测点与（用于生成观测的）真实源位置；示向度误差在 ±1° 内随机取定后写死，保证可复现。
EX = {
 'cover':   dict(G=(767.17, 765.32),
                 OBS=[((566.95, 377.34), 62.3212), ((1609.36, 1671.94), 226.5589), ((1266.68, 546.06), 156.2009)]),
 'nocover': dict(G=(-575.73, -947.42),
                 OBS=[((-1688.49, -1696.19), 33.2755), ((30.11, -1303.12), 150.0908), ((-481.55, -322.64), 260.5213)]),
}

def poly_of(obs):
    p = J.initial_poly()
    for s, deg in obs: p = J.update(p, s, math.radians(deg))
    return p

def panel(ax, key, title):
    P = poly_of(EX[key]['OBS'])
    d, (u, v) = J.diameter(P)
    M = ((u[0]+v[0])/2, (u[1]+v[1])/2)
    far = max(P, key=lambda q: math.dist(q, M)); fd = math.dist(far, M)
    ok = fd <= d/2 + 1e-9
    ax.add_patch(plt.Circle(M, d/2, facecolor=C['blue'], alpha=.10, edgecolor=C['blue'],
                            lw=1.4, ls=(0,(5,4)), zorder=3))
    ax.add_patch(MplPoly(P, closed=True, facecolor=C['orange'], alpha=.35,
                         edgecolor=C['orange'], lw=1.8, zorder=4))
    ax.plot([q[0] for q in P], [q[1] for q in P], 'o', ms=5, mfc=C['white'],
            mec=C['orange'], mew=1.4, zorder=6)
    ax.plot([u[0], v[0]], [u[1], v[1]], '-', color=C['ink'], lw=2.0, zorder=7)
    ax.plot([u[0], v[0]], [u[1], v[1]], 'o', ms=6, color=C['ink'], zorder=8)
    ax.plot([M[0]], [M[1]], '+', ms=10, mew=1.8, color=C['ink'], zorder=8)
    S.tag(ax, ((u[0]+v[0])/2, (u[1]+v[1])/2), '直径 $D$ = %.1f m' % d, color=C['ink'], dy=-15)
    if not ok:
        ax.plot([far[0]], [far[1]], 'o', ms=9, mfc='none', mec=C['red'], mew=2.2, zorder=9)
        ax.plot([M[0], far[0]], [M[1], far[1]], ls=(0,(2,2)), color=C['red'], lw=1.4, zorder=7)
        S.tag(ax, far, '越界顶点：到圆心 %.1f m = %.2f·$D/2$' % (fd, fd/(d/2)), dy=30)
    r = d*1.0
    ax.set_xlim(M[0]-r, M[0]+r); ax.set_ylim(M[1]-r, M[1]+r); ax.set_aspect('equal')
    ax.grid(True, zorder=1)
    for sp in ('top','right'): ax.spines[sp].set_visible(False)
    ax.set_title(title, pad=9); ax.set_xlabel('x / m')
    S.note(ax, '%d 个顶点　最远顶点到圆心 %.1f m，阈值 $D/2$ = %.1f m\n结论：直径圆%s覆盖定位区域'
                % (len(P), fd, d/2, '能' if ok else '不能'), loc='lower left')
    return ok

if __name__ == '__main__':
    S.use_style()
    fig, axes = plt.subplots(1, 2, figsize=(11.4, 5.6))
    panel(axes[0], 'cover',   '(a) 正例：直径圆覆盖成立')
    panel(axes[1], 'nocover', '(b) 反例：存在顶点落在直径圆外')
    axes[0].set_ylabel('y / m')
    fig.suptitle('图 2　"以直径为直径的圆"能否覆盖定位区域：判据是所有顶点到直径中点的距离 $\\leq D/2$',
                 fontsize=13, color=C['ink'], y=1.0)
    print('已输出：', S.save(fig, '图02_直径圆覆盖正反例'))
