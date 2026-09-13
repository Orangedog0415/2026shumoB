"""图 12：覆盖网的零漏测证书是怎么验的——解析边长检查 + 全域方位间隔复验。

我们对问题四覆盖网用的是三角网证书：Delaunay 剖分的凸包包住半径 1800 m 圆盘，且与圆盘相交的三角形三边 ≤1000 m。
(a) 横置在最上方：把"与圆盘相交的三角形"的边长全部画成直方图（横向条），看它离 1000 m 的约束线还有多少余量。
(b)(c)(d) 用 GT06 式(31) 的另一套写法独立复验：在极坐标网格上算每个位置"1000 m 内观测点对它的最大方位间隔"，
    以 180° 为中性色——蓝色表示被围住（任何定向方向都不漏测），红色表示存在漏测方向。
    问题三的七点网大片红色（GT06 报告的全域平均漏测概率 65.24%），GT06 的 37 点分级环网与我们的 25 点网都全域小于 180°。
方位间隔场算一次约 1 分钟，缓存在 code/experiments/results/图12_方位间隔场.npz，删掉会自动重算。
Delaunay 剖分走 _三角剖分.py：有 scipy 用 scipy，没有则用内置的暴力空外接圆检验，结果一致。
运行：python 图12_覆盖网证书验证.py   输出：figures/图12_覆盖网证书验证.pdf / .png
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
S = _m('S', HERE/'_绘图样式.py'); C = S.C
TRI = _m('TRI', HERE/'_三角剖分.py')
L = _m('L', HERE.parent/'experiments'/'方案四_实验台.py')
R = 1800.
FS = 1.5                     # 解释文字统一放大倍数
CACHE = HERE.parent/'experiments'/'results'/'图12_方位间隔场.npz'

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
    P = np.array(net); out = set()
    for simp in TRI.simplices(P):
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
    for i, rr in enumerate(RR):
        for j, a in enumerate(A):
            G = (rr*math.cos(a), rr*math.sin(a))
            b = sorted(math.atan2(p[1]-G[1], p[0]-G[0]) % (2*math.pi)
                       for p in net if math.dist(p, G) <= 1000.+1e-9)
            if len(b) < 2: Z[i, j] = 360.
            else: Z[i, j] = math.degrees(max([b[k+1]-b[k] for k in range(len(b)-1)] + [b[0]+2*math.pi-b[-1]]))
    return A, RR, Z

def fields(nets):
    """三张网的方位间隔场，带磁盘缓存。"""
    if CACHE.exists():
        d = np.load(CACHE)
        return d['A'], d['RR'], [d['Z%d' % k] for k in range(len(nets))]
    out = [gap_field(n) for n in nets]
    A, RR = out[0][0], out[0][1]
    np.savez_compressed(CACHE, A=A, RR=RR, **{'Z%d' % k: z for k, (_, _, z) in enumerate(out)})
    return A, RR, [z for _, _, z in out]

if __name__ == '__main__':
    S.use_style()
    plt.rcParams.update({'xtick.labelsize': 9*FS, 'ytick.labelsize': 9*FS, 'axes.labelsize': 10*FS})
    fig = plt.figure(figsize=(13.6, 9.9))
    gs = fig.add_gridspec(3, 3, height_ratios=[1.05, 2.35, .085],
                          hspace=.24, wspace=.10, left=.075, right=.965, top=.895, bottom=.065)

    # ---- (a) 解析边长检查：横置在最上方，条形横向 ----
    ax = fig.add_subplot(gs[0, :])
    for net, lab, col in ((L.NET4_V4(), '方案四 规则三角格（27 点）', C['orange']),
                          (L.NET4_V7(), '方案七 非规则三角网（25 点）', C['blue'])):
        e = edge_lengths(net)
        ax.hist(e, bins=np.arange(400, 1060, 25), orientation='horizontal', alpha=.7, color=col,
                edgecolor=C['white'], lw=.5, label='%s　最长 %.1f m' % (lab, e.max()))
    ax.axhline(1000, color=C['red'], lw=1.6)
    ax.set_xlim(0, ax.get_xlim()[1]*1.55)
    ax.text(ax.get_xlim()[1]*.985, 1000, '证书约束 1000 m', ha='right', va='bottom',
            fontsize=8.5*FS, color=C['red'])
    ax.set_ylabel('与圆盘相交的\n三角形边长 / m'); ax.set_xlabel('条数')
    ax.grid(True, axis='x'); ax.set_axisbelow(True)
    for sp in ('top', 'right'): ax.spines[sp].set_visible(False)
    ax.legend(loc='lower right', fontsize=8.2*FS)
    ax.set_title('(a) 解析边长检查', pad=9, fontsize=10.5*FS)

    # ---- (b)(c)(d) 全域方位间隔复验 ----
    NETS = [NET_Q3, NET_GT06, L.NET4_V7()]
    NAMES = ['(b) 问题三 七点网（7 点）', '(c) GT06 分级环网（37 点）', '(d) 方案七 三角网（25 点）']
    A, RR, ZS = fields(NETS)
    for k, (name, Z) in enumerate(zip(NAMES, ZS)):
        ax = fig.add_subplot(gs[1, k], projection='polar')
        AA, RRm = np.meshgrid(np.append(A, 2*math.pi), RR)
        Zc = np.concatenate([Z, Z[:, :1]], axis=1)
        pc = ax.pcolormesh(AA, RRm, Zc, cmap='RdBu_r', vmin=0, vmax=360, shading='nearest')
        ax.set_yticklabels([]); ax.set_xticklabels([])
        ax.grid(False); ax.set_title(name, pad=14, fontsize=10.5*FS)
        bad = float((Z >= 180).mean())
        ax.text(.5, -.07, '最大方位间隔 %.1f°　可漏测面积 %.0f%%' % (Z.max(), 100*bad),
                transform=ax.transAxes, ha='center', va='top', fontsize=8.8*FS, color=C['ink2'])
        if k == 2:
            cax = fig.add_subplot(gs[2, 1])
            cb = fig.colorbar(pc, cax=cax, orientation='horizontal', ticks=[0, 90, 180, 270, 360])
            cb.set_label('最大方位间隔 / °（180° 为分界）', fontsize=9*FS)
            cb.ax.tick_params(labelsize=9*FS)
            cb.outline.set_edgecolor(C['edge'])

    fig.suptitle('图 12　覆盖网零漏测证书的两重验证：解析边长检查与全域方位间隔复验',
                 fontsize=16.5, color=C['ink'], y=.972)
    print('已输出：', S.save(fig, '图12_覆盖网证书验证'))
