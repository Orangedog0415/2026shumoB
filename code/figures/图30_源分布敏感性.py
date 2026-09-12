"""图 30：源分布假设的敏感性——换一套生成分布，方案七还领先吗。

训练与验证案例都按同一套分布生成：位置在半径 1800 m 圆盘内均匀、接收半径 r~U[1000,1500]、
定向源比例 pD=0.65。这三条都是我们自己设的，题目并没有规定。这里各扫一轮，
每组重新生成 30 局（N=10/13/16 各 10 局），方案四与方案七在同一批案例上对比。
读法要点：
  · pD=0 就是纯全向源（等价于问题三的物理场景放在问题四的覆盖网上跑），pD=1 是全定向；
  · r 全取 1000 m 是最不利的（可检测域最小），全取 1500 m 最有利；
  · 源集中在外环（1200~1800 m）比集中在中心更难，因为边界处的方位包围最吃紧。
运行：python 图30_源分布敏感性.py   输出：figures/图30_源分布敏感性.pdf / .png
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
LAB = {'rmode': {'min': '全取\n1000 m', 'uniform': '$U$[1000,1500]\n（训练集口径）', 'max': '全取\n1500 m'},
       'pos':   {'inner': '集中在中心\n0~900 m', 'uniform': '圆内均匀\n（训练集口径）', 'outer': '集中在外环\n1200~1800 m'}}

if __name__ == '__main__':
    S.use_style()
    fig, axes = plt.subplots(1, 3, figsize=(13.8, 4.9), gridspec_kw=dict(wspace=.30, width_ratios=[1.25, 1, 1]))

    ax = axes[0]
    rows = V.S3['pD']; xs = [r['v'] for r in rows]
    for tag, col, mk in (('方案四', '#8fbaea', 's'), ('方案七', C['blue'], 'o')):
        ax.plot(xs, [r[tag] for r in rows], '-'+mk, color=col, lw=2.2, ms=7, label=tag)
    for r in rows:
        ax.annotate('%+.0f%%' % (100*(r['方案七']/r['方案四']-1)), xy=(r['v'], r['方案七']),
                    xytext=(0, -15), textcoords='offset points', ha='center',
                    fontsize=8.4, color=C['ink2'])
    ax.set_ylim(min(r['方案七'] for r in rows)-28, max(r['方案四'] for r in rows)+20)
    ax.axvline(.65, color=C['ink2'], lw=1.1, ls=(0,(4,3)))
    S.tag(ax, (.65, max(r['方案四'] for r in rows)), '训练/验证集用的 0.65', dy=10)
    ax.set_xlabel('定向源比例 $p_D$'); ax.set_ylabel('每源平均定位清除时间 / s')
    ax.grid(True); ax.set_axisbelow(True)
    for sp in ('top','right'): ax.spines[sp].set_visible(False)
    ax.legend(loc='lower right')
    ax.set_title('(a) 定向源比例', pad=9)

    for ax, key, title in ((axes[1], 'rmode', '(b) 接收半径分布'), (axes[2], 'pos', '(c) 源位置分布')):
        rows = V.S3[key]; x = np.arange(len(rows)); w = .34
        for i, (tag, col) in enumerate((('方案四', '#8fbaea'), ('方案七', C['blue']))):
            b = ax.bar(x+(i-.5)*w, [r[tag] for r in rows], width=w*.9, color=col, label=tag)
            for rect, r in zip(b, rows):
                ax.text(rect.get_x()+rect.get_width()/2, r[tag]+9, '%.0f' % r[tag],
                        ha='center', fontsize=8.4, color=C['ink2'])
        for i, r in enumerate(rows):
            ax.text(i, 40, '%+.1f%%' % (100*(r['方案七']/r['方案四']-1)), ha='center',
                    fontsize=9, color=C['white'])
        ax.set_xticks(x); ax.set_xticklabels([LAB[key][r['v']] for r in rows], fontsize=8.8)
        ax.set_ylim(0, max(max(r['方案四'], r['方案七']) for r in rows)*1.2)
        ax.grid(True, axis='y'); ax.set_axisbelow(True)
        for sp in ('top','right'): ax.spines[sp].set_visible(False)
        ax.set_title(title, pad=9)
        if key == 'rmode': ax.set_ylabel('每源平均定位清除时间 / s')
    axes[1].legend(loc='upper right', fontsize=9)

    fig.suptitle('图 30　源分布假设的敏感性：方案七相对方案四的优势在各种分布下都成立',
                 fontsize=13.5, color=C['ink'], y=1.0)
    print('已输出：', S.save(fig, '图30_源分布敏感性'))
