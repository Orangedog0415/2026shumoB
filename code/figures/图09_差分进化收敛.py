"""图 9：问题二第二检测点的差分进化求解——5 次独立运行都收敛到同一点。

与 code/experiments/问题二_DE选点.py 同一套目标与约束：F(S)=Ĵ(S)+0.05·|S−S₁|/5，
硬约束是外包络 P 的所有顶点到 S 的距离 ≤999 m。种群 24、迭代 40 代、F=0.7、CR=0.9。
第 1 次运行把 50 m 网格解 (850, −500) 作为初始个体之一，其余 4 次纯随机初始化。
运行：python 图09_差分进化收敛.py（约 1 分钟）  输出：figures/图09_差分进化收敛.pdf / .png
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
DE = _m('DE', HERE.parent/'experiments'/'问题二_DE选点.py')

if __name__ == '__main__':
    S.use_style()
    fg = DE.F((850., -500.))[0]
    runs = []
    for seed in range(5):
        pt, f, hist = DE.de(seed=seed, seeds=[(850., -500.)] if seed == 0 else [])
        runs.append((pt, f, hist)); print('seed %d → (%.1f, %.1f) F=%.3f' % (seed, pt[0], pt[1], f), flush=True)
    fig, axes = plt.subplots(1, 2, figsize=(12.2, 5.0), gridspec_kw=dict(width_ratios=[1.2, 1], wspace=.26))

    ax = axes[0]
    for i, (pt, f, hist) in enumerate(runs):
        ax.plot(range(1, len(hist)+1), hist, '-', lw=1.8,
                color=C['blue'] if i else C['orange'],
                label='第 1 次（含网格解作初始个体）' if i == 0 else ('第 2~5 次（纯随机初始）' if i == 1 else None),
                alpha=1.0 if i == 0 else .75)
    ax.axhline(fg, color=C['ink2'], lw=1.2, ls=(0,(4,3)))
    S.tag(ax, (len(runs[0][2])*.62, fg), '50 m 网格解 $F$ = %.2f m' % fg, dy=14)
    ax.set_xlabel('迭代代数'); ax.set_ylabel('当代最优评分 $F$ / m')
    ax.set_yscale('log'); ax.grid(True); ax.set_axisbelow(True)
    for sp in ('top','right'): ax.spines[sp].set_visible(False)
    ax.legend(loc='upper right')
    ax.set_title('(a) 5 次独立运行的收敛曲线（纵轴对数）', pad=9)

    ax = axes[1]
    pts = np.array([r[0] for r in runs])
    ax.plot(pts[:, 0], pts[:, 1], 'D', ms=9, mfc='none', mec=C['red'], mew=2.0, label='DE 解（5 次）')
    ax.plot([850], [-500], 'o', ms=9, mfc='none', mec=C['orange'], mew=2.0, label='50 m 网格解')
    for (x, y), (_, f, _) in zip(pts, runs):
        ax.text(x, y+38, '%.2f' % f, ha='center', fontsize=8.4, color=C['ink2'])
    ax.axhline(0, color=C['ink2'], lw=1.0, ls=(0,(4,3)))
    S.tag(ax, (pts[:, 0].mean(), 0), '目标关于 $y=0$ 对称', dy=13)
    ax.set_xlabel('x / m'); ax.set_ylabel('y / m')
    ax.grid(True); ax.set_axisbelow(True)
    for sp_ in ('top','right'): ax.spines[sp_].set_visible(False)
    ax.legend(loc='upper left')
    ax.set_title('(b) 解落在两个镜像最优上', pad=9)
    fold = np.stack([pts[:, 0], np.abs(pts[:, 1])], 1)
    sd = fold.std(axis=0)
    S.note(ax, '$F(S)$ 关于 $y=0$ 严格对称，故有两个等价最优。\n'
               '按 $|y|$ 折叠后 5 次解的标准差：x %.1f m，|y| %.1f m\n'
               '最优 $F$ = %.2f m，较网格解改进 %.1f%%'
               % (sd[0], sd[1], min(r[1] for r in runs), 100*(1-min(r[1] for r in runs)/fg)), loc='lower right')

    fig.suptitle('图 9　问题二的差分进化求解：收敛性与解的稳定性', fontsize=13.5, color=C['ink'], y=1.0)
    print('已输出：', S.save(fig, '图09_差分进化收敛'))
