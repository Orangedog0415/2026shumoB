"""图 19：逐局配对——方案七是不是"平均快"而已，还是"局局都快"。

三批案例共 90 局，每局一个点：横轴是方案六的用时，纵轴是方案七的用时，同一局、同一误差场。
落在 45° 参考线下方表示方案七更快。右图是配对差值的分布。
这样看比只比平均值可靠：平均值可能被少数几局拉动，而配对图直接回答"会不会有局变慢"。
运行：python 图19_逐局配对对比.py   输出：figures/图19_逐局配对对比.pdf / .png
"""
import importlib.util
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import font_manager
HERE = Path(__file__).resolve().parent
try: font_manager.fontManager.addfont('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
except Exception: pass
def _m(n, f):
    s = importlib.util.spec_from_file_location(n, str(f)); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
S = _m('S', HERE/'_绘图样式.py'); R = _m('R', HERE/'_结果数据.py'); C = S.C

if __name__ == '__main__':
    S.use_style()
    fig, axes = plt.subplots(1, 2, figsize=(12.2, 5.4), gridspec_kw=dict(width_ratios=[1.15, 1], wspace=.26))
    a = np.concatenate([R.t('方案六', s) for s in R.SEEDS])
    b = np.concatenate([R.t('方案七', s) for s in R.SEEDS])
    n = np.array([10]*10+[13]*10+[16]*10)
    n = np.concatenate([n, n, n])

    ax = axes[0]
    for k, (nn, col, mk) in enumerate(((10, '#bcd6f2', 'o'), (13, '#5d9ae1', 's'), (16, C['blue'], '^'))):
        m = n == nn
        ax.plot(a[m], b[m], mk, ms=5.5, mfc=col, mec=C['white'], mew=.6, label='N = %d' % nn, zorder=5)
    lo, hi = min(a.min(), b.min())*.92, max(a.max(), b.max())*1.04
    ax.plot([lo, hi], [lo, hi], '-', color=C['ink2'], lw=1.1, zorder=4)
    ax.fill_between([lo, hi], [lo, hi], [lo, lo], color=C['blue'], alpha=.05, zorder=2)
    ax.text(hi*.97, lo+ (hi-lo)*.06, '方案七更快', ha='right', fontsize=9.5, color=C['ink2'])
    ax.set_xlim(lo, hi); ax.set_ylim(lo, hi); ax.set_aspect('equal')
    ax.set_xlabel('方案六 每源平均时间 / s'); ax.set_ylabel('方案七 每源平均时间 / s')
    ax.grid(True); ax.set_axisbelow(True)
    for sp in ('top','right'): ax.spines[sp].set_visible(False)
    ax.legend(loc='upper left')
    ax.set_title('(a) 90 局配对散点', pad=9)

    ax = axes[1]
    d = b - a
    ax.hist(d, bins=np.arange(np.floor(d.min()/20)*20, np.ceil(d.max()/20)*20+1, 20),
            color=C['blue'], alpha=.85, edgecolor=C['white'], lw=.6)
    ax.axvline(0, color=C['ink2'], lw=1.2)
    ax.axvline(d.mean(), color=C['red'], lw=1.6, ls=(0,(4,3)))
    S.tag(ax, (d.mean(), ax.get_ylim()[1]*.82), '均值 %.1f s' % d.mean(), color=C['red'], dx=-34, dy=0)
    ax.set_xlabel('方案七 - 方案六（负值 = 方案七更快）/ s'); ax.set_ylabel('局数')
    ax.grid(True, axis='y'); ax.set_axisbelow(True)
    for sp in ('top','right'): ax.spines[sp].set_visible(False)
    ax.set_title('(b) 配对差值分布', pad=9)
    S.note(ax, '90 局里方案七更快 %d 局、更慢 %d 局\n最大变慢 %.0f s，最大变快 %.0f s'
               % (int((d < 0).sum()), int((d > 0).sum()), d.max(), -d.min()), loc='upper left')

    fig.suptitle('图 19　方案七 vs 方案六的逐局配对对比（问题四，3 批案例共 90 局）',
                 fontsize=13.5, color=C['ink'], y=1.0)
    print('已输出：', S.save(fig, '图19_逐局配对对比'))
