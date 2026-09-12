"""图 23：试过但没有采用的改动——每一条都在同一批案例上量过，负结果也是结果。

横轴是问题四每源平均时间相对当轮基线的变化，正值表示更慢。柱子是训练集，两个空心点是两个验证集
（部分改动当时只在训练集上测过，就只有柱子）。这些条目对应的脚本与输出都在仓库里，可复跑：
  3.3a  两步前瞻（beam）             code/experiments/方案四_实验台.py（select='beam'）
  5.1   更强的路线启发式             code/experiments/方案五_5.1_路线算法对比.py
  5.3b  regret-2 插入构造路线        code/experiments/方案五_5.3_服务簇与regret.py
  6.1   GT06 的 37 点分级同心环网    code/experiments/方案六_6.1_GT06分级环网.py
  6.2   自适应补测（粗探 + 加密）     code/experiments/方案六_6.2_自适应补测.py
  6.3   顺路复测加可检测性门槛        code/experiments/方案六_6.3_可检测锥选点.py
运行：python 图23_试过但未采用的改动.py   输出：figures/图23_试过但未采用的改动.pdf / .png
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

# (标签, 训练集 Δ%, [验证集 Δ%], 一句话原因)
ITEMS = [
    ('5.1　更强的路线启发式\n（2-opt + Or-opt + 双桥多起点）', 0.0, [], '固定点集上的巡回已是局部最优'),
    ('6.3e　顺路复测加门槛 $\\tau$=0.7', 3.8, [5.5, 3.2], '顺路复测边际成本只有 6 s，期望收益恒为正'),
    ('3.3a　任务选择改两步前瞻 beam', 4.2, [], '打乱了本已接近最优的覆盖巡回'),
    ('5.3b　regret-2 插入构造路线', 4.0, [], '与联合重规划重复，且更贪心'),
    ('6.2a　自适应补测（子集粗探）', 14.3, [18.7, 18.6], '空频道永远"未解"，前提不成立'),
    ('6.1　GT06 的 37 点分级环网', 15.5, [16.1, 16.6], '同心环族要多 10 个点、多走 4 km'),
    ('6.2c　自适应补测（七点网粗探）', 16.1, [20.4, 21.5], '同上，且粗探网不是认证网的子集'),
    ('6.3f　顺路复测加门槛 $\\tau$=0.9', 53.5, [52.5, 53.8], '几乎禁掉了所有复测'),
]

if __name__ == '__main__':
    S.use_style()
    fig, ax = plt.subplots(figsize=(11.6, 6.4))
    ITEMS.sort(key=lambda r: r[1])
    y = np.arange(len(ITEMS))
    vals = [r[1] for r in ITEMS]
    cols = [C['red'] if v > 8 else (C['orange'] if v > 0.5 else C['ink2']) for v in vals]
    ax.barh(y, vals, color=cols, height=.58, zorder=3)
    for i, (lab, v, vv, why) in enumerate(ITEMS):
        if vv:
            ax.plot(vv, [i]*len(vv), 'o', ms=6, mfc='none', mec=C['ink2'], mew=1.3, zorder=6)
        ax.text(max([v]+vv)+1.6, i, ('%+.1f%%' % v) if v else '0.0%', va='center',
                fontsize=9.5, color=C['ink'], zorder=5)
        ax.text(-1.0, i, why, ha='right', va='center', fontsize=8.6, color=C['ink2'], zorder=5)
    ax.axvline(0, color=C['ink2'], lw=1.0)
    ax.set_yticks(y); ax.set_yticklabels([r[0] for r in ITEMS], fontsize=9.2)
    ax.set_xlabel('问题四每源平均时间相对当轮基线的变化 / %（正值 = 更慢）')
    ax.set_xlim(-27, 60); ax.grid(True, axis='x'); ax.set_axisbelow(True)
    for sp in ('top','right','left'): ax.spines[sp].set_visible(False)
    ax.set_title('图 23　试过但没有采用的改动：八条负结果', fontsize=13.5, pad=12)
    fig.text(.5, -.015, '柱 = 训练集，空心点 = 两个验证集；左侧灰字是不采用的原因。'
             '另有一条不在图上：按抽样做的集合覆盖网在稠密复验里漏测 641 组，属于"不能作为保证"，不是慢。',
             ha='center', fontsize=9, color=C['ink2'])
    print('已输出：', S.save(fig, '图23_试过但未采用的改动'))
