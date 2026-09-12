"""图 31：保证假设的裕度与破坏——假设不成立时，"一定清干净"会怎样退化。

整条保证链建立在三条假设上：测向误差不超过 ±1°（实现里取 δ=1.005°，把 0.01° 的取整误差也算进去）、
接收半径不小于 1000 m、清除半径 20 m。前两条是题目给的，第三条是清除动作的物理规则。
这张图不是在调参，而是在回答"如果题目给的界不准，会发生什么"：
(a) 真实误差幅度从 0.5° 加到 3°，假设仍按 1.005°——一旦真实误差超过假设，楔形就可能把真源排除在外，
    定位区域会"指向错误的地方"，全清率断崖式下降；
(b) 反过来把假设的 δ 往上抬（买保险），真实误差固定 ±1°——代价是定位区域变大、补测与逐格清除变多；
(c) 清除方格边长越过理论阈值 20√2 ≈ 28.284 m 时，格心到格内最远点超过 20 m，逐格清除不再保证命中；
(d) 把 (a)(b) 合起来：假设的 δ 与真实误差的二维网格，答案非常干脆——只要 δ ≥ 真实误差就 30/30 全清，
    否则几乎全灭；δ 很大时仍有少量失败，因为 75×3 兜底格的 ±30 m 横向带宽是写死的，没有跟着 δ 一起放大。
运行：python 图31_保证假设的裕度.py   输出：figures/图31_保证假设的裕度.pdf / .png
"""
import importlib.util, math
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

if __name__ == '__main__':
    S.use_style()
    fig, axs = plt.subplots(2, 2, figsize=(12.4, 9.0), gridspec_kw=dict(wspace=.28, hspace=.38))
    axes = axs.ravel()

    ax = axes[0]
    rows = V.S4['true_error']; xs = [r['e'] for r in rows]
    ax.plot(xs, [100*r['ok']/r['tot'] for r in rows], '-o', color=C['blue'], lw=2.2, ms=7, label='全清局数占比')
    ax.plot(xs, [100*r['ratio'] for r in rows], '-s', color=C['orange'], lw=2.2, ms=6, label='平均清除率')
    ax.axvline(1.005, color=C['red'], lw=1.4, ls=(0,(4,3)))
    S.tag(ax, (1.005, 50), '假设的误差界 $\\delta$ = 1.005°', dx=44, dy=0)
    ax.set_xlabel('真实测向误差幅度 / °'); ax.set_ylabel('百分比 / %')
    ax.set_ylim(-4, 108); ax.grid(True); ax.set_axisbelow(True)
    for sp in ('top','right'): ax.spines[sp].set_visible(False)
    ax.legend(loc='lower left')
    ax.set_title('(a) 真实误差超过假设时的退化', pad=9)

    ax = axes[1]
    rows = V.S4['assumed_delta']; xs = [r['delta'] for r in rows]
    t0 = rows[0]['t']
    ax.plot(xs, [r['t'] for r in rows], '-o', color=C['blue'], lw=2.2, ms=7)
    for r in rows:
        ax.annotate('%+.1f%%' % (100*(r['t']/t0-1)), xy=(r['delta'], r['t']), xytext=(0, -16),
                    textcoords='offset points', ha='center', fontsize=8.6, color=C['ink2'])
    ax.axvline(1.005, color=C['red'], lw=1.4, ls=(0,(4,3)))
    ax.set_xlabel('假设的误差界 $\\delta$ / °'); ax.set_ylabel('每源平均定位清除时间 / s')
    ax.grid(True); ax.set_axisbelow(True)
    for sp in ('top','right'): ax.spines[sp].set_visible(False)
    ax.set_ylim(min(r['t'] for r in rows)-14, max(r['t'] for r in rows)+10)
    ax.set_title('(b) 把 $\\delta$ 抬高买保险的价钱', pad=9)
    S.note(ax, '真实误差固定 ±1°，全部 30 局都全清。\n抬 δ 只买保险，不改变正确性。', loc='upper left')

    ax = axes[2]
    rows = V.S4['cell']; xs = [r['cell'] for r in rows]
    ax.plot(xs, [100*r['ok']/r['tot'] for r in rows], '-o', color=C['blue'], lw=2.2, ms=7, label='全清局数占比')
    ax.plot(xs, [100*r['ratio'] for r in rows], '-s', color=C['orange'], lw=2.2, ms=6, label='平均清除率')
    ax.axvline(20*math.sqrt(2), color=C['red'], lw=1.4, ls=(0,(4,3)))
    S.tag(ax, (20*math.sqrt(2), 50), '理论阈值 $20\\sqrt{2}$ ≈ 28.284 m', dx=-58, dy=0)
    ax.set_xlabel('清除方格边长 / m'); ax.set_ylabel('百分比 / %')
    ax.set_ylim(-4, 108); ax.grid(True); ax.set_axisbelow(True)
    for sp in ('top','right'): ax.spines[sp].set_visible(False)
    ax.legend(loc='lower left')
    ax.set_title('(c) 方格边长越过理论阈值', pad=9)

    ax = axes[3]
    rows = V.S4['delta_vs_error']
    ds = [r['delta'] for r in rows]; es = [c['e'] for c in rows[0]['cells']]
    Z = np.array([[100*c['ok']/c['tot'] for c in r['cells']] for r in rows])
    pc = ax.pcolormesh(np.arange(len(es)+1), np.arange(len(ds)+1), Z, cmap='RdYlGn', vmin=0, vmax=100)
    for i in range(len(ds)):
        for j in range(len(es)):
            ax.text(j+.5, i+.5, '%.0f%%' % Z[i, j], ha='center', va='center', fontsize=10,
                    color=C['ink'])
    ax.plot([0, len(es)], [0, len(es)], '-', color=C['ink'], lw=1.6, zorder=6)
    S.tag(ax, (2.5, 2.5), '$\\delta$ = 真实误差', color=C['ink'], dx=30, dy=-16)
    cb = fig.colorbar(pc, ax=ax, pad=.02, fraction=.046); cb.outline.set_edgecolor(C['edge'])
    cb.set_label('全清局数占比 / %', fontsize=9.5)
    ax.set_xticks(np.arange(len(es))+.5); ax.set_xticklabels(['±%.1f°' % e for e in es])
    ax.set_yticks(np.arange(len(ds))+.5); ax.set_yticklabels(['%.3f°' % d for d in ds])
    ax.set_xlabel('真实测向误差幅度'); ax.set_ylabel('实现里假设的误差界 $\\delta$')
    ax.set_title('(d) 抬高 $\\delta$ 能不能救回超界的情形', pad=9)

    fig.suptitle('图 31　保证假设的裕度与破坏：假设不成立时会发生什么', fontsize=13.5, color=C['ink'], y=.985)
    print('已输出：', S.save(fig, '图31_保证假设的裕度'))
