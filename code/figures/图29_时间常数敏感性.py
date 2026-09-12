"""图 29：覆盖网的取舍完全由时间常数决定——换一套时间常数，最优的网会不会变。

问题四的粗探代价大致是"巡回长度 / 速度 + 覆盖点数 × 每点检测代价"。移动越贵越该缩短巡回，
检测越贵越该减少点数。附件给的常数是速度 5 m/s、检测 5 s、切换 1 s；如果正式测试与之不同，
25 点 / 17.5 km 的方案七网未必还优于 27 点 / 17.8 km 的方案六网。
(a)(b) 在 (速度, 检测时间) 的 3×3 网格上重跑三个版本，画出方案七相对方案六、相对方案四的变化；
(c) 用纯代价模型画出两张网的交叉线：横轴是"每点检测代价 / 速度"的比值。
注意：调度器内部的代价常数仍按默认值写死，三个版本用的是同一套调度器，只有覆盖网不同，比较是公平的。
运行：python 图29_时间常数敏感性.py   输出：figures/图29_时间常数敏感性.pdf / .png
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
S = _m('S', HERE/'_绘图样式.py'); V = _m('V', HERE/'_敏感性数据.py'); C = S.C
L = _m('L', HERE.parent/'experiments'/'方案四_实验台.py')

def tl(net):
    T = L.tour_nn2opt([tuple(p) for p in net])
    return L.dist((0,0), T[0]) + sum(L.dist(T[i], T[i+1]) for i in range(len(T)-1))

if __name__ == '__main__':
    S.use_style()
    rows = V.S2
    VS = sorted({r['v'] for r in rows}); TDS = sorted({r['td'] for r in rows})
    def grid(f):
        Z = np.zeros((len(TDS), len(VS)))
        for r in rows: Z[TDS.index(r['td']), VS.index(r['v'])] = f(r)
        return Z
    fig, axes = plt.subplots(1, 3, figsize=(14.0, 4.9), gridspec_kw=dict(wspace=.34, width_ratios=[1, 1, 1.15]))

    for ax, (ref, title) in zip(axes[:2], (('方案六', '(a) 方案七 相对 方案六'), ('方案四', '(b) 方案七 相对 方案四'))):
        Z = grid(lambda r: 100*(r['方案七']/r[ref]-1))
        m = max(abs(Z).max(), 1.)
        pc = ax.pcolormesh(np.arange(len(VS)+1), np.arange(len(TDS)+1), Z, cmap='RdBu_r', vmin=-m, vmax=m)
        for i in range(len(TDS)):
            for j in range(len(VS)):
                ax.text(j+.5, i+.5, '%+.1f%%' % Z[i, j], ha='center', va='center', fontsize=9.5,
                        color=C['white'] if abs(Z[i, j]) > .55*m else C['ink'])
        cb = fig.colorbar(pc, ax=ax, pad=.02, fraction=.046); cb.outline.set_edgecolor(C['edge'])
        cb.set_label('变化 / %（负 = 方案七更快）', fontsize=9)
        ax.set_xticks(np.arange(len(VS))+.5); ax.set_xticklabels(['%.1f' % v for v in VS])
        ax.set_yticks(np.arange(len(TDS))+.5); ax.set_yticklabels(['%.0f' % v for v in TDS])
        ax.set_xlabel('移动速度 / (m/s)'); ax.set_ylabel('单次检测时间 / s')
        ax.set_title(title, pad=9)
        ax.add_patch(plt.Rectangle((VS.index(5.), TDS.index(5.)), 1, 1, facecolor='none',
                                   edgecolor=C['ink'], lw=2.2, zorder=6))

    ax = axes[2]
    K = {'方案四 27 点 / %.1f km' % (tl(L.NET4_V4())/1000): (27, tl(L.NET4_V4())),
         '方案六 27 点 / %.1f km' % (tl(L.NET4_V6())/1000): (27, tl(L.NET4_V6())),
         '方案七 25 点 / %.1f km' % (tl(L.NET4_V7())/1000): (25, tl(L.NET4_V7()))}
    ratio = np.linspace(0, 820, 300)     # 每点检测代价 / (1/速度)，即 “每点代价 × 速度”
    for (lab, (k, ln)), col in zip(K.items(), ('#bcd6f2', '#5d9ae1', C['blue'])):
        ax.plot(ratio, ln + k*ratio, '-', color=col, lw=2.2, label=lab)
    ax.axvline(20*6*5, color=C['ink2'], lw=1.2, ls=(0,(4,3)))
    S.tag(ax, (20*6*5, 21000), '附件常数\n20 频道 × 6 s × 5 m/s', dx=-56, dy=0)
    ax.set_xlabel('每个覆盖点的检测代价 × 移动速度 / m'); ax.set_ylabel('等效粗探路程 / m')
    ax.grid(True); ax.set_axisbelow(True)
    for sp in ('top','right'): ax.spines[sp].set_visible(False)
    ax.legend(loc='upper left', fontsize=8.8)
    ax.set_title('(c) 纯代价模型：25 点网何时不再占优', pad=9)
    fig.subplots_adjust(bottom=.23)
    fig.text(.5, .02, '(c) 的纵轴是"把检测时间折算成等效路程"后的粗探总代价：每条线的斜率就是覆盖点数，截距就是巡回长度。'
             '方案七的斜率与截距都更小，\n所以在整个横轴范围内都压在方案六之下；只有当"每点检测代价"降到接近 0 时两者才趋同——'
             '这解释了 (a) 里九个格子为什么全是负值。',
             ha='center', fontsize=9, color=C['ink2'], linespacing=1.7)

    fig.suptitle('图 29　模拟器时间常数的敏感性：换一套常数，最优覆盖网会不会变',
                 fontsize=13.5, color=C['ink'], y=1.0)
    print('已输出：', S.save(fig, '图29_时间常数敏感性'))
