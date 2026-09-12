"""图 21：策略参数的敏感性——绕行阈值 x × 门槛 r_ok 的扫描，以及贝叶斯优化的标定过程。

(a) 问题三在 x（顺路清除的绕行距离上限）与 r_ok（去清之前要求的区域外接半径上限）两维上的扫描，
    其余参数固定为方案四的标定值。底色是训练集 30 局的每源平均时间。
(b) 方案四·3.1 用贝叶斯优化（GP + EI）在 7 维参数空间做的 51 次评估，纵轴是归一化综合得分
    （问题三、四各自相对基线的比值取平均，越小越好），可以看到 20 次左右就基本收敛。
扫描结果会缓存到 results/图21_参数扫描.json，第二次运行直接读缓存。
运行：python 图21_参数敏感性.py（首次约 5~10 分钟）  输出：figures/图21_参数敏感性.pdf / .png
"""
import json, copy, importlib.util, statistics as st, re
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
L = _m('L', HERE.parent/'experiments'/'方案四_实验台.py'); J = L.J
CACHE = HERE.parent/'experiments'/'results'/'图21_参数扫描.json'
XS = [350., 450., 530., 620., 720., 850.]
RS = [70., 90., 110., 130., 160., 200.]

def sweep():
    if CACHE.exists(): return json.load(open(CACHE, encoding='utf-8'))
    net3 = L.NET3(); cases = L.cases(1)[0]
    Z = []
    for r_ok in RS:
        row = []
        for x in XS:
            C_ = L.cfg(**{**L.CFG4, 'x': x, 'r_ok': r_ok})
            row.append(st.mean(L.solve(J.World(copy.deepcopy(s), i), False, net3, C_).time/len(s)
                               for i, s in enumerate(cases)))
            print('  x=%.0f r_ok=%.0f -> %.1f' % (x, r_ok, row[-1]), flush=True)
        Z.append(row)
    json.dump(dict(XS=XS, RS=RS, Z=Z), open(CACHE, 'w', encoding='utf-8'))
    return dict(XS=XS, RS=RS, Z=Z)

def bo_trace():
    txt = (HERE.parent/'experiments'/'results'/'方案四_参数标定输出.txt').read_text(encoding='utf-8')
    return [float(m) for m in re.findall(r'eval\s+([0-9.]+)', txt)]

if __name__ == '__main__':
    S.use_style()
    d = sweep(); Z = np.array(d['Z'])
    fig, axes = plt.subplots(1, 2, figsize=(12.8, 5.2), gridspec_kw=dict(width_ratios=[1.1, 1], wspace=.30))

    ax = axes[0]
    pc = ax.pcolormesh(np.arange(len(XS)+1), np.arange(len(RS)+1), Z, cmap='Blues', shading='flat')
    for i in range(len(RS)):
        for j in range(len(XS)):
            ax.text(j+.5, i+.5, '%.0f' % Z[i, j], ha='center', va='center', fontsize=8.6,
                    color=C['white'] if Z[i, j] > Z.min()+.6*(Z.max()-Z.min()) else C['ink'])
    bi = np.unravel_index(Z.argmin(), Z.shape)
    ax.add_patch(plt.Rectangle((bi[1], bi[0]), 1, 1, facecolor='none', edgecolor=C['red'], lw=2.4, zorder=6))
    ji = (RS.index(130.), XS.index(530.))
    ax.add_patch(plt.Rectangle((ji[1], ji[0]), 1, 1, facecolor='none', edgecolor=C['orange'], lw=2.0, ls=(0,(3,2)), zorder=6))
    cb = fig.colorbar(pc, ax=ax, pad=.02, fraction=.046); cb.outline.set_edgecolor(C['edge'])
    cb.set_label('问题三 每源平均时间 / s', fontsize=9.5)
    ax.set_xticks(np.arange(len(XS))+.5); ax.set_xticklabels(['%.0f' % v for v in XS])
    ax.set_yticks(np.arange(len(RS))+.5); ax.set_yticklabels(['%.0f' % v for v in RS])
    ax.set_xlabel('绕行阈值 $x$ / m'); ax.set_ylabel('门槛 $r_{ok}$ / m')
    ax.set_title('(a) $x\\times r_{ok}$ 扫描（问题三训练集）', pad=9)
    note_a = ('红框 = 本扫描的最优 %.1f s（x=350, $r_{ok}$=110）；橙虚框 = 方案四采用的 (530, 130)，'
              '差 %.1f s（%.1f%%）\n整张表的极差只有 %.1f s（%.1f%%），说明这两个参数在合理范围内都不敏感'
              % (Z.min(), Z[ji]-Z.min(), 100*(Z[ji]/Z.min()-1), Z.max()-Z.min(), 100*(Z.max()/Z.min()-1)))

    ax = axes[1]
    tr = bo_trace()
    ax.plot(range(1, len(tr)+1), tr, 'o', ms=4.5, color='#8fbaea', label='单次评估')
    ax.plot(range(1, len(tr)+1), np.minimum.accumulate(tr), '-', color=C['blue'], lw=2.0, label='当前最优')
    ax.axhline(1.0, color=C['ink2'], lw=1.1, ls=(0,(4,3)))
    S.tag(ax, (len(tr)*.55, 1.0), '方案三基线', dy=13)
    ax.set_xlabel('评估次数'); ax.set_ylabel('归一化综合得分（越小越好）')
    ax.grid(True); ax.set_axisbelow(True)
    for sp in ('top','right'): ax.spines[sp].set_visible(False)
    ax.legend(loc='upper right')
    ax.set_title('(b) 3.1 贝叶斯优化的 %d 次评估' % len(tr), pad=9)
    note_b = '7 个参数一起标定；约 20 次评估后不再明显下降，最优得分 %.3f，\n对应方案四采用的参数（取整后写进 CFG4）' % min(tr)

    fig.subplots_adjust(bottom=.26)
    fig.text(.055, .015, note_a, fontsize=9, color=C['ink2'], linespacing=1.7)
    fig.text(.565, .015, note_b, fontsize=9, color=C['ink2'], linespacing=1.7)
    fig.suptitle('图 21　策略参数的敏感性与标定过程', fontsize=13.5, color=C['ink'], y=1.0)
    print('已输出：', S.save(fig, '图21_参数敏感性'))
