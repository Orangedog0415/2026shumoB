"""图 17：四个版本在训练集与两个验证集上的每源平均定位清除时间。

三批案例都由 方案四_实验台.py 的 cases(seed) 生成（N=10/13/16 各 10 局），训练集 seed=1，
验证集 A/B 为 seed=202/777，参数只在训练集上标定过，验证集从未参与调参。
问题三的数字来自各版本的运行输出（方案六、七未改动问题三，沿用方案四）。
运行：python 图17_各版本每源平均时间.py   输出：figures/图17_各版本每源平均时间.pdf / .png
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
Q3 = {'方案一': (450.8, 448.3, 447.5), '方案四': (300.5, 305.8, 300.7),
      '方案六': (300.5, 305.8, 300.7), '方案七': (300.5, 305.8, 300.7)}
SH = ['#bcd6f2', '#8fbaea', '#5d9ae1', C['blue']]

if __name__ == '__main__':
    S.use_style()
    fig, axes = plt.subplots(1, 2, figsize=(12.6, 5.2), gridspec_kw=dict(wspace=.24))
    x = np.arange(3); w = .2
    for ax, which in zip(axes, ('问题三', '问题四')):
        for i, v in enumerate(R.VER):
            vals = Q3[v] if which == '问题三' else [R.mean_t(v, s) for s in R.SEEDS]
            b = ax.bar(x+(i-1.5)*w, vals, width=w*.92, color=SH[i], label=v)
            for r, val in zip(b, vals):
                ax.text(r.get_x()+r.get_width()/2, val+7, '%.0f' % val, ha='center', fontsize=8.2, color=C['ink2'])
        ax.set_xticks(x); ax.set_xticklabels([R.SEED_NAME[s] for s in R.SEEDS])
        ax.set_ylabel('每源平均定位清除时间 / s')
        ax.set_ylim(0, (1100 if which == '问题四' else 520))
        ax.grid(True, axis='y'); ax.set_axisbelow(True)
        for sp in ('top','right'): ax.spines[sp].set_visible(False)
        ax.set_title(which + ('（方案六、七沿用方案四，故三者相同）' if which == '问题三' else ''), pad=9)
    axes[1].legend(loc='upper right', ncol=2)
    axes[1].text(.02, .96, '方案七较方案一 -46%，较方案四 -23%', transform=axes[1].transAxes,
                 fontsize=9.5, color=C['ink2'], va='top')
    fig.suptitle('图 17　四个版本的每源平均定位清除时间（本地仿真，非官方成绩）', fontsize=13.5, color=C['ink'], y=1.0)
    print('已输出：', S.save(fig, '图17_各版本每源平均时间'))
