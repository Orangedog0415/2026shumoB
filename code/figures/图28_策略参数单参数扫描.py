"""图 28：八个策略参数的单参数(OAT)扫描——每个参数单独动，其余固定为方案四标定值。

纵轴是相对"采用值"的变化百分比（正值 = 更慢），问题三与问题四画在同一张子图里以便共用刻度。
细线是三批案例各自的结果，粗线是三批的平均，竖虚线标出实际采用的取值。
这张图回答两个问题：采用值是不是落在平坦区里（是否过拟合训练集），以及哪些参数真的要紧。
读法要点：
  · x（顺路清除绕行阈值）只影响问题三——问题四用的是联合重规划，根本不看这个阈值；
  · cover_k（直接逐格清除的格数上限）与 lp_max（局部补测次数上限）是少数几个真正有斜率的参数；
  · 大部分参数在采用值附近的 ±1% 带内，说明结果不是靠精调参数堆出来的。
运行：python 图28_策略参数单参数扫描.py   输出：figures/图28_策略参数单参数扫描.pdf / .png
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
NAME = {'x': '$x$　顺路清除绕行阈值 / m', 'r_ok': '$r_{ok}$　可清门槛（区域半径）/ m',
        'probe_angle': 'probe_angle　顺带补测夹角 / °', 'lp_cap': 'lp_cap　局部补测距离上限 / m',
        'lp_angle': 'lp_angle　与区域长轴夹角 / °', 'lp_max': 'lp_max　局部补测次数上限',
        'cover_k': 'cover_k　直接逐格清除的格数上限', 'final': 'final　最终清除顺序'}

if __name__ == '__main__':
    S.use_style()
    keys = list(V.S1)
    fig, axs = plt.subplots(2, 4, figsize=(15.0, 7.4), gridspec_kw=dict(hspace=.42, wspace=.26))
    for ax, k in zip(axs.ravel(), keys):
        d = V.S1[k]; rows = d['rows']; base = d['cfg4']
        cat = isinstance(rows[0]['v'], str)
        xs = np.arange(len(rows)) if cat else np.array([r['v'] for r in rows], float)
        bi = next(i for i, r in enumerate(rows) if r['v'] == base)
        for q, col, lab in (('q3', C['orange'], '问题三'), ('q4', C['blue'], '问题四')):
            M = np.array([r[q] for r in rows], float)           # (len(vals), 3 seeds)
            ref = M[bi]
            rel = (M/ref - 1)*100
            for j in range(rel.shape[1]):
                ax.plot(xs, rel[:, j], '-', color=col, lw=.8, alpha=.35)
            ax.plot(xs, rel.mean(1), '-o', color=col, lw=2.0, ms=4.5, label=lab)
        mx = max(abs((np.array([r[q] for r in rows], float)/np.array([r[q] for r in rows], float)[bi]-1)*100).max()
                 for q in ('q3', 'q4'))
        ax.text(.03, .96, '最大影响 %.1f%%' % mx, transform=ax.transAxes, va='top', fontsize=8.4, color=C['ink2'])
        ax.axvline(xs[bi], color=C['ink2'], lw=1.1, ls=(0,(4,3)))
        ax.axhline(0, color=C['edge'], lw=1.0)
        if cat: ax.set_xticks(xs); ax.set_xticklabels([r['v'] for r in rows])
        ax.set_title(NAME[k], fontsize=10, pad=7)
        ax.grid(True); ax.set_axisbelow(True)
        for sp in ('top','right'): ax.spines[sp].set_visible(False)
        ax.tick_params(labelsize=8.5)
    for ax in axs[:, 0]: ax.set_ylabel('相对采用值的变化 / %')
    axs[0, 0].legend(loc='center left', fontsize=8.6)
    fig.text(.5, .005, '每个子图的纵轴范围不同，左上角标出该参数在扫描范围内的最大影响幅度；竖虚线 = 实际采用值。'
             'x 与 final 只影响问题三（问题四用联合重规划，不看绕行阈值，也不用最终清除顺序）。',
             ha='center', fontsize=9, color=C['ink2'])
    fig.suptitle('图 28　八个策略参数的单参数扫描（细线 = 三批案例，粗线 = 均值）',
                 fontsize=13.5, color=C['ink'], y=.985)
    print('已输出：', S.save(fig, '图28_策略参数单参数扫描'))
