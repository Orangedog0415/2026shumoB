"""图 18：各版本在 N=10 / 13 / 16 三档源数下的表现。

每档 10 局（训练集）。注意每源平均时间随源数**下降**：因为"证明剩下的频道是空的"这件事的成本
几乎与源数无关，源越少，这份固定成本被摊到的源就越少。方案六、七里的计数提前停只在 N=16 时触发
（已清除 + 已发现达到 16 就不再走剩下的覆盖点），所以 N=16 一档的改进最明显。
运行：python 图18_按源数分的表现.py   输出：figures/图18_按源数分的表现.pdf / .png
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
SH = ['#bcd6f2', '#8fbaea', '#5d9ae1', C['blue']]
import statistics as st

if __name__ == '__main__':
    S.use_style()
    fig, axes = plt.subplots(1, 2, figsize=(12.6, 5.2), gridspec_kw=dict(wspace=.26))
    x = np.arange(3); w = .2
    ax = axes[0]
    for i, v in enumerate(R.VER):
        rows = R.t(v, '1')
        vals = [st.mean(rows[:10]), st.mean(rows[10:20]), st.mean(rows[20:])]
        b = ax.bar(x+(i-1.5)*w, vals, width=w*.92, color=SH[i], label=v)
        for r, val in zip(b, vals):
            ax.text(r.get_x()+r.get_width()/2, val+9, '%.0f' % val, ha='center', fontsize=8.2, color=C['ink2'])
    ax.set_xticks(x); ax.set_xticklabels(['N = 10', 'N = 13', 'N = 16'])
    ax.set_ylabel('每源平均定位清除时间 / s'); ax.set_ylim(0, 1250)
    ax.grid(True, axis='y'); ax.set_axisbelow(True)
    for sp in ('top','right'): ax.spines[sp].set_visible(False)
    ax.legend(loc='upper right', ncol=2)
    ax.set_title('(a) 每源平均时间（问题四训练集）', pad=9)

    ax = axes[1]
    for i, v in enumerate(R.VER):
        rows = R.t(v, '1')
        vals = [st.mean(rows[:10])*10, st.mean(rows[10:20])*13, st.mean(rows[20:])*16]
        ax.plot([10, 13, 16], vals, '-o', color=SH[i], lw=2.0, ms=7, label=v)
        for xx, val in zip((10, 13, 16), vals):
            ax.text(xx, val+190, '%.0f' % val, ha='center', fontsize=8.4, color=C['ink2'])
    ax.set_xticks([10, 13, 16]); ax.set_xlabel('干扰源个数 N')
    ax.set_ylabel('单局总时长 / s'); ax.set_ylim(0, 12500)
    ax.grid(True); ax.set_axisbelow(True)
    for sp in ('top','right'): ax.spines[sp].set_visible(False)
    ax.set_title('(b) 单局总时长：源越多，总时长才涨得慢', pad=9)
    S.note(ax, '每源平均随 N 下降，但单局总时长随 N 上升——\n"判空成本"基本固定，"清除成本"随 N 线性增加',
           loc='lower right')

    fig.suptitle('图 18　按源数分档的表现', fontsize=13.5, color=C['ink'], y=1.0)
    print('已输出：', S.save(fig, '图18_按源数分的表现'))
