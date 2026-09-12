"""图 24：自适应补测（GT06 §4.4.4）为什么在本题失效——空频道永远是"未解"的。

GT06 表 17 的收益建立在"未解频道数 u 很小"上：七点网粗探之后只有少数频道分辨不了，
对这批频道再走加密环即可。但本题是 20 个频道里只有 N≤16 个有源：
  · 有源频道：粗探时若落在朝向半平面内就当场检出，确实只有少数需要加密；
  · **空频道**：无论测多少次都只会返回 no_signal，它要变成"已判空"只有两条路——
    走完整张认证网出证书，或者靠计数提前停（已清+已发 = 16）。
所以未解频道数 u ≥ 20 − N ≥ 4，N=10 时 u ≥ 10，"少数频道才加密"的前提根本不成立。
实测三种粗探集分别慢 14.3% / 18.2% / 16.1%（训练集）。
运行：python 图24_自适应补测为何失效.py   输出：figures/图24_自适应补测为何失效.pdf / .png
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
S = _m('S', HERE/'_绘图样式.py'); C = S.C

if __name__ == '__main__':
    S.use_style()
    fig, axes = plt.subplots(1, 2, figsize=(12.6, 5.0), gridspec_kw=dict(width_ratios=[1.15, 1], wspace=.26))

    # (a) 20 个频道的格子图
    ax = axes[0]; S.blank_axes(ax, (0, 20.6), (-1.2, 4.6))
    for row, (N, lab) in enumerate(((16, 'N = 16'), (13, 'N = 13'), (10, 'N = 10'))):
        y = 3.2 - row*1.35
        for ch in range(20):
            occupied = ch < N
            det = occupied and (ch % 3 != 2)     # 示意：定向源约 1/3 在粗探时被漏
            fc = ('#9bc3a4' if det else C['orange']) if occupied else C['red']
            ax.add_patch(plt.Rectangle((ch+.08, y), .84, .9, facecolor=fc, alpha=.85 if occupied else .35,
                                       edgecolor='white', lw=.8))
        ax.text(-.4, y+.45, lab, ha='right', va='center', fontsize=10, color=C['ink'])
        ax.text(20.4, y+.45, 'u ≥ %d' % (20-N), ha='left', va='center', fontsize=9.5, color=C['red'])
    ax.text(10, 4.35, '20 个频道', ha='center', fontsize=10, color=C['ink2'])
    for i, (c, a, lab) in enumerate((('#9bc3a4', .85, '有源，粗探就检出'),
                                     (C['orange'], .85, '有源，粗探漏测（需加密）'),
                                     (C['red'], .35, '空频道：永远"未解"'))):
        ax.add_patch(plt.Rectangle((i*7.0+.2, -.95), .8, .7, facecolor=c, alpha=a, edgecolor='white'))
        ax.text(i*7.0+1.2, -.60, lab, va='center', fontsize=9, color=C['ink2'])
    ax.set_title('(a) 未解频道数 u 的下界就是空频道数', pad=9)

    # (b) 三种粗探集的实测代价
    ax = axes[1]
    names = ['方案六\n单段 27 点', '6.2a\nA1 子集粗探', '6.2b\n八边形粗探', '6.2c\n七点网粗探']
    train = [553.3, 632.6, 653.8, 642.5]
    vA = [556.8, 661.0, 669.8, 670.6]; vB = [549.2, 651.1, 668.0, 667.5]
    x = np.arange(4)
    ax.bar(x, train, width=.56, color=[C['blue']] + [C['red']]*3, alpha=.9)
    for i in range(4):
        ax.plot([i, i], [vA[i], vB[i]], '-', color=C['ink2'], lw=1.0, zorder=5)
        ax.plot([i]*2, [vA[i], vB[i]], 'o', ms=5, mfc='none', mec=C['ink2'], mew=1.2, zorder=6)
        ax.text(i, max(train[i], vA[i], vB[i])+12, '%.0f' % train[i], ha='center', fontsize=9.5, color=C['ink'])
        if i: ax.text(i, 60, '+%.1f%%' % (100*(train[i]/train[0]-1)), ha='center', fontsize=9.5, color='white')
    ax.set_xticks(x); ax.set_xticklabels(names, fontsize=8.8)
    ax.set_ylabel('每源平均定位清除时间 / s'); ax.set_ylim(0, 760)
    ax.grid(True, axis='y'); ax.set_axisbelow(True)
    for sp in ('top','right'): ax.spines[sp].set_visible(False)
    ax.set_title('(b) 三种粗探集都更慢（柱 = 训练集，点 = 验证集）', pad=9)

    fig.suptitle('图 24　自适应补测在本题失效的机理与实测', fontsize=13.5, color=C['ink'], y=1.0)
    print('已输出：', S.save(fig, '图24_自适应补测为何失效'))
