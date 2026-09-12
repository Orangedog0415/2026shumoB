"""图 7：第二检测点的评分场 F(S)，以及网格解与差分进化解的对比。

评分沿用固定的离散设计口径：
    F(S) = Ĵ(S) + 0.05·|S-S₁|/5，
其中 Ĵ(S) 是有限样本下的最坏后验直径（源沿 P 边界每 100 m 取样，示向度误差取 -δ / 0 / +δ），
后一项把移动时间折算进来（0.05 m/s 是固定的设计权重，不代表物理定律）。
图中底色是 20 m 网格上的 F(S)，只画安全候选域内的部分；两个标记分别是
题目口径 50 m 网格的最优解 (850, -500)（F=124.85）与差分进化在连续域上的解 (835.4, -547.8)（F=122.35）。
最优点落在安全候选域边界上（最远顶点 999.0 m），说明可探测约束在最优点处收紧；网格解与连续解只差 2.0%。
运行：python 图07_第二检测点评分热力图.py（约 1 分钟）  输出：figures/图07_第二检测点评分热力图.pdf / .png
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
S = _m('S', HERE/'_绘图样式.py'); Q = _m('Q', HERE/'_问题二数据.py'); J = Q.J; C = S.C
GRID_BEST = (850., -500.); DE_BEST = (835.4, -547.8)

if __name__ == '__main__':
    S.use_style()
    X, Y, F = Q.field(step=20., xs=(400., 1100.), ys=(-800., 800.))
    fig, axes = plt.subplots(1, 2, figsize=(13.4, 5.6), gridspec_kw=dict(width_ratios=[1.2, 1], wspace=.34))

    ax = axes[0]
    pc = ax.pcolormesh(X, Y, F, cmap='Blues', shading='nearest', vmin=120, vmax=220)
    cs = ax.contour(X, Y, F, levels=[130, 140, 160, 200, 300], colors=[C['ink2']], linewidths=.7, alpha=.65)
    ax.clabel(cs, fmt='%.0f', fontsize=7.5)
    cb = fig.colorbar(pc, ax=ax, pad=.03, fraction=.046, extend='max')
    cb.set_label('评分 $F(S)$ / m（越小越好，深色更差）', fontsize=9.5)
    cb.outline.set_edgecolor(C['edge'])
    for pt, lab, mk, col in ((GRID_BEST, '50 m 网格最优 (850, -500)\n$F$ = 124.85 m', 'o', C['orange']),
                             (DE_BEST,  '差分进化解 (835.4, -547.8)\n$F$ = 122.35 m', 'D', C['red'])):
        ax.plot([pt[0]], [pt[1]], mk, ms=9, mfc='none', mec=col, mew=2.2, zorder=8)
    S.tag(ax, GRID_BEST, '50 m 网格最优 (850, -500)　$F$ = 124.85 m', color=C['orange'], dy=26)
    S.tag(ax, DE_BEST,  '差分进化解 (835.4, -547.8)　$F$ = 122.35 m', color=C['red'], dy=-26)
    ax.plot([p[0] for p in Q.P], [p[1] for p in Q.P], '-', color=C['ink2'], lw=1.0, alpha=.5, zorder=5)
    ax.set_aspect('equal'); ax.grid(False)
    ax.set_xlabel('x / m'); ax.set_ylabel('y / m')
    ax.set_title('(a) 安全候选域内的评分场 $F(S)$（20 m 网格）', pad=9)

    # (b) 过最优点的两条剖线，说明目标函数有多平
    ax = axes[1]
    xs = np.arange(DE_BEST[0]-220, DE_BEST[0]+221, 5.)
    ys = np.arange(DE_BEST[1]-220, DE_BEST[1]+221, 5.)
    fx = [Q.score((x, DE_BEST[1])) if Q.feasible((x, DE_BEST[1])) else np.nan for x in xs]
    fy = [Q.score((DE_BEST[0], y)) if Q.feasible((DE_BEST[0], y)) else np.nan for y in ys]
    ax.plot(xs-DE_BEST[0], fx, '-', color=C['blue'], lw=2.0, label='沿 $x$ 方向')
    ax.plot(ys-DE_BEST[1], fy, '-', color=C['orange'], lw=2.0, label='沿 $y$ 方向')
    ax.axhline(122.35, color=C['red'], lw=1.2, ls=(0,(4,3)))
    ax.axhline(122.35*1.02, color=C['ink2'], lw=.9, ls=(0,(2,3)))
    S.tag(ax, (0, 122.35), '最优 122.35 m', color=C['red'], dy=-16)
    S.tag(ax, (150, 122.35*1.02), '最优值 +2%', color=C['ink2'], dy=13)
    ax.plot([GRID_BEST[0]-DE_BEST[0]], [124.85], 'o', ms=8, mfc='none', mec=C['orange'], mew=2.0, zorder=8)
    S.tag(ax, (GRID_BEST[0]-DE_BEST[0], 124.85), '50 m 网格最优', color=C['orange'], dy=17)
    ax.set_xlabel('相对差分进化解的偏移 / m'); ax.set_ylabel('评分 $F(S)$ / m')
    ax.set_ylim(120, 150); ax.grid(True); ax.set_axisbelow(True)
    for sp in ('top','right'): ax.spines[sp].set_visible(False)
    ax.legend(loc='upper center')
    ax.set_title('(b) 过最优点的剖线：偏离最优点的代价', pad=9)
    S.note(ax, '最优点落在安全候选域的边界上（最远顶点 999.0 m），\n所以沿 $x$ 正向没有可行点——可探测约束在最优点处收紧。\n偏离 50 m 评分上升 3%~9%，网格解与连续解只差 2.0%。', loc='lower right')

    fig.suptitle('图 7　第二检测点的评分场与选点结果', fontsize=13.5, color=C['ink'], y=1.0)
    print('已输出：', S.save(fig, '图07_第二检测点评分热力图'))
