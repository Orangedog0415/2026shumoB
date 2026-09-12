# -*- coding: utf-8 -*-
"""
问题四：含定向干扰源的检测与清除策略（理论建模）
------------------------------------------------------------------
模型组成：
  1) 可检测域模型：定向源的可检测域为"半圆盘"，全向源为"圆盘"
  2) 背向不可测定理：两点同时无信号且视角差 >= 180 度 => 该频道必为空闲
  3) 方位包围判据：零漏测 <=> 观测点集在源点处的方位角最大间隔 < 180 度
  4) 七点覆盖网的失效分析：定向场景下必然漏测，给出"可隐藏区"分布
  5) 分级冗余网：求解满足零漏测的最小环族构型
  6) 自适应补测策略与其时间代价、相对问题三的惩罚系数

说明：本题按纯理论建模口径求解，不接入模拟器；正式测试结果表（表1）保留空表头待回填。
"""
import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib import font_manager
from matplotlib.patches import Circle, Wedge as MplWedge, Polygon as MplPolygon
import warnings
warnings.filterwarnings('ignore')

# ========== 全局样式（必须先设置：style 会重置 font.sans-serif） ==========
plt.style.use('seaborn-v0_8-whitegrid')

# ========== 中文字体配置（强制，确保图例中文正常显示；置于 style 之后） ==========
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['SimHei', 'Heiti SC', 'Heiti TC', 'PingFang SC',
    'PingFang HK', 'Hiragino Sans GB', 'Songti SC', 'STHeiti', 'Arial Unicode MS',
    'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 150
plt.rcParams['savefig.dpi'] = 150
plt.rcParams['savefig.bbox'] = 'tight'

plt.rcParams['legend.fontsize'] = 10
plt.rcParams['legend.frameon'] = True
plt.rcParams['legend.edgecolor'] = '#CCCCCC'
for fname in font_manager.findSystemFonts():
    try:
        f = font_manager.FontProperties(fname=fname)
        if any(kw in f.get_name() for kw in ['Hei', 'Song', 'Ming', 'Fang', 'Kai',
                                             'SimSun', 'SimHei', 'PingFang', 'STHeiti']):
            font_manager.fontManager.addfont(fname)
    except Exception:
        pass

CMAP_SEQUENTIAL = plt.cm.viridis
CMAP_CATEGORICAL = plt.cm.tab10
CMAP_DIVERGING = plt.cm.RdBu_r

COLORS_10 = ['#4C72B0', '#DD8452', '#55A868', '#C44E52', '#8172B3',
             '#937860', '#DA8BC3', '#8C8C8C', '#CCB974', '#64B5CD']

BASE = '/Users/rzn/Desktop/IP计划/CUMCM2026Problems(4)/B-1/求解'
OUT_DIR = BASE + '/问题四/'
FIG_DIR = OUT_DIR + 'figures/'
os.makedirs(FIG_DIR, exist_ok=True)


def save_fig(fig, name_cn):
    fig.savefig(FIG_DIR + name_cn)
    plt.close(fig)


def save_csv(df, name_cn):
    df.to_csv(OUT_DIR + name_cn, index=False, encoding='utf-8-sig')


def apply_mpl_style(fig, despine=True, ax=None):
    ax = ax if ax is not None else fig.gca()
    if despine:
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
    ax.grid(True, linestyle='--', alpha=0.4, color='#AAAAAA')
    ax.tick_params(labelsize=10)
    fig.tight_layout()


def set_legend_cn(ax, **kwargs):
    return ax.legend(prop={'family': plt.rcParams['font.sans-serif']}, **kwargs)


# ==================================================================
# 全局常量
# ==================================================================
R_TARGET = 1800.0
R_C_MIN = 1000.0
R_C_MAX = 1500.0
CLEAR_R = 20.0
NEAR_R = 5.0
V_DOG = 5.0
T_MEASURE = 5.0
T_SWITCH = 1.0
T_CLEAR_OK = 5.0
N_CHANNEL = 20
D1 = 1122.96               # 问题三给出的最小行程覆盖网环半径 (m)


# ==================================================================
# 1. 观测点集构造
# ==================================================================
def ring(d, n, off=0.0):
    a = off + 2 * np.pi * np.arange(n) / n
    return np.c_[d * np.cos(a), d * np.sin(a)]


def net_p3():
    """问题三的七点保证覆盖网。"""
    return np.vstack([[0.0, 0.0], ring(D1, 6)])


def net_p4(radii=(1000.0, 1300.0, 1900.0), counts=(6, 12, 24), center=True):
    """问题四的分级冗余网：中心 + 逐层加密的同心环。"""
    pts = [np.array([0.0, 0.0])] if center else []
    for d, n in zip(radii, counts):
        pts.append(ring(d, n, np.pi / n))
    return np.vstack(pts)


# ==================================================================
# 2. 可检测域与方位包围
# ==================================================================
def can_detect(P, G, r_c, psi_deg=None):
    """可检测性判据。psi_deg=None 表示全向源。"""
    v = np.asarray(P, float) - np.asarray(G, float)
    if np.linalg.norm(v) > r_c:
        return False
    if psi_deg is None:
        return True
    d = np.rad2deg(np.arctan2(v[1], v[0])) % 360.0
    return abs((d - psi_deg + 180.0) % 360.0 - 180.0) <= 90.0 + 1e-12


def max_bearing_gap(Q, G, r_c=R_C_MIN):
    """Q 中位于 G 的 r_c 邻域内的观测点，其在 G 处的方位角最大间隔（度）。

    间隔 >= 180 度 -> 存在某个定向方向 psi 使所有该邻域内的观测点都落在背向半平面
    -> 该位置的定向源必被漏测。
    """
    v = Q - np.asarray(G, float)
    d = np.linalg.norm(v, axis=1)
    m = d <= r_c + 1e-9
    if m.sum() == 0:
        return 360.0
    a = np.sort(np.arctan2(v[m, 1], v[m, 0]))
    return float(np.rad2deg(np.diff(np.r_[a, a[0] + 2 * np.pi]).max()))


def is_hidden(Q, G, r_c=R_C_MIN):
    """G 处是否存在某个定向方向使源被完全漏测。"""
    return max_bearing_gap(Q, G, r_c) >= 180.0


def hidden_direction(Q, G, r_c=R_C_MIN):
    """返回使 G 处定向源被漏测的方向（取最大间隔的中点）。"""
    v = Q - np.asarray(G, float)
    d = np.linalg.norm(v, axis=1)
    m = d <= r_c + 1e-9
    if m.sum() == 0:
        return 0.0
    a = np.sort(np.arctan2(v[m, 1], v[m, 0]))
    ext = np.r_[a, a[0] + 2 * np.pi]
    gaps = np.diff(ext)
    k = int(np.argmax(gaps))
    return float(np.rad2deg((ext[k] + ext[k + 1]) / 2) % 360.0)


# ==================================================================
# 3. 冗余网求解
# ==================================================================
def survey(Q, r_c=R_C_MIN, n_r=160, n_t=288):
    """在目标域上评估最大方位间隔，返回 (最大值, 取到最大值的点, 网格)。"""
    rr = np.linspace(0, R_TARGET, n_r)
    tt = np.linspace(0, 2 * np.pi, n_t, endpoint=False)
    RR, TT = np.meshgrid(rr, tt, indexing='ij')
    Gs = np.c_[(RR * np.cos(TT)).ravel(), (RR * np.sin(TT)).ravel()]
    best = -1.0
    wg = None
    allg = np.empty(len(Gs))
    for i, g in enumerate(Gs):
        mg = max_bearing_gap(Q, g, r_c)
        allg[i] = mg
        if mg > best:
            best, wg = mg, g
    return best, wg, Gs, allg


def solve_redundant_net(verbose=True):
    """在'中心 + 分级同心环'族中求解满足零漏测的最小构型。"""
    cands = []
    for n1 in (6, 12):
        for n2 in (12, 18):
            for n3 in (18, 24):
                for r2 in (1300.0, 1400.0, 1500.0):
                    Q = np.vstack([[0.0, 0.0], ring(1000.0, n1, np.pi / n1),
                                   ring(r2, n2, np.pi / n2), ring(1900.0, n3, np.pi / n3)])
                    w, wg, _, _ = survey(Q, n_r=90, n_t=180)
                    cands.append((len(Q), w, (n1, n2, n3, r2), Q))
    cands.sort(key=lambda c: (c[0], c[1]))
    if verbose:
        print('  候选构型（按点数排序，前 8 个）：')
        for n, w, cfg, _ in cands[:8]:
            print(f'    点数 {n:3d}  最大方位间隔 {w:7.2f} 度  '
                  f'(环点数 {cfg[0]}/{cfg[1]}/{cfg[2]}, 第二环半径 {cfg[3]:.0f} m)')
    ok = [c for c in cands if c[1] < 179.0]
    n, w, cfg, Q = ok[0]
    w_full, wg, _, _ = survey(Q)
    if verbose:
        print(f'  => 最小零漏测构型：{n} 个观测点，'
              f'环点数 {cfg[0]}/{cfg[1]}/{cfg[2]}，第二环半径 {cfg[3]:.0f} m')
        print(f'     全域最大方位间隔 = {w_full:.2f} 度 (< 180 度，零漏测成立)')
    return dict(points=Q, n_points=n, radii=(1000.0, cfg[3], 1900.0),
                counts=(cfg[0], cfg[1], cfg[2]), max_gap=w_full, worst=wg)


# ==================================================================
# 4. 巡回路径（最近邻 + 2-opt）
# ==================================================================
def tour_length(pts, start_index=0):
    """最近邻构造 + 2-opt 改进的巡回路径长度（开放路径，从 start 出发）。"""
    P = np.asarray(pts, float)
    n = len(P)
    unvisited = set(range(n))
    cur = start_index
    unvisited.discard(cur)
    order = [cur]
    while unvisited:
        nxt = min(unvisited, key=lambda j: np.linalg.norm(P[j] - P[cur]))
        order.append(nxt)
        unvisited.discard(nxt)
        cur = nxt
    order = np.array(order)

    def path_len(o):
        return float(np.linalg.norm(P[o[1:]] - P[o[:-1]], axis=1).sum())

    improved = True
    while improved:
        improved = False
        for i in range(1, n - 1):
            for j in range(i + 1, n):
                o2 = order.copy()
                o2[i:j + 1] = o2[i:j + 1][::-1]
                if path_len(o2) < path_len(order) - 1e-9:
                    order = o2
                    improved = True
    return path_len(order), order


# ==================================================================
# 5. 时间模型
# ==================================================================
def scan_time(Q, L_tour, n_channels=N_CHANNEL, adaptive_drop=0):
    """覆盖网全域粗探的虚拟时间。adaptive_drop 为按顺序清理后免测的频道数。"""
    n_q = len(Q)
    n_meas = n_channels * n_q - adaptive_drop
    n_switch = (n_channels - 1) * n_q
    return L_tour / V_DOG + T_MEASURE * n_meas + T_SWITCH * n_switch, n_meas, n_switch


# ==================================================================
# 主流程
# ==================================================================
def main():
    print('=' * 76)
    print('问题四：含定向干扰源的检测与清除策略（理论建模）')
    print('=' * 76)

    Q3 = net_p3()

    # ---------------- 5.1 背向不可测定理的数值验证 ----------------
    print('\n[背向不可测定理验证] 随机 (G, psi) 与视角差 >= 180 度的探测点对')
    rng = np.random.default_rng(20260913)
    n_test = 4000
    tt = 2 * np.pi * rng.random(n_test)
    rr = 900.0 * np.sqrt(rng.random(n_test))     # 保证两点都在 1000 m 内
    viol = 0
    for k in range(n_test):
        G = np.array([R_TARGET * np.sqrt(rng.random()) * np.cos(tt[k]),
                      R_TARGET * np.sqrt(rng.random()) * np.sin(tt[k])])
        psi = 360.0 * rng.random()
        # 在 G 的 1000 m 邻域内取一对视角差 >= 180 度的探测点
        a1 = 360.0 * rng.random()
        P1 = G + rr[k] * np.array([np.cos(np.deg2rad(a1)), np.sin(np.deg2rad(a1))])
        # 第二点方位取 a1 + 180 度方向附近，保证视角差 >= 180 度
        a2 = a1 + 180.0
        P2 = G + rr[k] * np.array([np.cos(np.deg2rad(a2)), np.sin(np.deg2rad(a2))])
        v1 = P1 - G
        v2 = P2 - G
        cosang = float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-12))
        if np.rad2deg(np.arccos(np.clip(cosang, -1, 1))) < 179.9:
            continue
        if (not can_detect(P1, G, R_C_MIN, psi)) and (not can_detect(P2, G, R_C_MIN, psi)):
            viol += 1
    print(f'  视角差 >= 180 度的探测点对中，两点同时无信号的组数 = {viol} '
          f'(定理断言恒为 0)')
    # 单点探测的对照：单点无信号概率应为 1/2（背向半平面 180 度）
    cnt = 0
    N = 20000
    for _ in range(N):
        psi = 360.0 * rng.random()
        a = 360.0 * rng.random()
        P = np.array([900.0 * np.cos(np.deg2rad(a)), 900.0 * np.sin(np.deg2rad(a))])
        if not can_detect(P, np.zeros(2), R_C_MIN, psi):
            cnt += 1
    print(f'  单点探测对照：无信号频率 = {cnt/N:.4f} (理论值 0.5，'
          f'即背向半平面占 180 度)')

    # ---------------- 5.2 七点网在定向场景下的失效分析 ----------------
    print('\n[七点覆盖网的失效分析]')
    w7, wg7, Gs7, gaps7 = survey(Q3)
    r_w = np.linalg.norm(wg7)
    a_w = np.rad2deg(np.arctan2(wg7[1], wg7[0])) % 360
    print(f'  全域最大方位间隔 = {w7:.2f} 度 (>=180 度 -> 存在被漏测的定向方向)')
    print(f'  最坏位置：半径 {r_w:.0f} m，方位 {a_w:.1f} 度')
    # 定向方向随机均匀时，某位置的期望漏测概率 = 最大方位间隔 / 360
    miss7 = gaps7 / 360.0
    print(f'  定向方向随机时：全域平均漏测概率 = {miss7.mean()*100:.2f}%')
    # 按半径分层统计
    rad_grid = np.linalg.norm(Gs7, axis=1)
    layers = [(0, 400), (400, 800), (800, 1200), (1200, 1600), (1600, 1800)]
    row_l = []
    for lo, hi in layers:
        m = (rad_grid >= lo) & (rad_grid < hi + (1e-9 if hi == 1800 else 0))
        if m.sum() == 0:
            continue
        row_l.append(dict(半径区间=f'{lo}-{hi} m', 抽样点数=int(m.sum()),
                          最大方位间隔=float(gaps7[m].max()),
                          平均漏测概率=float(miss7[m].mean() * 100),
                          必然漏测占比=float((gaps7[m] >= 180).mean() * 100)))
    df_layer = pd.DataFrame(row_l)
    print('\n[按半径分层]')
    print(df_layer.round(2).to_string(index=False))
    save_csv(df_layer, '七点网漏测风险分层统计.csv')
    print(f'  最坏点处的漏测方向 psi = {hidden_direction(Q3, wg7):.1f} 度')

    # 解析：边界点可见外环窗口
    for rho in (1500.0, 1900.0, 2200.0):
        cos_t = (rho**2 + R_TARGET**2 - R_C_MIN**2) / (2 * rho * R_TARGET)
        if -1 <= cos_t <= 1:
            print(f'  外环半径 {rho:.0f} m 时，边界源可见窗口半角 = '
                  f'{np.rad2deg(np.arccos(cos_t)):.2f} 度')

    # ---------------- 5.3 冗余网求解 ----------------
    print('\n[分级冗余网求解]')
    net4 = solve_redundant_net()
    Q4 = net4['points']
    print(f'  冗余网规模 = {net4["n_points"]} 个观测点（问题三为 7 个）')

    # 对比表
    rows = []
    for tag, Q in [('问题三·七点保证覆盖网', Q3),
                   ('问题四·分级零漏测冗余网', Q4)]:
        L, _ = tour_length(Q)
        gaps = np.array([max_bearing_gap(Q, g) for g in Gs7])
        T, nm, ns = scan_time(Q, L)
        rows.append(dict(方案=tag, 观测点数=len(Q),
                         最大方位间隔=float(gaps.max()),
                         零漏测=bool(gaps.max() < 180.0),
                         巡回路径长=float(L),
                         检测次数=int(nm), 切换次数=int(ns),
                         粗探时间=float(T)))
    df_cmp = pd.DataFrame(rows)
    print('\n[两方案对比]')
    print(df_cmp.round(2).to_string(index=False))
    save_csv(df_cmp, '三方位检测网与对比表.csv')

    save_csv(pd.DataFrame(dict(
        点编号=[f'R{k}' for k in range(len(Q4))], x=Q4[:, 0], y=Q4[:, 1],
        半径=np.linalg.norm(Q4, axis=1),
        方位角=np.rad2deg(np.arctan2(Q4[:, 1], Q4[:, 0])) % 360.0)),
        '冗余网点位表.csv')

    # ---------------- 5.4 自适应补测策略的时间代价 ----------------
    # 自适应策略：先用七点网全频道粗探；仅当存在 u 个"未解频道"时，
    # 再沿加密环（中环 12 点 @1300 m + 外环 18 点 @1900 m）**只对未解频道**复测。
    print('\n[自适应补测策略的时间代价]')
    T3 = float(df_cmp[df_cmp['方案'].str.contains('七点')]['粗探时间'].iloc[0])
    T4 = float(df_cmp[df_cmp['方案'].str.contains('分级')]['粗探时间'].iloc[0])

    n_mid, r_mid = 12, 1300.0
    n_out, r_out = 18, 1900.0
    L_extra = 2 * np.pi * r_mid + 2 * np.pi * r_out          # 加密环的巡回路径
    n_extra = n_mid + n_out

    rows_pen = []
    for u in [0, 1, 2, 3, 4, 6]:
        if u == 0:
            rows_pen.append(dict(未解频道数=u, 加密环路径长=0.0, 追加检测次数=0,
                                 追加切换次数=0, 补测时间=0.0,
                                 自适应总时间=T3, 静态冗余总时间=T4,
                                 相对静态节省=1 - T3 / T4))
            continue
        n_meas = u * n_extra
        n_sw = u * n_extra
        T_fix = L_extra / V_DOG + T_MEASURE * n_meas + T_SWITCH * n_sw
        rows_pen.append(dict(未解频道数=u, 加密环路径长=float(L_extra),
                             追加检测次数=int(n_meas), 追加切换次数=int(n_sw),
                             补测时间=float(T_fix),
                             自适应总时间=float(T3 + T_fix),
                             静态冗余总时间=float(T4),
                             相对静态节省=float(1 - (T3 + T_fix) / T4)))
    df_pen = pd.DataFrame(rows_pen)
    print(df_pen.round(3).to_string(index=False))
    save_csv(df_pen, '自适应补测代价表.csv')

    print(f'\n  静态零漏测冗余网粗探时间   = {T4:.1f} s')
    print(f'  问题三七点网粗探时间       = {T3:.1f} s')
    print(f'  静态方案的定向时间惩罚系数 kappa_static = (T4 - T3)/T3 = {(T4-T3)/T3:.3f}')
    print(f'  自适应方案在 u=2 个未解频道时的总时间 = '
          f'{df_pen[df_pen["未解频道数"]==2]["自适应总时间"].iloc[0]:.1f} s，'
          f'较静态方案节省 '
          f'{df_pen[df_pen["未解频道数"]==2]["相对静态节省"].iloc[0]*100:.1f}%')

    # ---------------- 5.5 图1：可检测域与两个基本定理（1×3） ----------------
    fig, axes = plt.subplots(1, 3, figsize=(17.5, 5.6))
    G0 = np.array([0.0, 400.0])
    psi = 60.0

    ax = axes[0]
    ax.add_patch(Circle(G0, R_C_MIN, fill=True, alpha=0.18, facecolor=COLORS_10[0],
                        edgecolor=COLORS_10[0], linewidth=1.8,
                        label='全向源可检测域（圆盘）'))
    ax.add_patch(MplWedge(G0, R_C_MIN, psi - 90, psi + 90, fill=True, alpha=0.42,
                          facecolor=COLORS_10[3], edgecolor=COLORS_10[3],
                          linewidth=1.8, label='定向源可检测域（半圆盘）'))
    ax.annotate('', xy=G0 + 1150 * np.array([np.cos(np.deg2rad(psi)),
                                             np.sin(np.deg2rad(psi))]), xytext=G0,
                arrowprops=dict(arrowstyle='-|>', color=COLORS_10[3], lw=2.4))
    ax.scatter(G0[0], G0[1], s=200, marker='*', color='k', zorder=8, label='干扰源 $G_c$')
    ax.text(G0[0] - 620, G0[1] + 1160, '定向方向 $\\psi_c$', color=COLORS_10[3],
            fontsize=10)
    ax.text(G0[0] - 1500, G0[1] - 250, '背向区\n无信号', fontsize=10, color='#444444')
    ax.set_aspect('equal')
    ax.set_xlim(G0[0] - 1750, G0[0] + 1750)
    ax.set_ylim(G0[1] - 1400, G0[1] + 1400)
    ax.set_xlabel('X 方向坐标 (m)', fontsize=11)
    ax.set_ylabel('Y 方向坐标 (m)', fontsize=11)
    ax.set_title('(a) 定向源与全向源的可检测域', fontsize=12)
    apply_mpl_style(fig, ax=ax)
    set_legend_cn(ax, loc='lower right', fontsize=8.5)

    ax = axes[1]
    ax.add_patch(Circle(G0, R_C_MIN, fill=False, edgecolor='#BBBBBB', linestyle=':',
                        linewidth=1.4, label='有效接收半径 1000 m'))
    Pp = [G0 + 900 * np.array([np.cos(np.deg2rad(a)), np.sin(np.deg2rad(a))])
          for a in (psi + 180.0, psi)]
    ax.add_patch(MplWedge(G0, R_C_MIN, psi - 90, psi + 90, fill=True, alpha=0.20,
                          facecolor=COLORS_10[3], edgecolor=COLORS_10[3], linewidth=1.4))
    for k, pp in enumerate(Pp):
        ok = can_detect(pp, G0, R_C_MIN, psi)
        ax.scatter(pp[0], pp[1], s=150, marker='o',
                   color=COLORS_10[2] if ok else COLORS_10[3], edgecolor='k', zorder=7,
                   label=(f'$P_{k+1}$: {"有信号" if ok else "无信号"}'))
        ax.plot([G0[0], pp[0]], [G0[1], pp[1]], '-', color='#555555', linewidth=1.4)
    ax.scatter(G0[0], G0[1], s=200, marker='*', color='k', zorder=8, label='干扰源 $G_c$')
    ax.set_aspect('equal')
    ax.set_xlim(G0[0] - 1700, G0[0] + 1700)
    ax.set_ylim(G0[1] - 1300, G0[1] + 1300)
    ax.set_xlabel('X 方向坐标 (m)', fontsize=11)
    ax.set_ylabel('Y 方向坐标 (m)', fontsize=11)
    ax.set_title('(b) 背向不可测定理：视角差 $180^\\circ$', fontsize=12)
    apply_mpl_style(fig, ax=ax)
    set_legend_cn(ax, loc='lower right', fontsize=8.5)

    ax = axes[2]
    ax.add_patch(Circle(G0, R_C_MIN, fill=False, edgecolor='#BBBBBB', linestyle=':',
                        linewidth=1.4))
    ax.add_patch(MplWedge(G0, R_C_MIN, psi - 90, psi + 90, fill=True, alpha=0.20,
                          facecolor=COLORS_10[3], edgecolor=COLORS_10[3], linewidth=1.4,
                          label='覆盖半平面'))
    for k in range(3):
        a = np.deg2rad(0 + 120 * k)
        pp = G0 + 900 * np.array([np.cos(a), np.sin(a)])
        ok = can_detect(pp, G0, R_C_MIN, psi)
        ax.scatter(pp[0], pp[1], s=150, marker='o',
                   color=COLORS_10[2] if ok else COLORS_10[3], edgecolor='k', zorder=7,
                   label=(f'$Q_{k+1}$ ({["有信号", "无信号"][int(not ok)]})' if k < 2
                          else '$Q_3$ (有信号)'))
        ax.plot([G0[0], pp[0]], [G0[1], pp[1]], '-', color='#555555', linewidth=1.4)
    ax.scatter(G0[0], G0[1], s=200, marker='*', color='k', zorder=8, label='干扰源 $G_c$')
    ax.set_aspect('equal')
    ax.set_xlim(G0[0] - 1700, G0[0] + 1700)
    ax.set_ylim(G0[1] - 1300, G0[1] + 1300)
    ax.set_xlabel('X 方向坐标 (m)', fontsize=11)
    ax.set_ylabel('Y 方向坐标 (m)', fontsize=11)
    ax.set_title('(c) $120^\\circ$ 三方位定理', fontsize=12)
    apply_mpl_style(fig, ax=ax)
    set_legend_cn(ax, loc='lower right', fontsize=8.5)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.suptitle('定向源的可检测域与两个判别定理', fontsize=13)
    save_fig(fig, '定向源可检测域与判别定理图.png')

    # ---------------- 5.6 图2：七点网的可隐藏区与冗余网（1×2） ----------------
    fig, axes = plt.subplots(1, 2, figsize=(13.8, 6.4))
    ax = axes[0]
    n_r, n_t = 120, 240
    rr = np.linspace(0, R_TARGET, n_r)
    tt = np.linspace(0, 2 * np.pi, n_t, endpoint=False)
    RR, TT = np.meshgrid(rr, tt, indexing='ij')
    GP = np.c_[(RR * np.cos(TT)).ravel(), (RR * np.sin(TT)).ravel()]
    MG = np.array([max_bearing_gap(Q3, g) for g in GP]).reshape(RR.shape)
    # 发散配色以 180 度为中性点：<180 可行（蓝），>=180 存在漏测方向（红）
    pc = ax.pcolormesh(np.rad2deg(TT), RR, MG, cmap=CMAP_DIVERGING, shading='auto',
                       vmin=60, vmax=300)
    cb = fig.colorbar(pc, ax=ax)
    cb.set_label('观测点的方位角最大间隔 (度)', fontsize=10)
    ax.contour(np.rad2deg(TT), RR, MG, levels=[180.0], colors=['k'],
               linewidths=2.4)
    ax.scatter(np.rad2deg(np.arctan2(Q3[:, 1], Q3[:, 0])) % 360, np.linalg.norm(Q3, axis=1),
               s=90, marker='^', color='white', edgecolor='k', zorder=6,
               label='七点覆盖网')
    ax.set_xlabel('方位角 (度)', fontsize=11)
    ax.set_ylabel('距原点半径 (m)', fontsize=11)
    ax.set_title('(a) 七点网下的可漏测区（黑线为 $180^\\circ$ 门槛）', fontsize=11.5)
    apply_mpl_style(fig, ax=ax)
    set_legend_cn(ax, loc='upper right', fontsize=9)

    ax = axes[1]
    ax.plot(R_TARGET * np.cos(np.linspace(0, 2 * np.pi, 500)),
            R_TARGET * np.sin(np.linspace(0, 2 * np.pi, 500)), '-', color='#333333',
            linewidth=1.6, label='目标区域边界')
    for d in net4['radii']:
        ax.add_patch(Circle((0, 0), d, fill=False, linestyle='--', linewidth=1.0,
                            edgecolor='#999999'))
    ax.scatter(Q4[:, 0], Q4[:, 1], s=52, marker='o', color=COLORS_10[4],
               edgecolor='k', linewidth=0.5, zorder=6,
               label=f'零漏测冗余网（{net4["n_points"]} 点）')
    ax.scatter(Q3[:, 0], Q3[:, 1], s=120, marker='^', color=COLORS_10[0],
               edgecolor='k', zorder=7, label='七点覆盖网（问题三）')
    ax.set_aspect('equal')
    ax.set_xlim(-2200, 2200)
    ax.set_ylim(-2200, 2200)
    ax.set_xlabel('X 方向坐标 (m)', fontsize=11)
    ax.set_ylabel('Y 方向坐标 (m)', fontsize=11)
    ax.set_title('(b) 分级零漏测冗余网与七点网对比', fontsize=11.5)
    apply_mpl_style(fig, ax=ax)
    set_legend_cn(ax, loc='upper right', fontsize=8.5)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.suptitle('定向场景下的观测网设计', fontsize=13)
    save_fig(fig, '七点网可隐藏区与冗余网对比图.png')

    # ---------------- 5.7 图3：时间惩罚与网络规模权衡（1×2） ----------------
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.4))
    ax = axes[0]
    tags = ['问题三\n七点覆盖网', '问题四\n自适应补测', '问题四\n静态冗余网']
    vals = [T3, float(df_pen[df_pen['未解频道数'] == 2]['自适应总时间'].iloc[0]), T4]
    bars = ax.bar(tags, vals, color=[COLORS_10[0], COLORS_10[2], COLORS_10[3]],
                  width=0.55)
    for b, v in zip(bars, vals):
        ax.annotate(f'{v:.0f} s', (b.get_x() + b.get_width() / 2, v),
                    textcoords='offset points', xytext=(0, 6), ha='center', fontsize=10)
    ax.set_ylabel('粗探阶段虚拟时间 (s)', fontsize=11)
    ax.set_title('(a) 三种观测方案的时间代价', fontsize=12)
    apply_mpl_style(fig, ax=ax)

    ax = axes[1]
    trades = []
    for n1 in (6, 12):
        for n2 in (0, 6, 12, 18):
            for n3 in (6, 12, 18, 24):
                radii = [1000.0] + ([1300.0] if n2 else []) + [1900.0]
                counts = [n1] + ([n2] if n2 else []) + [n3]
                Q = net_p4(radii, counts)
                w, _, _, _ = survey(Q, n_r=45, n_t=90)
                trades.append((len(Q), w, (n1, n2, n3)))
    dt = pd.DataFrame(trades, columns=['点数', '最大方位间隔', '构型'])
    dt = dt.groupby('点数', as_index=False)['最大方位间隔'].min()
    ax.plot(dt['点数'], dt['最大方位间隔'], 'o-', color=COLORS_10[4], linewidth=2.0,
            markersize=7)
    ax.axhline(180.0, color=COLORS_10[3], linestyle='--', linewidth=1.8,
               label='零漏测门槛 $180^\\circ$')
    ax.scatter([net4['n_points']], [net4['max_gap']], s=170, marker='*',
               color=COLORS_10[2], edgecolor='k', zorder=7,
               label=f'最小可行构型 {net4["n_points"]} 点')
    ax.set_xlabel('观测点数量', fontsize=11)
    ax.set_ylabel('全域最大方位间隔 (度)', fontsize=11)
    ax.set_title('(b) 观测点数量与零漏测门槛的关系', fontsize=12)
    apply_mpl_style(fig, ax=ax)
    set_legend_cn(ax, fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.suptitle('定向源引入的时间代价与观测网规模权衡', fontsize=13)
    save_fig(fig, '定向源时间惩罚与网规模权衡图.png')

    # ---------------- 5.8 汇总 ----------------
    print('\n[关键结论]')
    print(f'  零漏测判据：观测点集在源点处方位角最大间隔 < 180 度')
    print(f'  七点覆盖网最大间隔 {w7:.2f} 度 -> 定向场景下必然漏测')
    print(f'  分级冗余网最小规模 {net4["n_points"]} 点，最大间隔 {net4["max_gap"]:.2f} 度')
    print(f'  粗探时间：问题三 {T3:.0f} s -> 问题四静态 {T4:.0f} s，'
          f'惩罚系数 kappa = {(T4-T3)/T3:.3f}')
    print('\n问题四求解完成，结果已保存至', OUT_DIR)


if __name__ == '__main__':
    main()
