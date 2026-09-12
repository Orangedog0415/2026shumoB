"""图 33：与外部方案（li2396803/cumcm2026，MIT）的正面对照——常规案例上打平，压力测试上分开。

对照口径：同一批案例（我们的 cases(seed)）、同一套误差场、同一套时间常数，示向度都保留两位小数。
外部方案用其 v2 策略（滚动时域重优化 + 朝向贝叶斯信念 + 风险可控自适应侦察，θ=0 严格档），
侦察点集用其求解出的问题三 8 点 / 问题四 19 点。
(a)(b) 两张问题四侦察点集的"可漏测区"：以 180° 为中性色画出每个位置的最大方位间隔。
    外部 19 点网有 1.9% 的面积存在漏测方向（稠密位置×朝向复验 3834 组漏测），我们的 25 点网为 0。
(c) 常规随机案例（90 局）上两边的每源平均时间——问题三他们快 6.5%，问题四基本打平。
(d) 我们的 180 局保证性压力测试——这里才分开：方案七 180/180 全清，外部 v2 136/180，
    且 40/44 次失败集中在"边界朝外的定向源"这一组，正是零漏测证书要管的地方。
运行：python 图33_外部方案对照.py   输出：figures/图33_外部方案对照.pdf / .png
"""
import json, math, importlib.util
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
G1 = _m('G1', HERE/'图12_覆盖网证书验证.py')
L = _m('L', HERE.parent/'experiments'/'方案四_实验台.py')
D = json.load(open(HERE.parent/'experiments'/'results'/'外部方案对照.json', encoding='utf-8'))
COV = json.load(open(HERE.parent/'external'/'li2396803'/'cover_points.json'))
P4_EXT = [tuple(map(float, q)) for q in
          {round(t['spacing']): t['points_ordered'] for t in COV['problem4_tradeoff']}[1000]]

def polar(ax, net, title):
    A, RR, Z = G1.gap_field(net)
    AA, RRm = np.meshgrid(np.append(A, 2*math.pi), RR)
    Zc = np.concatenate([Z, Z[:, :1]], axis=1)
    pc = ax.pcolormesh(AA, RRm, Zc, cmap='RdBu_r', vmin=0, vmax=360, shading='nearest')
    ax.set_yticklabels([]); ax.set_xticklabels([]); ax.grid(False)
    ax.set_title(title, pad=14, fontsize=10.5)
    ax.text(.5, -.11, '最大方位间隔 %.1f°　可漏测面积 %.1f%%' % (Z.max(), 100*float((Z >= 180).mean())),
            transform=ax.transAxes, ha='center', va='top', fontsize=9, color=C['ink2'])
    return pc

if __name__ == '__main__':
    S.use_style()
    fig = plt.figure(figsize=(13.6, 9.2))
    gs = fig.add_gridspec(2, 3, width_ratios=[1, 1, .05], height_ratios=[1, 1.05],
                          hspace=.34, wspace=.26)

    ax = fig.add_subplot(gs[0, 0], projection='polar')
    pc = polar(ax, P4_EXT, '(a) 外部方案 问题四侦察点集（19 点 / 18.0 km）')
    ax = fig.add_subplot(gs[0, 1], projection='polar')
    polar(ax, L.NET4_V7(), '(b) 方案七 覆盖网（25 点 / 17.5 km）')
    cax = fig.add_subplot(gs[0, 2])
    cb = fig.colorbar(pc, cax=cax, ticks=[0, 90, 180, 270, 360])
    cb.set_label('最大方位间隔 / °（180° 为分界）', fontsize=9); cb.outline.set_edgecolor(C['edge'])

    # (c) 常规案例
    ax = fig.add_subplot(gs[1, 0])
    groups = [('问题三\n90 局', 'A_q3', '方案四'), ('问题四\n90 局', 'A_q4', '方案七')]
    x = np.arange(len(groups)); w = .34
    for i, (who, col) in enumerate((('ours', C['blue']), ('ext', C['orange']))):
        vals = [D[k][mine if who == 'ours' else '外部 v2']['per'] for _, k, mine in groups]
        b = ax.bar(x+(i-.5)*w, vals, width=w*.9, color=col,
                   label='我们（方案四 / 方案七）' if who == 'ours' else '外部方案 v2')
        for r, v in zip(b, vals):
            ax.text(r.get_x()+r.get_width()/2, v+7, '%.1f' % v, ha='center', fontsize=9, color=C['ink2'])
    for i, (_, k, mine) in enumerate(groups):
        d = 100*(D[k]['外部 v2']['per']/D[k][mine]['per']-1)
        ax.text(i, max(D[k]['外部 v2']['per'], D[k][mine]['per'])+42, '外部 %+.1f%%' % d,
                ha='center', fontsize=10, color=C['red' if d > 0 else 'orange'])
        ext = D[k]['外部 v2']; our = D[k][mine]
        ax.text(i, -70, '按源数 10 / 13 / 16\n我们 %s\n外部 %s'
                % (' / '.join('%.0f' % our['byN'][n] for n in ('10', '13', '16')),
                   ' / '.join('%.0f' % ext['byN'][n] for n in ('10', '13', '16'))),
                ha='center', va='top', fontsize=8.6, color=C['ink2'], linespacing=1.5)
    ax.set_xticks(x); ax.set_xticklabels([g[0] for g in groups])
    ax.set_ylabel('每源平均定位清除时间 / s'); ax.set_ylim(0, 640)
    ax.grid(True, axis='y'); ax.set_axisbelow(True)
    for sp in ('top','right'): ax.spines[sp].set_visible(False)
    ax.legend(loc='upper left', fontsize=9)
    ax.set_title('(c) 常规随机案例：问题三他们更快，问题四打平', pad=9)

    # (d) 压力测试
    ax = fig.add_subplot(gs[1, 1])
    rows = D['C_stress']
    keys = ['方案七', '外部 v2']
    full = [100*sum(1 for r in rows[k] if r['ok'])/len(rows[k]) for k in keys]
    b = ax.bar([0, 1], full, width=.5, color=[C['blue'], C['orange']])
    for r, v, k in zip(b, full, keys):
        ax.text(r.get_x()+r.get_width()/2, v+1.6, '%.1f%%' % v, ha='center', fontsize=11, color=C['ink'])
        nf = sum(1 for x in rows[k] if not x['ok'])
        ax.text(r.get_x()+r.get_width()/2, 6, '未全清 %d 局' % nf, ha='center', fontsize=9.5, color=C['white'])
    lay = {}
    for r in rows['外部 v2']:
        if not r['ok']: lay[r['layout']] = lay.get(r['layout'], 0) + 1
    ax.set_xticks([0, 1]); ax.set_xticklabels(['方案七', '外部方案 v2'])
    ax.set_ylabel('全清局数占比 / %'); ax.set_ylim(0, 118)
    ax.grid(True, axis='y'); ax.set_axisbelow(True)
    for sp in ('top','right'): ax.spines[sp].set_visible(False)
    ax.set_title('(d) 180 局保证性压力测试：证书在这里兑现', pad=9)
    S.note(ax, '外部方案 %d 次未全清里 %d 次在"边界朝外的定向源"这一组\n'
               '（源在半径 1700~1800 m、朝向指向圆外）——正是 (a) 里红色区域对应的情形'
               % (sum(1 for x in rows['外部 v2'] if not x['ok']), lay.get('边界朝外', 0)), loc='lower left')

    fig.suptitle('图 33　与外部方案（li2396803/cumcm2026）的正面对照', fontsize=13.5, color=C['ink'], y=.98)
    print('已输出：', S.save(fig, '图33_外部方案对照'))
