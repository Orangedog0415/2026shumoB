"""图 1：测向楔形与半平面交——定位区域是怎么被"夹"出来的。

每次 direction 观测给出两条半平面约束（法向量 n(θ̂∓δ)），交出一个楔形 W_i；
若干次观测的楔形求交即定位多边形 P_w = ∩ W_i。实现上用 Sutherland–Hodgman 逐条裁剪。
δ = 1.005°（示向度保留两位小数 ⇒ 取整误差 0.005° 并入 1°）实在太窄，直接画看不出楔形，
所以 (a) 把误差角放大到 6° 只讲机理，(b) 用真实 δ 画同一组观测，并把交集放大到米级尺度。
运行：python 图01_楔形与半平面交.py   输出：figures/图01_楔形与半平面交.pdf / .png
"""
import math, importlib.util
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

G = (620., 340.)                                   # 真实源位置（画图用，算法并不知道）
ST = [(0., 0.), (1500., -700.), (-300., 1400.)]    # 三个检测点
ERR = [+1.0, -0.7, +0.35]                          # 各自的示向度误差（度），|e| ≤ 1°

def bearings():
    return [math.atan2(G[1]-s[1], G[0]-s[0]) + math.radians(e) for s, e in zip(ST, ERR)]

def wedge_clip(poly, s, th, delta):
    """与 方案一_最终方案验证.py 的 wedge 同构，只是把半角 delta 放开成参数。"""
    for a, sign in ((th-delta, -1), (th+delta, +1)):
        n = (-sign*math.sin(a), sign*math.cos(a))
        poly = J.clip(poly, n, J.dot(n, s))
    return poly

def poly_of(delta, n=3, cap=False):
    """前 n 个观测的楔形交集；cap=True 时并上“到检测点 ≤1500 m”的可探测约束（真实模型）。"""
    p = J.initial_poly()
    for s, th in list(zip(ST, bearings()))[:n]:
        p = wedge_clip(p, s, th, delta)
        if cap: p = J.disk_outer(p, s, 1500)
    return p

def draw_wedge(ax, s, th, delta, length, color, alpha=.13):
    a, b = th-delta, th+delta
    pts = [s, (s[0]+length*math.cos(a), s[1]+length*math.sin(a)),
              (s[0]+length*math.cos(th), s[1]+length*math.sin(th)),
              (s[0]+length*math.cos(b), s[1]+length*math.sin(b))]
    ax.add_patch(MplPoly(pts, closed=True, facecolor=color, alpha=alpha, edgecolor='none', zorder=2))
    for e in (a, b):
        ax.plot([s[0], s[0]+length*math.cos(e)], [s[1], s[1]+length*math.sin(e)],
                '-', color=color, lw=.9, alpha=.65, zorder=3)
    ax.plot([s[0], s[0]+length*math.cos(th)], [s[1], s[1]+length*math.sin(th)],
            ls=(0,(4,3)), color=color, lw=1.1, zorder=3)

if __name__ == '__main__':
    S.use_style()
    fig, axes = plt.subplots(1, 2, figsize=(11.4, 5.4))

    # ---- (a) 机理：误差角放大到 6° ----
    ax = axes[0]; S.field_axes(ax, 1800., pad=420.)
    big = math.radians(6.)
    for s, th in zip(ST, bearings()):
        draw_wedge(ax, s, th, big, 4200., C['blue'])
    P = poly_of(big)
    ax.add_patch(MplPoly(P, closed=True, facecolor=C['orange'], alpha=.55, edgecolor=C['orange'], lw=1.6, zorder=5))
    ax.plot([p[0] for p in ST], [p[1] for p in ST], '^', ms=9, mfc=C['white'], mec=C['blue'], mew=1.8, zorder=8, label='检测点 $S_i$')
    for i, s in enumerate(ST):
        ax.annotate('$S_%d$'%(i+1), xy=s, xytext=(10,10), textcoords='offset points', fontsize=10, color=C['blue'], zorder=9)
    ax.plot([G[0]], [G[1]], '*', ms=13, color=C['red'], zorder=9, label='真实源位置 $G$')
    ax.set_title('(a) 机理：三条楔形的交集（误差角放大到 6°）', pad=9)
    ax.set_xlabel('x / m'); ax.set_ylabel('y / m')
    ax.legend(loc='lower left', handletextpad=.5)
    S.note(ax, '每次观测 = 两条半平面\n$(X-S_i)\\cdot n(\\hat\\theta_i-\\delta)\\geq 0$,  $(X-S_i)\\cdot n(\\hat\\theta_i+\\delta)\\leq 0$\n橙色区域 = 三条楔形的交 $P_w=\\bigcap W_i$', loc='lower right')

    # ---- (b) 真实 δ=1.005°，逐次观测把区域夹小 ----
    ax = axes[1]
    cols = ['#9dc2ee', '#5d9ae1', C['blue']]
    polys = [poly_of(J.DELTA, n, cap=True) for n in (1, 2, 3)]
    P3 = polys[2]
    cx, cy = J.centroid(P3)
    for n, col in zip((1, 2, 3), cols):
        ax.add_patch(MplPoly(polys[n-1], closed=True, facecolor=col, alpha=.35 if n < 3 else .75,
                             edgecolor=col, lw=1.3, zorder=2+n, label='前 %d 次观测' % n))
    d, (u, v) = J.diameter(P3)
    ax.plot([G[0]], [G[1]], '*', ms=8, color=C['red'], zorder=9)
    half = 620.
    ax.set_xlim(cx-half, cx+half); ax.set_ylim(cy-half, cy+half)
    ax.set_aspect('equal'); ax.grid(True, zorder=1)
    for sp in ('top','right'): ax.spines[sp].set_visible(False)
    ax.set_title('(b) 真实 $\\delta=1.005°$：区域随观测次数收缩', pad=9)
    ax.set_xlabel('x / m'); ax.set_ylabel('y / m')
    ax.legend(loc='upper left', handletextpad=.6)
    # 放大插图：最终多边形与它的直径
    axi = ax.inset_axes([.56, .50, .42, .40])
    axi.add_patch(MplPoly(P3, closed=True, facecolor=C['blue'], alpha=.75, edgecolor=C['blue'], lw=1.3))
    axi.plot([u[0], v[0]], [u[1], v[1]], '-', color=C['red'], lw=2.0, zorder=8)
    axi.plot([G[0]], [G[1]], '*', ms=11, color=C['red'], zorder=9)
    h2 = d*.85
    axi.set_xlim(cx-h2, cx+h2); axi.set_ylim(cy-h2, cy+h2); axi.set_aspect('equal')
    axi.set_xticks([]); axi.set_yticks([])
    for sp in axi.spines.values(): sp.set_color(C['edge'])
    axi.set_title('放大：直径 %.1f m' % d, fontsize=9, color=C['ink2'], pad=4)
    ax.indicate_inset_zoom(axi, edgecolor=C['ink2'], alpha=.5, lw=.9)
    S.note(ax, '$\\delta$ 虽小，单次观测的楔形在 800 m 外仍有约 28 m 宽\n三次观测后区域直径 %.1f m，红星为真实源位置' % d)

    fig.suptitle('图 1　测向楔形与半平面交：定位区域的构造', fontsize=13.5, color=C['ink'], y=1.0)
    print('已输出：', S.save(fig, '图01_楔形与半平面交'))
