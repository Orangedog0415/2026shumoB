"""图 22：保证性压力测试——180 局全部清除，且时间没有失控。

测试网格：5 种误差模型 × 接收半径（随机 1000~1500 m / 全取 1000 m）× 布局（圆内均匀 / 边界朝外的定向源）
× N=10/13/16 × 3 次重复，共 180 局，全部由方案七跑完。
其中"恒 +1°/恒 −1°/每点独立 ±1°"是刻意构造的最坏误差场（交接版本的误差场是空间相关的正弦），
"边界朝外"则把定向源全部摆在半径 1700~1800 m 处且朝向指向圆外——这是零漏测证书最吃紧的布局。
结论：未全清 0 局；每源平均 656 s。
运行：python 图22_压力测试.py   输出：figures/图22_压力测试.pdf / .png
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
FS = 2.5                                   # 全图文字统一放大倍数（相对原始字号）

def box(ax, groups, title, xlabel):
    keys = list(groups)
    data = [groups[k] for k in keys]
    bp = ax.boxplot(data, vert=True, widths=.5, patch_artist=True, showfliers=False,
                    medianprops=dict(color=C['ink'], lw=1.6),
                    boxprops=dict(facecolor='#d9e7f7', edgecolor=C['blue'], lw=1.1),
                    whiskerprops=dict(color=C['blue'], lw=1.1), capprops=dict(color=C['blue'], lw=1.1))
    rng = np.random.default_rng(0)
    for i, d in enumerate(data):
        ax.plot(rng.normal(i+1, .055, len(d)), d, 'o', ms=3.2, color=C['orange'], alpha=.55, zorder=5)
    ax.set_xticks(range(1, len(keys)+1)); ax.set_xticklabels(keys, fontsize=9*FS)
    ax.set_title(title, pad=12); ax.set_xlabel(xlabel)
    ax.grid(True, axis='y'); ax.set_axisbelow(True)
    for sp in ('top','right'): ax.spines[sp].set_visible(False)

if __name__ == '__main__':
    S.use_style()
    plt.rcParams.update({'xtick.labelsize': 9*FS, 'ytick.labelsize': 9*FS,
                         'axes.labelsize': 10*FS, 'axes.titlesize': 11.5*FS})
    rows = R.STRESS
    ts = np.array([r['t'] for r in rows])
    fig, axes = plt.subplots(1, 3, figsize=(18.6, 9.2),
                             gridspec_kw=dict(wspace=.28, width_ratios=[1, 1.24, 1.18]))
    fig.subplots_adjust(left=.085, right=.985, top=.80, bottom=.175)

    g = {}
    for r in rows: g.setdefault('N = %d' % r['n'], []).append(r['t'])
    box(axes[0], dict(sorted(g.items())), '(a) 按源数', '')
    axes[0].set_ylabel('每源平均定位清除时间 / s')

    g = {}
    for r in rows: g.setdefault(r['layout'] + '\n' + r['rmode'].replace(' 1000 m', '1000'), []).append(r['t'])
    box(axes[1], g, '(b) 按布局 × 接收半径', '')

    g = {}
    SHORT = {'交接误差场': '交接场', '每点独立均匀': '独立均匀', '恒 +1°': '恒 +1°', '恒 −1°': '恒 −1°', '每点独立 ±1°': '独立 ±1°'}
    for r in rows: g.setdefault(SHORT.get(r['err'], r['err']), []).append(r['t'])
    box(axes[2], g, '(c) 按误差模型', '')
    axes[2].tick_params(axis='x', labelrotation=40)

    for ax in axes: ax.set_ylim(0, max(ts)*1.12)
    axes[0].text(.04, .035, '180 局，未全清 0 局\n每源平均 %.0f s\n中位 %.0f s，最大 %.0f s'
                 % (ts.mean(), np.median(ts), ts.max()), transform=axes[0].transAxes,
                 va='bottom', fontsize=9.2*FS, color=C['ink2'], linespacing=1.6)
    fig.suptitle('图 22　方案七的保证性压力测试（问题四，180 局）', fontsize=13.5*FS, color=C['ink'], y=.965)
    print('已输出：', S.save(fig, '图22_压力测试'))
