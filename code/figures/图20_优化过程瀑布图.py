"""图 20：问题四从交接基线到方案七，每一轮各省下多少秒。

起点是交接版基线（方案一，977.4 s/源），终点是方案七（529.1 s/源），中间四段是四轮优化。
每一段里列出了这一轮实际生效的改动；段内各条改动的单独消融见 docs/review/ 下对应的迭代记录
（方案四_迭代记录.md、方案五_5x实验与方案六.md、方案六_6x实验与方案七.md），本图只做累计口径，
避免把"单独测出来的增益"直接相加——它们并不可加。
数字为问题四训练集 30 局的每源平均时间，本地仿真。
运行：python 图20_优化过程瀑布图.py   输出：figures/图20_优化过程瀑布图.pdf / .png
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

STEPS = [
    ('方案一\n交接基线', 977.4, None),
    ('方案三', 745.0, '每点扫完所有未定频道（批量扫描）\n顺路清除阈值 x 与门槛 $r_{ok}$\n覆盖完成后集中清除 + 顺带补测'),
    ('方案四', 688.9, '3.1 策略参数贝叶斯优化标定\n3.2 覆盖网换 h=950 偏移格网\n3.3b 集中清除顺序改 ALNS'),
    ('方案六', 553.3, '5.2 可认证非规则三角网（25.1→17.8 km）\nB 联合重规划　C 计数提前停\n5.3a 待清源表示成服务簇'),
    ('方案七', 529.1, '6.4 覆盖网再压缩：27 点 → 25 点\n（同心环枚举给退火找新起点）'),
]

if __name__ == '__main__':
    S.use_style()
    fig, ax = plt.subplots(figsize=(12.8, 7.0))
    fig.subplots_adjust(left=.30, right=.97, top=.90, bottom=.19)
    vals = [v for _, v, _ in STEPS]
    rows, labels, kinds = [], [], []
    for i, (lab, v, why) in enumerate(STEPS):
        rows.append(v); labels.append(lab.replace('\n', ' ')); kinds.append('v')
        if i+1 < len(STEPS):
            rows.append(None); labels.append(STEPS[i+1][2]); kinds.append('d')
    y = np.arange(len(rows))[::-1]
    vi = 0
    for k, (r, lab, kind) in enumerate(zip(rows, labels, kinds)):
        yy = y[k]
        if kind == 'v':
            col = C['blue'] if vi in (0, len(STEPS)-1) else '#8fbaea'
            ax.barh(yy, vals[vi], height=.56, color=col, zorder=4)
            ax.text(vals[vi]+12, yy, '%.1f s' % vals[vi], va='center', fontsize=11, color=C['ink'], zorder=6)
            vi += 1
        else:
            top, bot = vals[vi-1], vals[vi]
            ax.barh(yy, top-bot, left=bot, height=.40, color=C['orange'], alpha=.9, zorder=4)
            ax.plot([top, top], [yy-.30, yy+.72], ls=(0,(3,3)), color=C['ink2'], lw=.8, zorder=3)
            ax.plot([bot, bot], [yy-.72, yy+.30], ls=(0,(3,3)), color=C['ink2'], lw=.8, zorder=3)
            ax.text(top+12, yy, '-%.1f s　(-%.1f%%)' % (top-bot, 100*(top-bot)/top),
                    va='center', fontsize=10, color=C['orange'], zorder=6)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9.2)
    for tick, kind in zip(ax.get_yticklabels(), kinds):
        tick.set_fontsize(11 if kind == 'v' else 8.8)
        tick.set_color(C['ink'] if kind == 'v' else C['ink2'])
        tick.set_linespacing(1.5)
    ax.set_xlabel('问题四 每源平均定位清除时间 / s')
    ax.set_xlim(0, 1175); ax.set_ylim(-.8, len(rows)-.2)
    ax.grid(True, axis='x'); ax.set_axisbelow(True)
    for sp in ('top','right','left'): ax.spines[sp].set_visible(False)
    ax.tick_params(axis='y', length=0)
    ax.set_title('图 20　问题四的优化过程：977.4 s → 529.1 s（累计 -45.9%）', fontsize=13.5, pad=14)
    fig.text(.30, .025, '橙色 = 该轮省下的时间，左侧文字是这一轮实际生效的改动。'
             '各条改动的单独消融见 docs/review/ 下的迭代记录，单独增益不可直接相加。\n'
             '问题三同期由 450.8 s 降到 300.5 s（-33.3%），方案六、七未改动问题三。',
             fontsize=9, color=C['ink2'], linespacing=1.6)
    print('已输出：', S.save(fig, '图20_优化过程瀑布图'))
