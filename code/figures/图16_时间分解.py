"""图 16：四个版本的时间都花在哪——每源平均时间的分解。

分解口径直接取自模拟器的计时器：行进（距离 / 5 m·s⁻¹）、检测（每次 5 s）、频道切换（每次 1 s）、
清除（成功 5 s / 未命中 3 s）。数值是问题四训练集 30 局的每源平均。
可以看到：优化一路做下来，**行进始终是第一大项**，这也是为什么后面几轮都在压覆盖网与路线，
而不是去抠检测次数。检测的绝对时间一路从 140 s 降到 109 s，但它的占比反而从 14% 升到 21%——
说明行进被压得更狠，剩下的检测大多是"为了出证书必须做"的那部分。
运行：python 图16_时间分解.py   输出：figures/图16_时间分解.pdf / .png
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
KEYS = [('moves', '行进', C['blue']), ('detect', '检测', '#8fbaea'),
        ('switch', '频道切换', C['orange']), ('clear', '清除', '#9bc3a4')]

if __name__ == '__main__':
    S.use_style()
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 5.2), gridspec_kw=dict(wspace=.28))
    data = {v: R.share(v) for v in R.VER}
    x = np.arange(len(R.VER))

    ax = axes[0]
    bot = np.zeros(len(R.VER))
    for k, lab, col in KEYS:
        vals = np.array([data[v][k] for v in R.VER])
        ax.bar(x, vals, bottom=bot, color=col, width=.6, label=lab, edgecolor=C['white'], lw=1.2)
        for i, (b, h) in enumerate(zip(bot, vals)):
            if h > 18: ax.text(i, b+h/2, '%.0f' % h, ha='center', va='center', fontsize=9, color=C['white'])
        bot += vals
    for i, v in enumerate(bot): ax.text(i, v+8, '%.0f s' % v, ha='center', fontsize=9.5, color=C['ink'])
    ax.set_xticks(x); ax.set_xticklabels(R.VER)
    ax.set_ylabel('每源平均时间 / s'); ax.set_ylim(0, bot.max()*1.16)
    ax.grid(True, axis='y'); ax.set_axisbelow(True)
    for sp in ('top','right'): ax.spines[sp].set_visible(False)
    ax.legend(loc='upper right', ncol=2)
    ax.set_title('(a) 绝对时间分解（问题四训练集）', pad=9)

    ax = axes[1]
    bot = np.zeros(len(R.VER))
    tot = np.array([sum(data[v][k] for k, _, _ in KEYS) for v in R.VER])
    for k, lab, col in KEYS:
        vals = np.array([data[v][k] for v in R.VER])/tot*100
        ax.bar(x, vals, bottom=bot, color=col, width=.6, edgecolor=C['white'], lw=1.2)
        for i, (b, h) in enumerate(zip(bot, vals)):
            if h > 4: ax.text(i, b+h/2, '%.0f%%' % h, ha='center', va='center', fontsize=9, color=C['white'])
        bot += vals
    ax.set_xticks(x); ax.set_xticklabels(R.VER)
    ax.set_ylabel('占比 / %'); ax.set_ylim(0, 108)
    ax.grid(True, axis='y'); ax.set_axisbelow(True)
    for sp in ('top','right'): ax.spines[sp].set_visible(False)
    ax.set_title('(b) 相对占比：行进始终是第一大项', pad=9)

    fig.suptitle('图 16　四个版本的时间分解（每源平均，问题四）', fontsize=13.5, color=C['ink'], y=1.0)
    print('已输出：', S.save(fig, '图16_时间分解'))
