"""问题二各张插图共用的数据：首次观测的外包络多边形 P、安全候选域、评分场 F(S)、最坏后验区域。

与 方案一_最终方案验证.py 的 second_station_example 同一套口径：
  首次检测点 S1=(0,0)，示向度 0°；P = 楔形(δ=1.005°) ∩ {到 S1 ≤1500 m} ∩ 目标圆盘；
  候选点可行 ⟺ max_{V∈vert(P)} |S-V| ≤ 999 m（保证第二点一定能收到信号的充分条件）；
  评分 F(S) = Ĵ(S) + 0.05·|S-S1|/5，其中 Ĵ 为有限样本下的最坏后验直径（源沿 P 边界每 100 m 取样，误差取 -δ/0/+δ）。
"""
import math, importlib.util
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
_j = importlib.util.spec_from_file_location('J', str(HERE.parent/'baseline'/'方案一_最终方案验证.py'))
J = importlib.util.module_from_spec(_j); _j.loader.exec_module(J)

S1 = (0., 0.); TH1 = 0.
P = J.update(J.initial_poly(), S1, TH1)

def samples(poly=None, step=100.):
    poly = poly or P; out = []
    for a, b in zip(poly, poly[1:]+poly[:1]):
        n = max(1, math.ceil(J.dist(a,b)/step))
        out += [(a[0]+i/n*(b[0]-a[0]), a[1]+i/n*(b[1]-a[1])) for i in range(n)]
    out.append(J.centroid(poly)); return out

SAMP = samples()

def worst_post(s):
    """候选点 s 处的有限样本最坏后验直径，同时返回取到它的 (源样本, 误差, 后验多边形)。"""
    best = (0., None, None, None)
    for g in SAMP:
        if J.dist(g, s) <= 5:
            if 10. > best[0]: best = (10., g, 0., None)
            continue
        a = math.atan2(g[1]-s[1], g[0]-s[0])
        for e in (-J.DELTA, 0., J.DELTA):
            post = J.wedge(P, s, a+e)
            d = J.diameter(post)[0]
            if d > best[0]: best = (d, g, e, post)
    return best

def feasible(s): return J.radius(P, s) <= 999.
def score(s): return worst_post(s)[0] + .05*J.dist(S1, s)/5

def field(step=25., xs=(0., 1500.), ys=(-1000., 1000.)):
    """在矩形网格上算 F(S)，不可行处置 NaN。返回 (X, Y, F)。"""
    X = np.arange(xs[0], xs[1]+1e-9, step); Y = np.arange(ys[0], ys[1]+1e-9, step)
    F = np.full((len(Y), len(X)), np.nan)
    for i, y in enumerate(Y):
        for k, x in enumerate(X):
            if feasible((x, y)): F[i, k] = score((x, y))
    return X, Y, F
