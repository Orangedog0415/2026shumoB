"""图 34：《问题三、四算法修订大纲》四条改动的验收——两条采用、两条未通过。

大纲里所有可验证的数字我们都复算过并逐位吻合（时间占比、按源数表、压力分组均值、七点环的覆盖上界与巡回）。
四条改动按大纲自己的验收口径逐条实现、在同一批冻结案例上做**配对**比较：
(a) 7.2 的机理：大纲给的算例——顶点均值中心不是最小包围圆圆心，覆盖半径 28.26 m 越过 19.5 m 门槛，
    而真正的最小包围圆只有 19.01 m，本可以一次清除。实测 390 次局部清除里，最小包围圆 100% 更小，
    其中 7.7% 把"不可直接清除"变成"可直接清除"。
(b) 四条改动的配对效果与 95% bootstrap 区间：只有 7.2 的区间不跨 0；7.3 时间中性但少 1.0% 请求；
    7.4、7.5 点估计更慢、区间跨 0，按大纲的验收口径不采用。
(c) 方案八（= 方案七 + 7.2 + 7.3）在开发集、全新留出集与 180 局压力测试上的结果。
运行：python 图34_大纲修订的验收.py   输出：figures/图34_大纲修订的验收.pdf / .png
"""
import json, math, importlib.util
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPoly
from matplotlib import font_manager
HERE = Path(__file__).resolve().parent
try: font_manager.fontManager.addfont('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
except Exception: pass
def _m(n, f):
    s = importlib.util.spec_from_file_location(n, str(f)); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
S = _m('S', HERE/'_绘图样式.py'); C = S.C
ST = json.load(open(HERE.parent/'experiments'/'results'/'大纲修订_配对统计.json', encoding='utf-8'))

# 方案七 → 方案八（来自 results/方案八_运行输出.txt）
DEV = {'问题三': (302.4, 300.6), '问题四': (535.3, 530.3)}
HOLD = {'问题三': 297.6, '问题四': 527.6}

if __name__ == '__main__':
    S.use_style()
    fig, axes = plt.subplots(1, 3, figsize=(14.4, 5.6), gridspec_kw=dict(wspace=.38, width_ratios=[1, 1.2, 1]))
    fig.subplots_adjust(bottom=.26, top=.86)

    # ---- (a) 最小包围圆 vs 顶点均值中心 ----
    ax = axes[0]
    P = [(-19., 0.), (19., 0.), (19., 1.), (18., 2.)]
    cm = (sum(p[0] for p in P)/4, sum(p[1] for p in P)/4); rm = max(math.dist(cm, p) for p in P)
    cc, rc = (0., .5), 19.0066
    ax.add_patch(plt.Circle(cm, rm, facecolor=C['red'], alpha=.08, edgecolor=C['red'], lw=1.5, ls=(0,(5,4))))
    ax.add_patch(plt.Circle(cc, rc, facecolor='#9bc3a4', alpha=.20, edgecolor='#3f8a50', lw=1.8))
    ax.add_patch(MplPoly(P, closed=True, facecolor=C['orange'], alpha=.55, edgecolor=C['orange'], lw=1.8, zorder=5))
    ax.plot([p[0] for p in P], [p[1] for p in P], 'o', ms=5, mfc=C['white'], mec=C['orange'], mew=1.4, zorder=6)
    ax.plot([cm[0]], [cm[1]], 'x', ms=10, mew=2.2, color=C['red'], zorder=8)
    ax.plot([cc[0]], [cc[1]], 'P', ms=10, color='#3f8a50', zorder=8)
    S.tag(ax, cm, '顶点均值中心　覆盖半径 %.2f m > 19.5 m' % rm, color=C['red'], dx=0, dy=-26)
    S.tag(ax, cc, '最小包围圆　半径 %.2f m ≤ 19.5 m' % rc, color='#3f8a50', dx=-14, dy=30)
    ax.set_aspect('equal')
    ax.set_xlim(-23.5, 40.5); ax.set_ylim(-30.5, 33.5)
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values(): sp.set_visible(False)
    ax.set_title('(a) 7.2 的机理（大纲给的算例）', pad=9)
    note_a = '实测 390 次局部清除：最小包围圆 100% 更小，其中 7.7%\n把"不可直接清除"变成"可直接清除"（每局少 7 次动作）'

    # ---- (b) 四条改动的配对效果 ----
    ax = axes[1]
    items = []
    for tag, r in ST.items():
        for q in ('q3', 'q4'):
            if q in r: items.append((tag.split(' ')[0] + ('・问题三' if q == 'q3' else '・问题四'), r[q]))
    items = items[::-1]
    y = np.arange(len(items))
    for i, (lab, d) in enumerate(items):
        good = d['hi'] < 0
        col = C['blue'] if good else C['ink2']
        ax.plot([d['lo'], d['hi']], [i, i], '-', color=col, lw=3.0, solid_capstyle='round', zorder=4)
        ax.plot([d['mean']], [i], 'o', ms=9, color=col, zorder=5)
        ax.text(d['hi']+.6, i, '%+.2f s　更快 %d/%d' % (d['mean'], d['faster'], d['n']),
                va='center', fontsize=9, color=C['ink'])
    ax.axvline(0, color=C['ink2'], lw=1.2)
    ax.set_yticks(y); ax.set_yticklabels([lab for lab, _ in items], fontsize=9.2)
    ax.set_xlabel('相对基线的配对差 / s（负值 = 更快，横线为 95% bootstrap 区间）')
    ax.set_xlim(-14, 30)
    ax.grid(True, axis='x'); ax.set_axisbelow(True)
    for sp in ('top','right','left'): ax.spines[sp].set_visible(False)
    ax.set_title('(b) 四条改动的配对效果（90 局）', pad=9)
    note_b = ('蓝色 = 区间不跨 0，采用；灰色 = 点估计更慢或区间跨 0，按大纲的验收口径不采用。\n'
              '7.3 那一行是"在 7.2 之上的增量"：时间中性，但每局少 3.3 次请求（-1.0%）。\n'
              '7.2 最小包围圆　7.3 补测点记账　7.4 问题三七点环　7.5 完整服务代价的滚动路线')

    # ---- (c) 方案八的验收 ----
    ax = axes[2]
    x = np.arange(2); w = .26
    for i, (lab, col) in enumerate((('方案七', '#8fbaea'), ('方案八 开发集', C['blue']), ('方案八 留出集', '#3f8a50'))):
        vals = [DEV[k][0] if i == 0 else (DEV[k][1] if i == 1 else HOLD[k]) for k in ('问题三', '问题四')]
        b = ax.bar(x+(i-1)*w, vals, width=w*.9, color=col, label=lab)
        for r, v in zip(b, vals):
            ax.text(r.get_x()+r.get_width()/2, v+8, '%.1f' % v, ha='center', fontsize=8.4, color=C['ink2'])
    ax.set_xticks(x); ax.set_xticklabels(['问题三', '问题四'])
    ax.set_ylabel('每源平均定位清除时间 / s'); ax.set_ylim(0, 640)
    ax.grid(True, axis='y'); ax.set_axisbelow(True)
    for sp in ('top','right'): ax.spines[sp].set_visible(False)
    ax.legend(loc='upper left', fontsize=8.8)
    ax.set_title('(c) 方案八 = 方案七 + 7.2 + 7.3', pad=9)
    note_c = ('留出集 seed 31337/90210 本轮之前从未跑过，不参与任何选择。\n'
              '180 局压力测试：未全清 0 局，每源 660 s。覆盖网与保证层未改动。')

    for xf, note in ((.055, note_a), (.375, note_b), (.735, note_c)):
        fig.text(xf, .035, note, fontsize=8.8, color=C['ink2'], linespacing=1.7, va='bottom')
    fig.suptitle('图 34　算法修订大纲的逐条验收：两条采用、两条未通过', fontsize=13.5, color=C['ink'], y=.985)
    print('已输出：', S.save(fig, '图34_大纲修订的验收'))
