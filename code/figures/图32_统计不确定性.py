"""图 32：结果的统计不确定性——均值的 bootstrap 区间与逐局配对检验。

每批案例只有 30 局，均值本身是有抽样误差的。这里对 results/绘图数据.json 里的逐局结果做：
(a) 各版本每源平均时间的 95% bootstrap 置信区间（每批 30 局，10000 次重抽样）；
(b) 三批合并 90 局的**配对**差值（同一局、同一误差场）的 bootstrap 区间，以及 Wilcoxon 符号秩检验。
配对比独立两样本更有力：案例难度的个体差异被消掉了。
结论：方案七 vs 方案四、方案七 vs 方案一的差异远大于抽样误差；方案七 vs 方案六的差异虽然只有 -18 s，
但配对区间不跨 0，Wilcoxon p 值也显著——不是噪声，只是幅度小。
运行：python 图32_统计不确定性.py   输出：figures/图32_统计不确定性.pdf / .png
"""
import importlib.util
from pathlib import Path
import numpy as np
from scipy.stats import wilcoxon
import matplotlib.pyplot as plt
from matplotlib import font_manager
HERE = Path(__file__).resolve().parent
try: font_manager.fontManager.addfont('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
except Exception: pass
def _m(n, f):
    s = importlib.util.spec_from_file_location(n, str(f)); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
S = _m('S', HERE/'_绘图样式.py'); R = _m('R', HERE/'_结果数据.py'); C = S.C
RNG = np.random.default_rng(0)

def boot(x, n=10000):
    x = np.asarray(x, float)
    m = RNG.choice(x, size=(n, len(x)), replace=True).mean(1)
    return x.mean(), np.percentile(m, 2.5), np.percentile(m, 97.5)

if __name__ == '__main__':
    S.use_style()
    SH = ['#bcd6f2', '#8fbaea', '#5d9ae1', C['blue']]
    fig, axes = plt.subplots(1, 2, figsize=(12.8, 5.4), gridspec_kw=dict(width_ratios=[1.15, 1], wspace=.28))

    ax = axes[0]
    w = .2; x = np.arange(3)
    for i, v in enumerate(R.VER):
        ms, los, his = [], [], []
        for sd in R.SEEDS:
            m, lo, hi = boot(R.t(v, sd)); ms.append(m); los.append(m-lo); his.append(hi-m)
        ax.bar(x+(i-1.5)*w, ms, width=w*.9, color=SH[i], label=v)
        ax.errorbar(x+(i-1.5)*w, ms, yerr=[los, his], fmt='none', ecolor=C['ink2'], elinewidth=1.2, capsize=3)
    ax.set_xticks(x); ax.set_xticklabels([R.SEED_NAME[s] for s in R.SEEDS])
    ax.set_ylabel('每源平均定位清除时间 / s'); ax.set_ylim(0, 1150)
    ax.grid(True, axis='y'); ax.set_axisbelow(True)
    for sp in ('top','right'): ax.spines[sp].set_visible(False)
    ax.legend(loc='upper right', ncol=2)
    ax.set_title('(a) 每批 30 局的均值与 95% bootstrap 区间', pad=9)
    hw = np.mean([boot(R.t('方案七', sd))[0]-boot(R.t('方案七', sd))[1] for sd in R.SEEDS])
    S.note(ax, '单批 30 局的均值半宽约 ±%.0f s\n所以只看单批的小差异不可靠，要看配对' % hw, loc='upper left')

    ax = axes[1]
    PAIRS = [('方案七', '方案六'), ('方案七', '方案四'), ('方案七', '方案一')]
    ys = np.arange(len(PAIRS))[::-1]
    for k, (a, b) in enumerate(PAIRS):
        da = np.concatenate([R.t(a, sd) for sd in R.SEEDS])
        db = np.concatenate([R.t(b, sd) for sd in R.SEEDS])
        d = da - db
        m, lo, hi = boot(d)
        p = wilcoxon(da, db).pvalue
        ax.plot([lo, hi], [ys[k]]*2, '-', color=C['blue'], lw=3.0, solid_capstyle='round', zorder=4)
        ax.plot([m], [ys[k]], 'o', ms=9, color=C['blue'], zorder=5)
        ax.text(hi+6, ys[k], '%.1f s　[%.1f, %.1f]　Wilcoxon p = %s'
                % (m, lo, hi, ('%.1e' % p) if p < 1e-3 else '%.4f' % p),
                va='center', fontsize=9.5, color=C['ink'])
        ax.text(lo-6, ys[k], '%s - %s' % (a, b), va='center', ha='right', fontsize=10, color=C['ink'])
        ax.text(lo-6, ys[k]-.26, '更快 %d / %d 局' % (int((d < 0).sum()), len(d)),
                va='center', ha='right', fontsize=8.6, color=C['ink2'])
    ax.axvline(0, color=C['ink2'], lw=1.2)
    ax.set_yticks([]); ax.set_xlabel('配对差值（负值 = 前者更快）/ s')
    ax.set_xlim(-520, 240); ax.set_ylim(-.7, len(PAIRS)-.3)
    ax.grid(True, axis='x'); ax.set_axisbelow(True)
    for sp in ('top','right','left'): ax.spines[sp].set_visible(False)
    ax.set_title('(b) 90 局配对差值的 95% bootstrap 区间', pad=9)

    fig.suptitle('图 32　结果的统计不确定性：30 局够不够，差异是不是噪声', fontsize=13.5, color=C['ink'], y=1.0)
    print('已输出：', S.save(fig, '图32_统计不确定性'))
