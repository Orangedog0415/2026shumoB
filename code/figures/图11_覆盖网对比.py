"""图 11：三张覆盖网的构造与巡回对比（问题三正八边形 / 问题四方案四规则三角格 / 方案七非规则三角网）。

(a) 问题三用的是**距离覆盖**证书：任一目标点到最近覆盖点 ≤ 974.3 m < 1000 m，所以画出每个覆盖点的
    1000 m 接收圆，它们的并集盖住整个目标圆盘。
(b)(c) 问题四用的是**三角网**证书：与目标圆盘相交的三角形三边均 ≤1000 m 且凸包含圆，
    于是任一源落在某三角形内、到三顶点的距离都 ≤1000 m 且被三顶点围住，任何定向方向下都至少有一个顶点收得到。
    图里把 Delaunay 剖分画出来，并把最长的那条边标红，直观看出证书余量。
运行：python 图11_覆盖网对比.py   需要 numpy、matplotlib（Delaunay 走 _三角剖分.py，没有 scipy 时用内置实现）
输出：figures/图11_覆盖网对比.pdf 与 .png
"""
import math, importlib.util
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import font_manager

HERE = Path(__file__).resolve().parent
try: font_manager.fontManager.addfont('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
except Exception: pass
_s = importlib.util.spec_from_file_location('S', str(HERE/'_绘图样式.py')); S = importlib.util.module_from_spec(_s); _s.loader.exec_module(S)
_l = importlib.util.spec_from_file_location('L', str(HERE.parent/'experiments'/'方案四_实验台.py')); L = importlib.util.module_from_spec(_l); _l.loader.exec_module(L)
_t = importlib.util.spec_from_file_location('TRI', str(HERE/'_三角剖分.py')); TRI = importlib.util.module_from_spec(_t); _t.loader.exec_module(TRI)
C = S.C; R = 1800.
FS = 2.0                                    # 全图文字统一放大倍数（相对原始字号）

def tri_hits_disk(V):
    s = [(V[(i+1)%3][0]-V[i][0])*(-V[i][1])-(V[(i+1)%3][1]-V[i][1])*(-V[i][0]) for i in range(3)]
    if all(z>=0 for z in s) or all(z<=0 for z in s): return True
    def sd(a,b):
        dx,dy = b[0]-a[0], b[1]-a[1]
        t = max(0,min(1,-(a[0]*dx+a[1]*dy)/(dx*dx+dy*dy)))
        return math.hypot(a[0]+t*dx, a[1]+t*dy)
    return min(sd(V[i],V[(i+1)%3]) for i in range(3)) < R

def draw_net(ax, pts, mode):
    """mode='disk' 画 1000 m 接收圆；mode='tri' 画 Delaunay 剖分并标出最长边。"""
    P = np.array(pts)
    if mode == 'disk':
        for x,y in pts:
            ax.add_patch(plt.Circle((x,y), 1000., facecolor=C['blue'], alpha=.055, edgecolor='none', zorder=2))
            ax.add_patch(plt.Circle((x,y), 1000., facecolor='none', edgecolor=C['blue'],
                                    lw=.6, alpha=.30, ls=(0,(3,3)), zorder=3))
        return None
    longest = (0., None)
    for simp in TRI.simplices(P):
        V = [tuple(P[i]) for i in simp]
        if not tri_hits_disk(V): continue
        for i in range(3):
            a, b = V[i], V[(i+1)%3]
            ax.plot([a[0],b[0]], [a[1],b[1]], '-', color=C['edge'], lw=.9, zorder=2)
            d = math.dist(a,b)
            if d > longest[0]: longest = (d,(a,b))
    (a,b) = longest[1]
    ax.plot([a[0],b[0]], [a[1],b[1]], '-', color=C['red'], lw=2.4, zorder=5)
    mid = ((a[0]+b[0])/2, (a[1]+b[1])/2)
    nx, ny = -(b[1]-a[1]), (b[0]-a[0]); nl = math.hypot(nx,ny) or 1.
    S.tag(ax, mid, '最长边 %.1f m'%longest[0], dx=30*FS*nx/nl, dy=30*FS*ny/nl, fs=8.5*FS)
    return longest[0]

def worst_cover(pts, step=8.):
    """任一目标点到最近覆盖点的最大距离，并给出取到它的位置（距离覆盖证书的数值余量）。"""
    Ss=[(0.,0.)]; r=step
    while r <= R+1e-9:
        n = max(6,int(2*math.pi*r/step))
        Ss += [(r*math.cos(2*math.pi*k/n), r*math.sin(2*math.pi*k/n)) for k in range(n)]
        r += step
    A = np.array(Ss); N = np.array(pts)
    d = np.sqrt(((A[:,None,:]-N[None,:,:])**2).sum(-1)).min(1)
    i = int(d.argmax()); return float(d[i]), tuple(A[i])

if __name__ == '__main__':
    S.use_style()
    plt.rcParams.update({'xtick.labelsize': 9*FS, 'ytick.labelsize': 9*FS,
                         'axes.labelsize': 10*FS, 'axes.titlesize': 11.5*FS,
                         'legend.fontsize': 9*FS})
    NETS = [
        ('(a) 问题三\n正八边形覆盖网', L.NET3(), 'disk',
         '证书：距离覆盖\n任一点到最近覆盖点\n%.1f m < 1000 m', 'lower left'),
        ('(b) 问题四·方案四\n规则三角格 h=950 m', L.NET4_V4(), 'tri',
         '证书：三角网\n相交三角形三边 ≤1000 m', 'lower left'),
        ('(c) 问题四·方案七\n非规则三角网', L.NET4_V7(), 'tri',
         '证书：三角网（同上）\n最大方位间隔 179.86° < 180°', 'upper left'),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(19.2, 9.0))
    fig.subplots_adjust(wspace=.26, left=.075, right=.985, top=.795, bottom=.165)
    for ax, (title, net, mode, cert, nloc) in zip(axes, NETS):
        S.field_axes(ax, R)
        draw_net(ax, net, mode)
        T = L.tour_nn2opt([tuple(p) for p in net])
        ln = S.tour(ax, T, label='巡回路线')
        ax.plot([p[0] for p in net], [p[1] for p in net], 'o', ms=5.5, mfc=C['blue'],
                mec=C['white'], mew=.9, zorder=8, label='覆盖点')
        ax.set_title(title, pad=12)
        if mode == 'disk':
            wd, wp = worst_cover(net); cert = cert % wd
            ax.plot([wp[0]],[wp[1]], marker='x', ms=8, mew=2, color=C['red'], zorder=9)
            S.tag(ax, wp, '最坏覆盖点', dy=26*FS, fs=8.5*FS)
        out = sum(1 for p in net if math.hypot(*p) > R)
        head = '%d 个覆盖点（%d 点在目标圆外）\n巡回 %s m' % (len(net), out, format(round(ln), ',')) \
               if out else '%d 个覆盖点　巡回 %s m' % (len(net), format(round(ln), ','))
        S.note(ax, '%s\n%s' % (head, cert), loc=nloc, fs=9*FS)
        ax.set_xlabel('x / m')
    axes[0].set_ylabel('y / m')
    h, lb = axes[0].get_legend_handles_labels()
    fig.legend(h, lb, loc='lower center', ncol=2, bbox_to_anchor=(.5,.012),
               handletextpad=.6, columnspacing=2.2)
    fig.suptitle('图 11　目标区域（半径 1800 m）的三张覆盖网：构造、证书与巡回路线',
                 fontsize=13.5*FS, color=C['ink'], y=.975)
    p = S.save(fig, '图11_覆盖网对比')
    print('已输出：', p)
