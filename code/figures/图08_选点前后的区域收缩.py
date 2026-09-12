"""图 8：第二次观测把定位区域收缩成什么样——最坏后验区域及其直径。

给定候选点 S，第二次示向度可能是 θ̂₂ = atan2(G-S) + e（(G,r)∈Ω₁，|e| ≤ δ），后验外包络 P₂ = P ∩ W(S, θ̂₂)。
设计口径下的 Ĵ(S) 就是对有限样本取到的最大后验直径。本图画的是差分进化解 (835.4, -547.8) 处
取到 Ĵ 的那一组 (G, e)：
(a) 全局看两条方位线怎么交会；(b) 放大看后验区域本身——它仍然是一条 112 m 长的细片，
    这正是"两次观测就能定位，但还不足以直接清除（需要 ≤19.5 m）"的量化依据。
运行：python 图08_选点前后的区域收缩.py   输出：figures/图08_选点前后的区域收缩.pdf / .png
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
S2 = (835.4, -547.8)

if __name__ == '__main__':
    S.use_style()
    d_worst, g_worst, e_worst, P2 = Q.worst_post(S2)
    th2 = math.atan2(g_worst[1]-S2[1], g_worst[0]-S2[0]) + e_worst
    dd, (u, v) = J.diameter(P2)
    fig, axes = plt.subplots(1, 2, figsize=(12.2, 5.4))

    ax = axes[0]; S.field_axes(ax, 1800., pad=200.)
    ax.add_patch(MplPoly(Q.P, closed=True, facecolor=C['orange'], alpha=.8, edgecolor=C['orange'], lw=1.3, zorder=5))
    L = 2600.
    for sgn, sty in ((-1, (0,(4,3))), (0, '-'), (1, (0,(4,3)))):
        a = th2 + sgn*J.DELTA
        ax.plot([S2[0], S2[0]+L*math.cos(a)], [S2[1], S2[1]+L*math.sin(a)],
                ls=sty, color=C['blue'], lw=1.6 if sgn == 0 else .9, zorder=6)
    for pt, mk, col, lab in ((Q.S1, '^', C['blue'], '$S_1$'), (S2, 'v', C['red'], '$S_2$')):
        ax.plot([pt[0]], [pt[1]], mk, ms=10, mfc=C['white'], mec=col, mew=1.9, zorder=9)
        S.tag(ax, pt, lab, color=col, dy=-18)
    ax.plot([g_worst[0]], [g_worst[1]], '*', ms=12, color=C['red'], zorder=9)
    ax.set_title('(a) 两条方位线的交会', pad=9); ax.set_xlabel('x / m'); ax.set_ylabel('y / m')
    S.note(ax, '橙色：首次观测的外包络 $P$\n蓝色：第二次观测的楔形 $W(S_2,\\hat\\theta_2)$\n'
               '红星：取到最坏后验直径的那个源样本', loc='lower left')

    ax = axes[1]
    cx, cy = J.centroid(P2); half = max(dd*0.9, 80.)
    ax.add_patch(MplPoly(Q.P, closed=True, facecolor=C['orange'], alpha=.30, edgecolor=C['orange'], lw=1.2, zorder=4))
    ax.add_patch(MplPoly(P2, closed=True, facecolor=C['blue'], alpha=.65, edgecolor=C['blue'], lw=1.6, zorder=6))
    ax.plot([u[0], v[0]], [u[1], v[1]], '-', color=C['ink'], lw=2.0, zorder=8)
    S.tag(ax, ((u[0]+v[0])/2, (u[1]+v[1])/2), '后验直径 %.1f m' % dd, color=C['ink'], dy=-16)
    ax.add_patch(plt.Circle((cx, cy), 19.5, facecolor='none', edgecolor=C['red'], lw=1.6, ls=(0,(3,3)), zorder=7))
    S.tag(ax, (cx-19.5, cy), '保证清除半径 19.5 m', color=C['red'], dx=-66, dy=0)
    ax.set_xlim(cx-half, cx+half); ax.set_ylim(cy-half, cy+half); ax.set_aspect('equal')
    ax.grid(True, zorder=1); ax.set_axisbelow(True)
    for sp in ('top','right'): ax.spines[sp].set_visible(False)
    ax.set_title('(b) 放大：最坏后验区域 $P_2$', pad=9); ax.set_xlabel('x / m')
    S.note(ax, '$\\hat J(S_2)$ = %.1f m，评分 $F(S_2)$ = %.2f m\n后验区域仍远大于 19.5 m，'
               '所以问题三、四里还要靠顺带补测继续收缩' % (d_worst, Q.score(S2)), loc='lower left')

    fig.suptitle('图 8　第二次观测后的区域收缩：从 1500 m 长条到 %.0f m 细片' % dd, fontsize=13.5, color=C['ink'], y=1.0)
    print('已输出：', S.save(fig, '图08_选点前后的区域收缩'), 'Ĵ=%.2f 直径=%.2f' % (d_worst, dd))
