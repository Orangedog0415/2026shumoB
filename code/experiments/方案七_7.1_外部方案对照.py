"""【7.1】外部方案对照：li2396803/cumcm2026 的 B 题解法 vs 我们的方案七，同案例、同误差场、同时间常数。

外部方案取自 https://github.com/li2396803/cumcm2026 （MIT），代码原样收录在 code/external/li2396803/。
它与我们的思路差别很大，值得逐项对照：

| | 我们（方案四 / 方案七） | 外部方案（v2） |
|---|---|---|
| 问题三侦察点 | 正八边形 974 m，8 点，巡回 6 192 m | 8 点，巡回 6 708 m |
| 问题四侦察点 | 25 点非规则三角网，17 547 m，**有零漏测证书** | 19 点，18 000 m，**无证书**（其报告全清率 93~100%） |
| 调度 | 联合重规划（覆盖点 + 可清源一起排路线） | 滚动时域重优化 RHO + 风险可控自适应侦察 |
| 定向源 | 靠覆盖网的方位包围保证不漏 | 朝向贝叶斯信念 + 连续无信号后的保证性射线扫掠 |
| 接收半径 R | 只用下界 1000 m（保证层） | 对 R 做在线贝叶斯学习，据此估计漏检概率 |
| 终止判据 | 覆盖证书 + 计数提前停（≤16） | 期望漏检源个数 θ 的风险预算（θ=0 即严格） |

对照口径：两边跑**同一批案例**（我们的 cases(seed)）、**同一套误差场**、同一套时间常数
（移动 5 m/s、检测 5 s、切换 1 s、清除 5/3 s，两边本来就一致），示向度都四舍五入到 0.01°。
误差场跑两个臂：A 用我们的正弦相关场，B 用他们的 5 m 网格哈希场（均匀 ±1°）。

运行：python 方案七_7.1_外部方案对照.py --repo <外部代码目录>   （默认用 code/external/li2396803）
      python 方案七_7.1_外部方案对照.py --only A_q4              只跑某一块，支持断点续跑
输出：results/外部方案对照.json 与 results/方案七_7.1_外部方案对照输出.txt
"""
import argparse, copy, json, math, sys, time, importlib.util, statistics as st
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
def _m(n, f):
    s = importlib.util.spec_from_file_location(n, str(f)); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
R6 = _m('R6', HERE/'方案六_运行.py')
L = R6.L; J = L.J; CFG = L.cfg(**L.CFG4)
NET3, NET7 = L.NET3(), L.NET4_V7()
SEEDS = (1, 202, 777)
OUT = []
def log(s): OUT.append(s); print(s, flush=True)
JF = HERE/'results'/'外部方案对照.json'
DATA = json.load(open(JF, encoding='utf-8')) if JF.exists() else {}
def save(): json.dump(DATA, open(JF, 'w', encoding='utf-8'), ensure_ascii=False)

# ---------------- 误差场：两个臂共用同一份定义 ----------------
def err_ours(p, ch, salt):
    """我们的误差场：空间相关的正弦，同点同频道恒定（见 方案一_最终方案验证.py）。"""
    return math.sin(.007*p[0] + .011*p[1] + ch*1.7 + salt)
_THEIRS = None
def err_theirs(p, ch, salt):
    """他们的误差场：5 m 网格上的哈希，均匀落在 ±1°（见 external/.../lib/sim.py 的 env_error）。"""
    return _THEIRS(p, ch)

# ---------------- 把我们的案例转成他们的 Source ----------------
def to_sources(case, SourceCls):
    out = []
    for ch, s in case.items():
        kind = 'dir' if s['type'] == 'D' else 'omni'
        d = math.degrees(math.atan2(s['u'][1], s['u'][0])) % 360. if kind == 'dir' else None
        out.append(SourceCls(int(ch), np.array(s['g'], float), float(s['r']), kind, d))
    return out

# ---------------- 我们这边的运行 ----------------
def run_ours(case, salt, problem, ef):
    w = R6.W(copy.deepcopy(case), salt, ef)
    ok = True
    try:
        if problem == 3: L.solve(w, False, NET3, CFG)
        else: R6.solve6(w, NET7, CFG)
    except AssertionError:
        ok = False
    n = len(case); nc = sum(1 for v in w.sources.values() if v['cleared'])
    return dict(ok=ok and nc == n, n=n, nc=nc, t=w.time, per=w.time/nc if nc else float('nan'),
                move=w.moves*5, act=w.actions)

# ---------------- 他们那边的运行 ----------------
def run_theirs(case, salt, problem, ef, mods):
    sim, strategy2 = mods['sim'], mods['strategy2']
    mods['set_err'](lambda p, ch: ef(p, ch, salt))
    srcs = to_sources(case, sim.Source)
    plan = mods['plan3'] if problem == 3 else mods['plan4']
    pr = strategy2.Params2(theta_miss=0., use_belief=(problem == 4))
    r = strategy2.run_trial_v2(srcs, plan, pr, problem=problem)
    s = r['stats']
    return dict(ok=s['n_cleared'] == s['n_sources'], n=s['n_sources'], nc=s['n_cleared'],
                t=s['total_time_s'], per=s['avg_time_s'] if s['avg_time_s'] else float('nan'),
                move=s['move_m'], act=s['n_requests'])

def load_external(repo):
    """加载外部代码，并把它的 measure 换成"与我们完全同一套规则"的版本（四舍五入到 0.01°）。"""
    sys.path.insert(0, str(repo/'lib')); sys.path.insert(0, str(repo))
    import sim, strategy2, geom
    global _THEIRS
    _THEIRS = sim.env_error
    box = {'ef': lambda p, ch: 0.}
    def measure(self, pos, channel):
        self.n_requests += 1
        self._move(pos)
        dt = sim.T_MEASURE
        if channel != self.channel:
            dt += sim.T_SWITCH; self.t_switch += sim.T_SWITCH; self.channel = channel
        self.t += dt; self.t_measure += sim.T_MEASURE
        src = next((s for s in self.sources if s.channel == channel and not s.cleared), None)
        if src is None or not src.covers(self.pos): return 'no_signal', None
        d = src.dist(self.pos)
        if d <= sim.R_NEAR: return 'near', None
        svd = (geom.ang_deg(src.pos - self.pos) + box['ef'](self.pos, channel)) % 360.
        return 'direction', round(svd, 2) % 360.          # 与我们的 World 一致：保留两位小数
    sim.Simulator.measure = measure
    cov = json.load(open(repo/'cover_points.json'))
    p3 = cov['problem3']['points_ordered']
    p4 = {round(t['spacing']): t['points_ordered'] for t in cov['problem4_tradeoff']}[1000]
    return dict(sim=sim, strategy2=strategy2, geom=geom,
                plan3={'level1': p3, 'escalation': []}, plan4={'level1': p4, 'escalation': []},
                set_err=lambda f: box.__setitem__('ef', f), pts3=p3, pts4=p4)

def summarize(rows):
    per = [r['per'] for r in rows if r['nc']]
    return dict(n_games=len(rows), full=sum(1 for r in rows if r['ok']),
                ratio=st.mean(r['nc']/r['n'] for r in rows), per=st.mean(per),
                move=st.mean(r['move'] for r in rows), act=st.mean(r['act'] for r in rows),
                byN={str(nn): round(st.mean([r['per'] for r in rows if r['n'] == nn and r['nc']]), 1)
                     for nn in sorted({r['n'] for r in rows})})

def block(tag, problem, ef, seeds, mods):
    if tag in DATA: log('=== %s 已有结果，跳过 ===' % tag); return
    log('\n=== %s ===' % tag)
    res = {}
    for who, fn in (('方案七' if problem == 4 else '方案四', run_ours), ('外部 v2', run_theirs)):
        rows = []
        for sd in seeds:
            cases = L.cases(sd)[0 if problem == 3 else 1]
            for i, c in enumerate(cases):
                rows.append(fn(c, i, problem, ef) if fn is run_ours else fn(c, i, problem, ef, mods))
        res[who] = summarize(rows)
        s = res[who]
        log('  %-8s %d 局  全清 %d 局（%.1f%%）  清除率 %.4f  每源 %.1f s  移动 %.1f km  动作 %.0f  按源数 %s'
            % (who, s['n_games'], s['full'], 100*s['full']/s['n_games'], s['ratio'], s['per'],
               s['move']/1000, s['act'], s['byN']))
    a, b = list(res)
    log('  → 每源时间 %s 比 %s %+.1f%%；全清率 %.1f%% vs %.1f%%'
        % (b, a, 100*(res[b]['per']/res[a]['per']-1),
           100*res[b]['full']/res[b]['n_games'], 100*res[a]['full']/res[a]['n_games']))
    DATA[tag] = res; save()

# ---------------- C 组：保证性压力测试（与 方案七_运行.py 同一批 180 局）----------------
def stress_cases():
    import random
    out = []
    for en, ef0 in R6.ERR.items():
        for rmode in ('随机', '全 1000 m'):
            for layout in ('圆内均匀', '边界朝外'):
                rng = random.Random(abs(hash(en)) % 97 + len(rmode) + 2*len(layout))
                for n in (10, 13, 16):
                    for rep in range(3):
                        src = {}
                        for k, ch in enumerate(rng.sample(range(1, 21), n)):
                            if layout == '圆内均匀':
                                aa = rng.random()*2*math.pi; rr = 1800*math.sqrt(rng.random())
                                kind = 'D' if rng.random() < .65 else 'O'; ang = rng.random()*2*math.pi
                            else:
                                aa = 2*math.pi*k/n + rng.uniform(-.05, .05); rr = rng.uniform(1700, 1800)
                                kind = 'D'; ang = aa
                            r = 1000. if rmode == '全 1000 m' else rng.uniform(1000, 1500)
                            src[ch] = J.source((rr*math.cos(aa), rr*math.sin(aa)), r, kind, ang)
                        ef = err_ours if ef0 is None else (lambda p, c, s, f=ef0: f(p, c, s))
                        out.append((src, rep, ef, dict(err=en, rmode=rmode, layout=layout, n=n)))
    return out

def block_C(mods):
    if 'C_stress' in DATA: log('=== C_stress 已有结果，跳过 ==='); return
    log('\n=== C_stress 保证性压力测试（问题四，180 局：5 误差模型 × 半径 × 布局 × N × 3 次）===')
    cases = stress_cases(); res = {}
    for who, fn in (('方案七', run_ours), ('外部 v2', run_theirs)):
        rows = []
        for src, salt, ef, meta in cases:
            try:
                r = fn(src, salt, 4, ef) if fn is run_ours else fn(src, salt, 4, ef, mods)
            except Exception as e:
                r = dict(ok=False, n=len(src), nc=0, t=float('nan'), per=float('nan'),
                         move=float('nan'), act=0, exc=type(e).__name__)
            r.update(meta); rows.append(r)
        res[who] = rows
        full = sum(1 for r in rows if r['ok'])
        per = [r['per'] for r in rows if r['nc']]
        log('  %-8s 全清 %d/%d 局（%.1f%%）  平均清除率 %.4f  每源 %.0f s'
            % (who, full, len(rows), 100*full/len(rows), st.mean(r['nc']/r['n'] for r in rows), st.mean(per)))
        bad = {}
        for r in rows:
            if not r['ok']: bad[(r['layout'], r['rmode'])] = bad.get((r['layout'], r['rmode']), 0) + 1
        if bad:
            log('       未全清的分组：' + '，'.join('%s/%s ×%d' % (k[0], k[1], v) for k, v in sorted(bad.items())))
    DATA['C_stress'] = {k: [{kk: vv for kk, vv in r.items() if kk != 'exc'} for r in v] for k, v in res.items()}
    save()

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', default=str(HERE.parent/'external'/'li2396803'))
    ap.add_argument('--only', default='A_q3,A_q4,B_q3,B_q4,C')
    a = ap.parse_args(); only = set(a.only.split(','))
    mods = load_external(Path(a.repo))
    def tl(P, order=False):
        P = L.tour_nn2opt([tuple(map(float, q)) for q in P]) if order else [tuple(map(float, q)) for q in P]
        return L.dist((0, 0), P[0]) + sum(L.dist(P[i], P[i+1]) for i in range(len(P)-1))
    log('侦察点集：问题三 我们 %d 点/%.0f m，外部 %d 点/%.0f m；问题四 我们 %d 点/%.0f m，外部 %d 点/%.0f m'
        % (len(NET3), tl(NET3, True), len(mods['pts3']), tl(mods['pts3']),
           len(NET7), tl(NET7, True), len(mods['pts4']), tl(mods['pts4'])))
    t0 = time.time()
    for tag, problem, ef, seeds in (('A_q3', 3, err_ours, SEEDS), ('A_q4', 4, err_ours, SEEDS),
                                    ('B_q3', 3, err_theirs, (1,)), ('B_q4', 4, err_theirs, (1,))):
        if tag in only: block(tag, problem, ef, seeds, mods)
    if 'C' in only or 'C_stress' in only: block_C(mods)
    log('\n用时 %.1f 分钟' % ((time.time()-t0)/60))
    f = HERE/'results'/'方案七_7.1_外部方案对照输出.txt'
    f.write_text((f.read_text(encoding='utf-8') if f.exists() else '') + '\n'.join(OUT) + '\n', encoding='utf-8')
