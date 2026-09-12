"""图 25：由已检出方位反推朝向可行集——GT06 背向不可测定理的闭式写法，以及它为什么没带来增益。

设已检出点相对源中心的方位为 β₁…β_k，源朝向 ψ 必须满足 |wrap(βᵢ−ψ)| ≤ 90°（否则那次检测不会成功），
于是可行朝向集是 βᵢ 的最小包围弧 [lo,hi]（张角 s）向两侧各扩 90°−s/2，宽度恰为 180°−s。
若从方位 φ 去补测，能检测到当且仅当 ψ 落在 [φ−90°, φ+90°]，于是"保证可检测"的程度
    frac(φ) = 1                                   φ ∈ [lo,hi]
            = 1 − d(φ,[lo,hi]) / (180°−s)         φ 在外侧，线性衰减到 0
混合场景里源以 0.35 的先验为全向，故 p_det(φ) = 0.35 + 0.65·frac(φ)。
(a) 两次检出时的几何；(b) frac(φ) 随偏角的衰减曲线；(c) 把 p_det 当门槛用在"顺路复测"上的实测代价——
门槛越严越慢，因为顺路复测的边际成本只有 5 s 检测 + 1 s 切换，没有额外移动，期望收益恒为正。
运行：python 图25_可检测锥的闭式.py   输出：figures/图25_可检测锥的闭式.pdf / .png
"""
import math, importlib.util
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge
from matplotlib import font_manager
HERE = Path(__file__).resolve().parent
try: font_manager.fontManager.addfont('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
except Exception: pass
def _m(n, f):
    s = importlib.util.spec_from_file_location(n, str(f)); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
S = _m('S', HERE/'_绘图样式.py'); C = S.C

if __name__ == '__main__':
    S.use_style()
    fig, axes = plt.subplots(1, 3, figsize=(13.6, 4.9), gridspec_kw=dict(wspace=.30))
    b1, b2 = 30., 95.; s = b2-b1; lo, hi = b1, b2

    ax = axes[0]
    ax.set_aspect('equal'); ax.set_anchor('N'); ax.set_xlim(-1.5, 1.5); ax.set_ylim(-1.5, 1.5)
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values(): sp.set_visible(False)
    ax.add_patch(Wedge((0,0), 1.22, hi-90, lo+90, facecolor=C['blue'], alpha=.16, edgecolor=C['blue'], lw=1.2))
    ax.add_patch(Wedge((0,0), 1.05, lo, hi, facecolor=C['orange'], alpha=.35, edgecolor=C['orange'], lw=1.2))
    for b, lab in ((b1, r'$\beta_1$'), (b2, r'$\beta_2$')):
        a = math.radians(b)
        ax.annotate('', xy=(1.28*math.cos(a), 1.28*math.sin(a)), xytext=(0,0),
                    arrowprops=dict(arrowstyle='-|>', color=C['orange'], lw=1.8))
        ax.text(1.42*math.cos(a), 1.42*math.sin(a), lab, ha='center', va='center', fontsize=11, color=C['orange'])
    ax.plot([0],[0],'*',ms=15,color=C['red'],zorder=9)
    S.tag(ax, (0,0), '源中心', color=C['red'], dy=-16)
    S.tag(ax, (.85*math.cos(math.radians((lo+hi)/2)), .85*math.sin(math.radians((lo+hi)/2))),
          '已检出方位\n张角 $s$ = %.0f°' % s, color=C['orange'], dx=52, dy=16)
    S.tag(ax, (1.0*math.cos(math.radians((hi-90+lo+90)/2)), 1.0*math.sin(math.radians((hi-90+lo+90)/2))),
          '可行朝向集\n宽度 $180°-s$ = %.0f°' % (180-s), color=C['blue'], dx=-30, dy=-40)
    ax.set_title('(a) 两次检出下的可行朝向集', pad=9)

    ax = axes[1]
    phi = np.linspace(lo-(180-s)-20, hi+(180-s)+20, 1200)
    def frac(p):
        if lo <= p <= hi: return 1.
        d = min(abs(p-lo), abs(p-hi))
        return max(0., 1.-d/(180-s))
    f = np.array([frac(p) for p in phi])
    ax.plot(phi, f, '-', color=C['blue'], lw=2.2, label=r'$frac(\varphi)$')
    ax.plot(phi, .35+.65*f, '-', color=C['orange'], lw=2.2, label=r'$p_{det}(\varphi)=0.35+0.65\,frac$')
    ax.axvspan(lo, hi, color=C['orange'], alpha=.12)
    ax.set_xlabel(r'补测方位 $\varphi$ / °'); ax.set_ylabel('可检测程度')
    ax.set_ylim(0, 1.08); ax.grid(True); ax.set_axisbelow(True)
    for sp in ('top','right'): ax.spines[sp].set_visible(False)
    ax.legend(loc='lower center', fontsize=8.6)
    ax.set_title('(b) 衰减是线性的，且有 0.35 的先验托底', pad=9)

    ax = axes[2]
    names = ['方案六\n无门槛', r'$\tau$=0.5', r'$\tau$=0.7', r'$\tau$=0.9']
    train = [553.3, 558.4, 574.4, 849.3]
    x = np.arange(4)
    ax.bar(x, train, width=.56, color=[C['blue']] + [C['orange'], C['orange'], C['red']], alpha=.9)
    for i, v in enumerate(train):
        ax.text(i, v+14, '%.0f' % v, ha='center', fontsize=9.5, color=C['ink'])
        if i: ax.text(i, 60, '+%.1f%%' % (100*(v/train[0]-1)), ha='center', fontsize=9.5, color='white')
    ax.set_xticks(x); ax.set_xticklabels(names, fontsize=9.2)
    ax.set_ylabel('每源平均定位清除时间 / s'); ax.set_ylim(0, 960)
    ax.grid(True, axis='y'); ax.set_axisbelow(True)
    for sp in ('top','right'): ax.spines[sp].set_visible(False)
    ax.set_title('(c) 用 $p_{det}\\geq\\tau$ 卡顺路复测：越严越慢', pad=9)

    fig.suptitle('图 25　朝向可行集的闭式，以及"避免走到背向"为什么在这里不划算',
                 fontsize=13.5, color=C['ink'], y=1.0)
    print('已输出：', S.save(fig, '图25_可检测锥的闭式'))
