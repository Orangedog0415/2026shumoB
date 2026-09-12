"""【7.2~7.5】按《问题三、四算法修订大纲》逐条实现并验证。

大纲里所有可验证的数字我们都复算过，逐位吻合（见 results/方案七_7.x_输出.txt 开头的核对段）。
四条改动分别编号实现，先单独测、再组合：

  7.2 最小包围圆圆心：Src.RC() 原来返回"顶点均值 + 到顶点最大距离"，顶点均值不是最小包围圆圆心，
      会高估可能区域的外接半径，从而错失"半径 ≤19.5 m 直接清除"的机会。改为精确最小包围圆
      （顶点数很少，用穷举对/三元组的确定性实现，等价于 Welzl 的结果）。
      正确性不变：真源在多边形内 ⇒ 到最小包围圆圆心的距离 ≤ 半径 ≤19.5 m < 20 m。

  7.3 补测点记账：原实现只记录**成功**的补测点（Src.det），无信号的点没记，而误差场对同一点是确定的，
      于是同一个点会被反复测。实测：局部补测 121 次里 78 次无信号，其中 39 次是重测已测过的点。
      改为记录所有已测点并在候选里排除。

  7.4 问题三七点环：Q_k = 999·(cos 2kπ/7, sin 2kπ/7)。解析上界 max{999, 998.88} = 999 < 1000，
      稠密复验最坏覆盖距离 999.000 m。静态开放巡回 6200.40 m，比八点环 6192.27 m 只长 8.13 m，
      但少一个站点。几何可行不等于更快，要在冻结案例上配对比较。

  7.5 完整服务代价：原路线把一个待清源压缩成"离当前位置最近的那个清除点"，而实际会按顺序试到成功。
      实测 46% 的服务是多点服务，平均 4.48 个动作。改为按大纲的上界式把整条服务序列计入路线代价：
          C(p, q_1..k, z) = max_j [ (|p-q1| + Σ|q_i-q_i+1| + |q_j-z|)/5 + 3(j-1) + 5 ]
      并据此做最近邻 + 2-opt 的滚动重排。

运行：python 方案七_7.x_大纲修订实验.py            全部跑一遍（约 10 分钟，支持断点续跑）
      python 方案七_7.x_大纲修订实验.py --only 7.2
输出：results/大纲修订实验.json 与 results/方案七_7.x_输出.txt
"""
import argparse, copy, itertools, json, math, time, importlib.util, statistics as st
from pathlib import Path
HERE = Path(__file__).resolve().parent
def _m(n, f):
    s = importlib.util.spec_from_file_location(n, str(f)); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
R6 = _m('R6', HERE/'方案六_运行.py')
L = R6.L; J = L.J; dist = L.dist; CFG = L.cfg(**L.CFG4)
NET3_8 = L.NET3()
NET3_7 = [(999.*math.cos(2*math.pi*k/7), 999.*math.sin(2*math.pi*k/7)) for k in range(7)]
NET4 = L.NET4_V7()
SEEDS = (1, 202, 777)
OUT = []
def log(s): OUT.append(s); print(s, flush=True)
JF = HERE/'results'/'大纲修订实验.json'
DATA = json.load(open(JF, encoding='utf-8')) if JF.exists() else {}
def save(): json.dump(DATA, open(JF, 'w', encoding='utf-8'), ensure_ascii=False)

# ---------------- 7.2 最小包围圆 ----------------
def _circ2(a, b):
    return ((a[0]+b[0])/2, (a[1]+b[1])/2), dist(a, b)/2
def _circ3(a, b, c):
    ax, ay = a; bx, by = b; cx, cy = c
    d = 2*(ax*(by-cy) + bx*(cy-ay) + cx*(ay-by))
    if abs(d) < 1e-12: return None
    ux = ((ax*ax+ay*ay)*(by-cy) + (bx*bx+by*by)*(cy-ay) + (cx*cx+cy*cy)*(ay-by))/d
    uy = ((ax*ax+ay*ay)*(cx-bx) + (bx*bx+by*by)*(ax-cx) + (cx*cx+cy*cy)*(bx-ax))/d
    return (ux, uy), dist((ux, uy), a)
def min_circle(P):
    """精确最小包围圆（确定性穷举；顶点数 ≤ 十几个，代价可忽略）。

    退化情形（空集 / 单点 / 共线点 / 数值上三点几乎共线）必须也返回一个**确实包住所有点**的圆，
    否则下游会拿到 None——压力测试里的对抗误差场就会造出这种多边形。
    """
    P = list(dict.fromkeys(P))
    if not P: return (0., 0.), 0.
    if len(P) == 1: return P[0], 0.
    best = None
    for a, b in itertools.combinations(P, 2):
        c, r = _circ2(a, b)
        if all(dist(c, p) <= r + 1e-9 for p in P) and (best is None or r < best[1]): best = (c, r)
    if best is None or len(P) >= 3:
        for a, b, c0 in itertools.combinations(P, 3):
            got = _circ3(a, b, c0)
            if not got: continue
            c, r = got
            if all(dist(c, p) <= r + 1e-9 for p in P) and (best is None or r < best[1]): best = (c, r)
    if best is None:                       # 数值退化时退回"质心 + 最大距离"，保证仍然包住所有点
        c = J.centroid(P); best = (c, max(dist(c, p) for p in P))
    return best
def RC_mec(s):
    return min_circle(s.P)
RC_ORIG = L.Src.RC

# ---------------- 7.3 补测点记账 ----------------
def local_clear_v2(world, ch, src, C):
    """与 方案四_实验台.local_clear 相同，只加一条：记录所有已测点（含无信号），候选里排除。"""
    probes = 0
    tried = list(src.det)                      # 关键改动：无信号的补测点也进这个表
    while True:
        c, r = src.RC()
        if r <= 19.5:
            if world.clear(c, ch): return
            raise AssertionError('certified clear failed')
        cc = L.cover_centers(src.P)
        if len(cc) <= C['cover_k']:
            cur = world.pos; rem = cc[:]
            while rem:
                q = min(rem, key=lambda q: dist(cur, q)); rem.remove(q); cur = q
                if world.clear(q, ch): return
            raise AssertionError('cover failed')
        if probes >= C['lp_max']: break
        _, ang = L.axis(src.P)
        dp = max(r+15, min(C['lp_cap'], dist(world.pos, c)))
        cand = []
        for k in range(36):
            phi = 2*math.pi*k/36
            if abs(math.sin(phi-ang)) < math.sin(math.radians(C['lp_angle'])): continue
            p = (c[0]+dp*math.cos(phi), c[1]+dp*math.sin(phi))
            if all(dist(p, t) >= 1 for t in tried): cand.append(p)
        if not cand: break
        dets = [math.atan2(d[1]-c[1], d[0]-c[0]) for d in src.det]
        ad = lambda a, b: abs(math.atan2(math.sin(a-b), math.cos(a-b)))
        def risk(p):
            a = math.atan2(p[1]-c[1], p[0]-c[0]); return min(ad(a, b) for b in dets)
        p = min(cand, key=lambda p: (dist(p, world.pos)/5 + (0 if risk(p) < math.radians(60) else 60), p[0], p[1]))
        probes += 1
        tried.append(p)
        z, a = world.measure(p, ch)
        if z == 'near':
            assert world.clear(p, ch); return
        if z == 'direction': src.add(p, a)
    for cpt, _ in J.fallback_cells(src.P, src.first, src.theta):
        if world.clear(cpt, ch): return
    for cpt, _ in J.fallback_cells(None, src.first, src.theta):
        if world.clear(cpt, ch): return
    raise AssertionError('exhausted')
LC_ORIG = L.local_clear

# ---------------- 7.5 完整服务代价 + 滚动路线 ----------------
def service_seq(src, C, frm):
    """按 frm 出发的最近邻顺序给出完整清除序列。"""
    c, r = src.RC()
    if r <= 19.5: return [c]
    cc = L.cover_centers(src.P)
    if len(cc) > C['cover_k']: return [c]
    seq = []; cur = frm; rem = cc[:]
    while rem:
        q = min(rem, key=lambda q: dist(cur, q)); rem.remove(q); seq.append(q); cur = q
    return seq
def svc_cost(p, seq, z=None):
    """大纲式：C(p,q_1..k,z) = max_j [(|p-q1| + Σ|q_i-q_{i+1}| + |q_j-z|)/5 + 3(j-1) + 5]。"""
    acc = dist(p, seq[0]); best = -1.
    for j, q in enumerate(seq):
        if j: acc += dist(seq[j-1], q)
        v = (acc + (dist(q, z) if z is not None else 0.))/5 + 3*j + 5
        if v > best: best = v
    return best
def route_cost(p, order):
    """一条任务顺序的保守总代价；每个任务给 (entry, exit, internal_extra, kind)。"""
    tot = 0.; cur = p
    for k, nd in enumerate(order):
        z = order[k+1]['entry'] if k+1 < len(order) else None
        if nd['kind'] == 'scan':
            tot += dist(cur, nd['entry'])/5 + nd['extra'] + (0. if z is None else 0.)
            cur = nd['entry']
        else:
            tot += svc_cost(cur, nd['seq'], None)
            cur = nd['seq'][-1]
    return tot
def solve8(world, net, C, use_service_cost=True):
    """方案六/七的调度 + 7.5 的完整服务代价滚动重排。"""
    Q = L.tour_nn2opt(net); rem = list(range(len(Q)))
    unknown = set(range(1, 21)); active = {}; cleared = 0; measured = {c: set() for c in unknown}
    pend = lambda i: [c for c in unknown if i not in measured[c]]
    def scan(i):
        nonlocal cleared
        q = Q[i]
        chans = sorted(pend(i), key=lambda c: (c != world.channel, c))
        extra = [c for c, s in active.items() if s.RC()[1] > 19.5 and J.radius(s.P, q) <= 1500 and L.good_geom(s, q, C['probe_angle'])]
        for ch in chans+extra:
            if ch in unknown: measured[ch].add(i)
            z, a = world.measure(q, ch)
            if z == 'near':
                assert world.clear(q, ch); cleared += 1; unknown.discard(ch); active.pop(ch, None)
            elif z == 'direction':
                if ch in unknown: unknown.discard(ch); active[ch] = L.Src(q, a)
                else: active[ch].add(q, a)
            if cleared == 16 or cleared+len(active) >= 16: return
    while cleared < 16:
        stop = cleared+len(active) >= 16
        todo = [] if stop else [i for i in rem if pend(i)]
        if not todo and not active: break
        ready = [c for c, s in active.items() if s.RC()[1] <= C['r_ok']]
        nodes = [dict(kind='scan', key=i, entry=Q[i], seq=[Q[i]], extra=6.*len(pend(i))) for i in todo]
        for c in (ready if todo else list(active)):
            seq = service_seq(active[c], C, world.pos)
            nodes.append(dict(kind='clear', key=c, entry=seq[0], seq=seq, extra=0.))
        if not nodes:
            ch = min(active, key=lambda c: dist(world.pos, active[c].RC()[0]))
            L.local_clear(world, ch, active.pop(ch), C); cleared += 1; continue
        if use_service_cost:
            order = sorted(nodes, key=lambda nd: dist(world.pos, nd['entry']))
            cur = [order[0]] if len(order) == 1 else None
            if cur is None:                                   # 最近邻 + 2-opt，代价用 route_cost
                seq2 = []; restn = nodes[:]; p = world.pos
                while restn:
                    nd = min(restn, key=lambda nd: (svc_cost(p, nd['seq']) if nd['kind'] == 'clear'
                                                    else dist(p, nd['entry'])/5 + nd['extra']))
                    seq2.append(nd); restn.remove(nd); p = nd['seq'][-1]
                best = seq2; bc = route_cost(world.pos, best)
                imp = True
                while imp:
                    imp = False
                    for i in range(len(best)-1):
                        for j in range(i+1, len(best)):
                            t = best[:i] + best[i:j+1][::-1] + best[j+1:]
                            c2 = route_cost(world.pos, t)
                            if c2 < bc - 1e-9: best, bc, imp = t, c2, True
                order = best
            first = order[0]
        else:
            pts = [min(nd['seq'], key=lambda q: dist(world.pos, q)) for nd in nodes]
            o = L.tour_nn2opt(pts, world.pos)
            first = nodes[pts.index(o[0])]
        if first['kind'] == 'clear':
            L.local_clear(world, first['key'], active.pop(first['key']), C); cleared += 1
        else:
            scan(first['key']); rem.remove(first['key'])
    if cleared < 16 and cleared+len(active) < 16:
        for ch in unknown: assert len(measured[ch]) == len(Q)
    assert all(s['cleared'] for s in world.sources.values()), '漏清'
    return world

# ---------------- 评测 ----------------
def evaluate(mec=False, probe=False, net3=None, svc=False, seeds=SEEDS):
    L.Src.RC = RC_mec if mec else RC_ORIG
    L.local_clear = local_clear_v2 if probe else LC_ORIG
    n3 = net3 or NET3_8
    try:
        q3, q4, bad = [], [], 0
        for sd in seeds:
            C3, C4 = L.cases(sd)
            for i, s in enumerate(C3):
                w = J.World(copy.deepcopy(s), i)
                try: L.solve(w, False, n3, CFG); q3.append(w.time/len(s))
                except AssertionError: bad += 1
            for i, s in enumerate(C4):
                w = J.World(copy.deepcopy(s), i)
                try:
                    solve8(w, NET4, CFG, use_service_cost=svc) if svc else R6.solve6(w, NET4, CFG)
                    q4.append(w.time/len(s))
                except AssertionError: bad += 1
        return dict(q3=st.mean(q3), q4=st.mean(q4), fail=bad, n3=len(q3), n4=len(q4))
    finally:
        L.Src.RC = RC_ORIG; L.local_clear = LC_ORIG

VAR = [
    ('方案七 基线',        dict()),
    ('7.2 最小包围圆',      dict(mec=True)),
    ('7.3 补测点记账',      dict(probe=True)),
    ('7.4 七点环（问题三）', dict(net3=NET3_7)),
    ('7.5 完整服务代价',    dict(svc=True)),
    ('7.2+7.3',            dict(mec=True, probe=True)),
    ('7.2+7.3+7.4',        dict(mec=True, probe=True, net3=NET3_7)),
    ('7.2+7.3+7.4+7.5',    dict(mec=True, probe=True, net3=NET3_7, svc=True)),
]

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--only', default='all')
    only = ap.parse_args().only
    t0 = time.time()
    for tag, kw in VAR:
        if only != 'all' and not tag.startswith(only): continue
        if tag not in DATA:
            DATA[tag] = evaluate(**kw); save()
        base = DATA['方案七 基线']; r = DATA[tag]
        log('  %-20s 问题三 %6.1f s（%+.2f%%）  问题四 %6.1f s（%+.2f%%）  未全清 %d 局'
            % (tag, r['q3'], 100*(r['q3']/base['q3']-1), r['q4'], 100*(r['q4']/base['q4']-1), r['fail']))
    log('\n用时 %.1f 分钟' % ((time.time()-t0)/60))
    f = HERE/'results'/'方案七_7.x_输出.txt'
    f.write_text((f.read_text(encoding='utf-8') if f.exists() else '') + '\n'.join(OUT) + '\n', encoding='utf-8')
