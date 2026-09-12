"""图 15：同一局、同一误差场下，方案一与方案七的机器狗轨迹。

案例取训练集第 21 局（N=16，问题四混合源）。灰线是行进轨迹，圆点是检测动作，方块是清除动作，
星号是干扰源真实位置（定向源画出朝向箭头）。两张图的坐标范围完全一致，可以直接比长度。
方案一"发现一个就去清一个"，于是在覆盖点与源之间来回折返；方案七每一步把覆盖点和可清源放在一起重排，
再加上计数提前停（找齐 16 个就不再走剩下的覆盖点），轨迹明显更短。
运行：python 图15_单局轨迹对比.py   输出：figures/图15_单局轨迹对比.pdf / .png
"""
import math, importlib.util
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib import font_manager
HERE = Path(__file__).resolve().parent
try: font_manager.fontManager.addfont('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
except Exception: pass
def _m(n, f):
    s = importlib.util.spec_from_file_location(n, str(f)); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
S = _m('S', HERE/'_绘图样式.py'); R = _m('R', HERE/'_结果数据.py'); C = S.C

if __name__ == '__main__':
    S.use_style()
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 6.4))
    srcs = R.TRAJ['sources']
    for ax, tag in zip(axes, ('方案一', '方案七')):
        d = R.TRAJ[tag]; log = d['log']
        S.field_axes(ax, 1800., pad=520.)
        xs = [p[0] for p, _, _ in log]; ys = [p[1] for p, _, _ in log]
        ax.plot(xs, ys, '-', color='#b9b8b2', lw=1.0, zorder=3)
        mx = [p for p, k, v in log if k == 'measure']
        cx = [p for p, k, v in log if k == 'clear']
        ax.plot([p[0] for p in mx], [p[1] for p in mx], 'o', ms=3.2, color=C['blue'], zorder=5, label='检测动作')
        ax.plot([p[0] for p in cx], [p[1] for p in cx], 's', ms=4.6, mfc='none', mec=C['orange'], mew=1.2, zorder=6, label='清除动作')
        for s in srcs:
            g = s['g']
            ax.plot([g[0]], [g[1]], '*', ms=11, color=C['red'], zorder=7)
            if s['u']:
                ax.annotate('', xy=(g[0]+240*s['u'][0], g[1]+240*s['u'][1]), xytext=(g[0], g[1]),
                            arrowprops=dict(arrowstyle='-|>', color=C['red'], lw=1.1, alpha=.8), zorder=7)
        ax.plot([0], [0], 's', ms=8, mfc=C['white'], mec=C['ink'], mew=1.6, zorder=8)
        ax.set_title('%s：总时长 %.0f s，每源 %.0f s' % (tag, d['time'], d['time']/d['n']), pad=9)
        ax.set_xlabel('x / m')
        S.note(ax, '行进 %.0f s　检测 %.0f s　切换 %.0f s　清除 %.0f s\n动作 %d 次'
                   % (d['moves'], d['detect'], d['switch'], d['cleartime'], d['actions'])
                   + '\n密集的橙色方块 = 75×3 有限兜底逐格试清', loc='lower left')
    axes[0].set_ylabel('y / m')
    h, lb = axes[0].get_legend_handles_labels()
    fig.legend(h + [plt.Line2D([], [], marker='*', ls='', color=C['red'], ms=11)],
               lb + ['干扰源真实位置（箭头 = 定向方向）'], loc='lower center', ncol=3,
               bbox_to_anchor=(.5, -.045), handletextpad=.6, columnspacing=2.4)
    fig.suptitle('图 15　同一局（N=16 混合源）下方案一与方案七的轨迹对比', fontsize=13.5, color=C['ink'], y=1.0)
    print('已输出：', S.save(fig, '图15_单局轨迹对比'))
