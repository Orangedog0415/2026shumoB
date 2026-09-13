"""图 3：直径圆覆盖判据的几何解释、最坏情形，以及"不覆盖"到底有多常见。

(a) Thales 等价形式：点 X 落在以 UV 为直径的圆内 ⟺ ∠UXV ≥ 90°。于是"某顶点看直径端点的张角小于 90°"
    就是它跑到圆外的充要条件——这给了判据一个不用算距离的读法。
(b) 最坏情形是正三角形：三边等长 D，直径就是边长 D，直径圆半径 D/2，而第三顶点到直径中点的距离是
    (√3/2)D ≈ 0.866D，比阈值大 73%。此时能覆盖整个区域的最小圆半径是外接圆 D/√3 ≈ 0.577D（Jung 定理在平面上的取等情形）。
(c) 随机算例统计：对 3000 组随机三次观测生成的定位多边形，统计"最远顶点距离 / (D/2)"。
    等于 1 表示直径圆恰好覆盖，大于 1 表示不覆盖。可见不覆盖并非罕见情形。
运行：python 图03_覆盖判据与最小包围圆.py   输出：figures/图03_覆盖判据与最小包围圆.pdf / .png
"""
import math, random, importlib.util
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPoly, Arc
from matplotlib import font_manager

HERE = Path(__file__).resolve().parent
try: font_manager.fontManager.addfont('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
except Exception: pass
_s = importlib.util.spec_from_file_location('S', str(HERE/'_绘图样式.py')); S = importlib.util.module_from_spec(_s); _s.loader.exec_module(S)
_j = importlib.util.spec_from_file_location('J', str(HERE.parent/'baseline'/'方案一_最终方案验证.py')); J = importlib.util.module_from_spec(_j); _j.loader.exec_module(J)
C = S.C

def ratios(n=3000, seed=11):
    """随机三次观测 → 定位多边形 → 最远顶点距离 / (D/2)。"""
    rng = random.Random(seed); out = []
    while len(out) < n:
        G = (rng.uniform(-1000,1000), rng.uniform(-1000,1000))
        ST = [(rng.uniform(-1700,1700), rng.uniform(-1700,1700)) for _ in range(3)]
        if any(not (300 < math.dist(G,s) < 1400) for s in ST): continue
        p = J.initial_poly()
        for s in ST:
            p = J.update(p, s, math.atan2(G[1]-s[1], G[0]-s[0]) + math.radians(rng.uniform(-1,1)))
        if len(p) < 3: continue
        d, (u,v) = J.diameter(p)
        if d < 1e-6: continue
        M = ((u[0]+v[0])/2, (u[1]+v[1])/2)
        out.append(max(math.dist(q,M) for q in p)/(d/2))
    return np.array(out)

if __name__ == '__main__':
    S.use_style()
    FS = 2.5                                    # 全图文字统一放大倍数（相对原始字号）
    plt.rcParams.update({'xtick.labelsize': 9*FS, 'ytick.labelsize': 9*FS,
                         'axes.labelsize': 10*FS, 'axes.titlesize': 11.5*FS})
    fig, axes = plt.subplots(1, 3, figsize=(18.0, 9.6))
    fig.subplots_adjust(wspace=.24, left=.075, right=.975, top=.735, bottom=.135)

    # ---- (a) Thales 等价形式 ----
    ax = axes[0]
    U, V = (-1., 0.), (1., 0.)
    ax.add_patch(plt.Circle((0,0), 1., facecolor=C['blue'], alpha=.10, edgecolor=C['blue'], lw=1.4, ls=(0,(5,4))))
    ax.plot([U[0],V[0]],[U[1],V[1]], '-', color=C['ink'], lw=2.0, zorder=6)
    ax.plot([U[0],V[0]],[U[1],V[1]], 'o', ms=6, color=C['ink'], zorder=7)
    for X, col, lab, ok in (((.15,.72), C['blue'], '$X_1$：圆内', True), ((.55,1.32), C['red'], '$X_2$：圆外', False)):
        ang = math.degrees(math.acos(max(-1,min(1,
              ((U[0]-X[0])*(V[0]-X[0])+(U[1]-X[1])*(V[1]-X[1])) /
              (math.dist(U,X)*math.dist(V,X))))))
        for W in (U, V):
            ax.plot([X[0],W[0]],[X[1],W[1]], ls=(0,(3,3)), color=col, lw=1.2, zorder=5)
        ax.plot([X[0]],[X[1]], 'o', ms=7, mfc=C['white'], mec=col, mew=1.8, zorder=8)
        ax.add_patch(Arc(X, .42, .42, angle=0, theta1=math.degrees(math.atan2(U[1]-X[1],U[0]-X[0])),
                         theta2=math.degrees(math.atan2(V[1]-X[1],V[0]-X[0])), color=col, lw=1.3, zorder=6))
        S.tag(ax, X, '%s\n$\\angle UXV$ = %.0f°' % (lab, ang), color=col, dy=19*FS if ok else 23*FS, fs=8.5*FS)
    ax.text(0,-.13,'$M$', ha='center', va='top', color=C['ink2'], fontsize=10*FS)
    ax.plot([0],[0],'+',ms=10,mew=1.8,color=C['ink'],zorder=7)
    ax.text(U[0],-.13,'$U$',ha='center',va='top',color=C['ink2'],fontsize=10*FS)
    ax.text(V[0],-.13,'$V$',ha='center',va='top',color=C['ink2'],fontsize=10*FS)
    ax.set_aspect('equal', adjustable='datalim')
    ax.set_xlim(-1.32, 1.32); ax.set_ylim(-1.12, 1.85)
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ('top','right','bottom','left'): ax.spines[sp].set_visible(False)
    ax.set_title('(a) Thales 判据\n$X$ 在直径圆内 $\\Leftrightarrow$\n$\\angle UXV\\geq 90°$', pad=14)

    # ---- (b) 最坏情形：正三角形 ----
    ax = axes[1]
    T = [(-.5, 0.), (.5, 0.), (0., math.sqrt(3)/2)]
    ax.add_patch(plt.Circle((0,0), .5, facecolor=C['blue'], alpha=.10, edgecolor=C['blue'], lw=1.4, ls=(0,(5,4))))
    ax.add_patch(plt.Circle((0, math.sqrt(3)/6), 1/math.sqrt(3), facecolor='none',
                            edgecolor=C['orange'], lw=1.6, ls=(0,(1,2))))
    ax.add_patch(MplPoly(T, closed=True, facecolor=C['orange'], alpha=.30, edgecolor=C['orange'], lw=1.8, zorder=4))
    ax.plot([-.5,.5],[0,0], '-', color=C['ink'], lw=2.0, zorder=6)
    ax.plot([0,0],[0,math.sqrt(3)/2], ls=(0,(2,2)), color=C['red'], lw=1.4, zorder=6)
    ax.plot([T[2][0]],[T[2][1]], 'o', ms=9, mfc='none', mec=C['red'], mew=2.2, zorder=8)
    S.tag(ax, T[2], '到中点 $0.866D$\n阈值 $D/2$\n超出 73%', dy=21*FS, fs=8.5*FS)
    S.tag(ax, (-.02, -.46), '最小包围圆\n半径 $D/\\sqrt{3}\\approx0.577D$', color=C['orange'], dx=0, dy=0, fs=8.5*FS)
    ax.set_aspect('equal', adjustable='datalim')
    ax.set_xlim(-.86, .86); ax.set_ylim(-.62, 1.26)
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ('top','right','bottom','left'): ax.spines[sp].set_visible(False)
    ax.set_title('(b) 最坏情形\n边长为 $D$ 的正三角形', pad=14)

    # ---- (c) 随机算例统计 ----
    ax = axes[2]
    r = ratios()
    bad = float((r > 1+1e-9).mean())
    ax.hist(r, bins=np.linspace(1, max(1.78, r.max()*1.02), 52), color=C['blue'],
            alpha=.85, edgecolor=C['white'], lw=.5, log=True)
    ax.axvline(math.sqrt(3), color=C['orange'], lw=1.4, ls=(0,(4,3)))
    ax.set_ylim(.7, ax.get_ylim()[1]*3)
    S.tag(ax, (math.sqrt(3), 4.0), '正三角形上界\n$\\sqrt{3}\\approx1.732$', color=C['orange'], dx=-31*FS, dy=0, fs=8.5*FS)
    ax.set_xlabel('最远顶点距离 / $(D/2)$'); ax.set_ylabel('算例数（对数刻度）')
    ax.grid(True, axis='y'); ax.set_axisbelow(True)
    for sp in ('top','right'): ax.spines[sp].set_visible(False)
    ax.set_title('(c) 3000 组随机算例\n不覆盖占 %.1f%%' % (100*bad), pad=14)
    S.note(ax, '取值恒 $\\geq 1$，$=1$ 即覆盖\n实测最大 %.2f $<\\sqrt{3}$\n纵轴为对数刻度' % r.max(), loc='upper right', fs=9*FS)

    fig.suptitle('图 3　直径圆覆盖判据的几何解释、最坏情形与经验分布', fontsize=13.5*FS, color=C['ink'], y=.988)
    print('已输出：', S.save(fig, '图03_覆盖判据与最小包围圆'), '　不覆盖比例 %.3f' % bad)
