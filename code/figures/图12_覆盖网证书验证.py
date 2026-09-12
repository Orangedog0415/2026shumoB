"""图 12：覆盖网的零漏测证书是怎么验的——解析边长检查 + 全域方位间隔复验。

我们对问题四覆盖网用的是三角网证书：Delaunay 剖分的凸包包住半径 1800 m 圆盘，且与圆盘相交的三角形三边 ≤1000 m。
(a) 把"与圆盘相交的三角形"的边长全部画成直方图，看它离 1000 m 的约束线还有多少余量。
(b)(c)(d) 用 GT06 式(31) 的另一套写法独立复验：在极坐标网格上算每个位置"1000 m 内观测点对它的最大方位间隔"，
    以 180° 为中性色——蓝色表示被围住（任何定向方向都不漏测），红色表示存在漏测方向。
    问题三的七点网大片红色（GT06 报告的全域平均漏测概率 65.24%），GT06 的 37 点分级环网与我们的 25 点网都全域小于 180°。
运行：python 图12_覆盖网证书验证.py（约 1 分钟）  输出：figures/图12_覆盖网证书验证.pdf / .png
"""
import math, importlib.util
from pathlib import Path
import numpy as np
from scipy.spatial import Delaunay
import matplotlib.pyplot as plt
from matplotlib import font_manager
HERE = Path(__file__).resolve().parent
try: font_manager.fontManager.addfont('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
except Exception: pass
def _m(n, f):
    s = importlib.util.spec_from_file_location(n, str(f)); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
S = _m('S', HERE/'_绘图样式.py'); C = S.C
L = _m('L', HERE.parent/'experiments'/'方案四_实验台.py')
R = 1800.

def ring(rho, n, ph=0.): return [(rho*math.cos(2*math.pi*k/n+ph), rho*math.sin(2*math.pi*k/n+ph)) for k in range(n)]
NET_GT06 = [(0.,0.)] + ring(1000.,6,math.pi/6) + ring(1300.,12,math.pi/12) + ring(1900.,18,math.pi/18)
NET_Q3   = [(0.,0.)] + ring(1122.96,6)

def tri_hits_disk(V):
    s = [(V[(i+1)%3][0]-V[i][0])*(-V[i][1])-(V[(i+1)%3][1]-V[i][1])*(-V[i][0]) for i in range(3)]
    if all(z>=0 for z in s) or all(z<=0 for z in s): return True
    def sd(a,b):
        dx,dy=b[0]-a[0],b[1]-a[1]
        t=max(0,min(1,-(a[0]*dx+a[1]*dy)/(dx*dx+dy*dy))); return math.hypot(a[0]+t*dx,a[1]+t*dy)
    return min(sd(V[i],V[(i+1)%3]) for i in range(3)) < R

def edge_lengths(net):
    P = np.array(net); tri = Delaunay(P); out = set()
    for simp in tri.simplices:
        V = [tuple(P[i]) for i in simp]
        if not tri_hits_disk(V): continue
        for i in range(3):
            a, b = sorted((simp[i], simp[(i+1)%3]))
            out.add((a, b))
    return np.array([math.dist(tuple(P[a]), tuple(P[b])) for a, b in out])

def gap_field(net, nang=180, nrad=46):
    A = np.linspace(0, 2*math.pi, nang, endpoint=False)
    RR = np.linspace(0, R, nrad)
    Z = np.zeros((nrad, nang))
    N = np.array(net)
    for i, rr in enumerate(RR):
        for j, a in enumerate(A):
            G = (rr*math.cos(a), rr*math.sin(a))
            b = sorted(math.atan2(p[1]-G[1], p[0]-G[0]) % (2*math.pi)
                       for p in net if math.dist(p, G) <= 1000.+1e-9)
            if len(b) < 2: Z[i, j] = 360.
            else: Z[i, j] = math.degrees(max([b[k+1]-b[k] for k in range(len(b)-1)] + [b[0]+2*math.pi-b[-1]]))
    return A, RR, Z

if __name__ == '__main__':
    S.use_style()
    fig = plt.figure(figsize=(13.6, 5.4))
    gs = fig.add_gridspec(1, 5, width_ratios=[1.25, 1, 1, 1, .06], wspace=.34)

    ax = fig.add_subplot(gs[0, 0])
    for net, lab, col in ((L.NET4_V4(), '方案四 规则三角格（27 点）', C['orange']),
                          (L.NET4_V7(), '方案七 非规则三角网（25 点）', C['blue'])):
        e = edge_lengths(net)
        ax.hist(e, bins=np.arange(400, 1060, 25), alpha=.7, color=col, edgecolor=C['white'], lw=.5,
                label='%s　最长 %.1f m' % (lab, e.max()))
    ax.axvline(1000, color=C['red'], lw=1.6)
    ax.set_ylim(0, ax.get_ylim()[1]*1.45)
    S.tag(ax, (1000, ax.get_ylim()[1]*.62), '证书约束 1000 m', dx=-52, dy=0)
    ax.set_xlabel('与圆盘相交的三角形的边长 / m'); ax.set_ylabel('条数')
    ax.grid(True, axis='y'); ax.set_axisbelow(True)
    for sp in ('top','right'): ax.spines[sp].set_visible(False)
    ax.legend(loc='upper left', fontsize=8.2)
    ax.set_title('(a) 解析边长检查', pad=9)

    for k, (net, name) in enumerate(((NET_Q3, '(b) 问题三 七点网（7 点）'),
                                     (NET_GT06, '(c) GT06 分级环网（37 点）'),
                                     (L.NET4_V7(), '(d) 方案七 三角网（25 点）'))):
        ax = fig.add_subplot(gs[0, k+1], projection='polar')
        A, RR, Z = gap_field(net)
        AA, RRm = np.meshgrid(np.append(A, 2*math.pi), RR)
        Zc = np.concatenate([Z, Z[:, :1]], axis=1)
        pc = ax.pcolormesh(AA, RRm, Zc, cmap='RdBu_r', vmin=0, vmax=360, shading='nearest')
        ax.set_yticklabels([]); ax.set_xticklabels([])
        ax.grid(False); ax.set_title(name, pad=12, fontsize=10.5)
        bad = float((Z >= 180).mean())
        ax.text(.5, -.10, '最大方位间隔 %.1f°　可漏测面积 %.0f%%' % (Z.max(), 100*bad),
                transform=ax.transAxes, ha='center', va='top', fontsize=8.8, color=C['ink2'])
        if k == 2:
            cax = fig.add_subplot(gs[0, 4])
            cb = fig.colorbar(pc, cax=cax, ticks=[0, 90, 180, 270, 360])
            cb.set_label('最大方位间隔 / °（180° 为分界）', fontsize=9)
            cb.outline.set_edgecolor(C['edge'])

    fig.suptitle('图 12　覆盖网零漏测证书的两重验证：解析边长检查与全域方位间隔复验',
                 fontsize=13.5, color=C['ink'], y=1.02)
    print('已输出：', S.save(fig, '图12_覆盖网证书验证'))
