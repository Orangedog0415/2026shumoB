"""【方案七】敏感性分析：策略参数、时间常数、源分布、保证假设，四组扫描一次跑完。

分五块（第五块"统计不确定性"由出图脚本直接对 results/绘图数据.json 做 bootstrap，不在这里跑）：

S1 策略参数的单参数(OAT)扫描
    固定其余参数为 CFG4，逐个扫 x / r_ok / probe_angle / lp_cap / lp_angle / lp_max / cover_k / final。
    问题三用方案四调度 + 正八边形网，问题四用方案七调度 + 25 点网，三批案例（seed 1/202/777）各 30 局。

S2 模拟器时间常数的敏感性
    覆盖网的取舍完全由"移动速度 / 检测时间 / 切换时间"的比值决定：
    移动越贵越该缩短巡回，检测越贵越该减少点数。若正式测试的时间常数与附件不同，
    25 点网未必还优于 27 点网。这里在 (速度, 检测时间) 的网格上重跑方案四 / 六 / 七，看排名是否翻转。
    注意：调度器内部的代价模型仍按默认常数写死（dist/5、6 s/频道、5 或 11 s），
    三个版本都用同一套被"标定错"的调度器，只有覆盖网不同，所以比较仍然公平。

S3 源分布假设的敏感性
    定向源比例 pD、接收半径 r 的分布、源位置的分布各扫一轮，方案四与方案七同批对比。

S4 保证假设的裕度与破坏
    (a) 真实测向误差幅度超过假设的 δ=1.005° 时，全清率怎么退化；
    (b) 把假设的 δ 往上抬（买保险）要付多少时间；
    (c) 清除方格边长越过理论阈值 20√2≈28.284 m 时，全清率怎么掉。

运行：python 方案七_敏感性分析.py            全部跑一遍（约 15~25 分钟）
      python 方案七_敏感性分析.py --only S2,S4  只跑指定的块
每算完一个参数/一个块就写一次 results/敏感性分析.json，再次运行会自动跳过已完成的部分（断点续跑）。
输出：results/敏感性分析.json（出图脚本读它）与 results/方案七_敏感性分析输出.txt
"""
import math, copy, json, random, importlib.util, statistics as st, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
def _m(n, f):
    s = importlib.util.spec_from_file_location(n, str(f)); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
R6 = _m('R6', HERE/'方案六_运行.py')
L = R6.L; J = L.J; dist = L.dist
NET3, NET4, NET6, NET7 = L.NET3(), L.NET4_V4(), L.NET4_V6(), L.NET4_V7()
SEEDS = (1, 202, 777)
OUT = []
def log(s): OUT.append(s); print(s, flush=True)
JF = HERE/'results'/'敏感性分析.json'
DATA = json.load(open(JF, encoding='utf-8')) if JF.exists() else {}
def save():
    json.dump(DATA, open(JF, 'w', encoding='utf-8'), ensure_ascii=False)

# ---------------- 通用评测 ----------------
def eval_q3(C, cases=None, W=None):
    W = W or J.World
    return st.mean(L.solve(W(copy.deepcopy(s), i), False, NET3, C).time/len(s)
                   for i, s in enumerate(cases if cases is not None else L.cases(1)[0]))
def eval_q4(C, net=None, cases=None, W=None):
    W = W or J.World; net = net or NET7
    return st.mean(R6.solve6(W(copy.deepcopy(s), i), net, C).time/len(s)
                   for i, s in enumerate(cases if cases is not None else L.cases(1)[1]))

# ---------------- S1 策略参数 OAT ----------------
GRID = [
    ('x',           [200., 350., 450., 530., 650., 800., 1000.]),
    ('r_ok',        [60., 90., 110., 130., 170., 220., 300.]),
    ('probe_angle', [8., 10., 12., 16., 22., 30., 40.]),
    ('lp_cap',      [320., 420., 540., 650., 800., 1000.]),
    ('lp_angle',    [35., 40., 48., 55., 65., 75.]),
    ('lp_max',      [1, 2, 3, 4, 6]),
    ('cover_k',     [1, 2, 3, 4, 5, 6]),
    ('final',       ['nn', 'alns']),
]
def s1():
    log('\n=== S1 策略参数的单参数扫描（其余参数固定为 CFG4）===')
    res = DATA.setdefault('S1', {})
    for name, vals in GRID:
        if name in res:
            log('  %-12s 已有结果，跳过' % name); continue
        rows = []
        for v in vals:
            C = L.cfg(**{**L.CFG4, name: v})
            q3 = [eval_q3(C, L.cases(sd)[0]) for sd in SEEDS]
            q4 = [eval_q4(C, NET7, L.cases(sd)[1]) for sd in SEEDS]
            rows.append(dict(v=v, q3=q3, q4=q4))
            log('  %-12s = %-6s  问题三 %6.1f / %6.1f / %6.1f   问题四 %6.1f / %6.1f / %6.1f'
                % (name, v, *q3, *q4))
        res[name] = dict(vals=[r['v'] for r in rows], rows=rows, cfg4=L.CFG4.get(name, L.DEF.get(name)))
        save()
    return res

# ---------------- S2 时间常数 ----------------
def timed_world(v=5., td=5., tsw=1., tok=5., tno=3.):
    class TW(J.World):
        def move(s, p):
            dt = dist(s.pos, p)/v; s.time += dt; s.moves += dt; s.pos = p
        def measure(s, p, ch):
            s.move(p); sw = int(ch != s.channel); s.channel = ch
            s.time += td + sw*tsw; s.detect += td; s.switch += sw*tsw; s.actions += 1
            src = s.sources.get(ch)
            if src is None or src['cleared']: return 'no_signal', None
            d = dist(p, src['g'])
            if d > src['r'] or (src['type'] == 'D' and J.dot((p[0]-src['g'][0], p[1]-src['g'][1]), src['u']) < -1e-10):
                return 'no_signal', None
            if d <= 5: return 'near', None
            e = math.sin(.007*p[0] + .011*p[1] + ch*1.7 + s.salt)
            return 'direction', math.radians(round((math.degrees(math.atan2(src['g'][1]-p[1], src['g'][0]-p[0]))+e) % 360, 2) % 360)
        def clear(s, p, ch):
            s.move(p); src = s.sources.get(ch)
            ok = src is not None and not src['cleared'] and dist(p, src['g']) <= 20
            dt = tok if ok else tno
            s.time += dt; s.cleartime += dt; s.actions += 1
            if ok: src['cleared'] = True
            return ok
    return TW
def s2():
    log('\n=== S2 模拟器时间常数的敏感性（问题四训练集）===')
    C = L.cfg(**L.CFG4); cases = L.cases(1)[1]
    VS = [2.5, 5., 10.]; TDS = [2., 5., 10.]
    res = []
    for v in VS:
        for td in TDS:
            W = timed_world(v=v, td=td)
            r = {}
            for tag, net in (('方案四', NET4), ('方案六', NET6), ('方案七', NET7)):
                r[tag] = eval_q4(C, net, cases, W)
            best = min(r, key=r.get)
            res.append(dict(v=v, td=td, **r, best=best))
            log('  速度 %4.1f m/s  检测 %4.1f s   方案四 %7.1f  方案六 %7.1f  方案七 %7.1f   最优 %s'
                % (v, td, r['方案四'], r['方案六'], r['方案七'], best))
    return res

# ---------------- S3 源分布 ----------------
def gen_cases(seed, n_list=(10, 13, 16), per=10, pD=.65, rmode='uniform', pos='uniform'):
    rng = random.Random(seed); out = []
    for n in n_list:
        for _ in range(per):
            src = {}
            for ch in rng.sample(range(1, 21), n):
                if pos == 'uniform': rr = 1800*math.sqrt(rng.random())
                elif pos == 'outer': rr = rng.uniform(1200, 1800)
                else:               rr = rng.uniform(0, 900)
                a = rng.random()*2*math.pi
                r = {'uniform': lambda: rng.uniform(1000, 1500), 'min': lambda: 1000.,
                     'max': lambda: 1500.}[rmode]()
                src[ch] = J.source((rr*math.cos(a), rr*math.sin(a)), r,
                                   'D' if rng.random() < pD else 'O', rng.random()*2*math.pi)
            out.append(src)
    return out
def s3():
    log('\n=== S3 源分布假设的敏感性（问题四，每组 30 局）===')
    C = L.cfg(**L.CFG4); res = {}
    for key, variants in (('pD', [0., .25, .5, .65, .85, 1.]),
                          ('rmode', ['min', 'uniform', 'max']),
                          ('pos', ['inner', 'uniform', 'outer'])):
        rows = []
        for v in variants:
            kw = {key: v}
            cases = gen_cases(1, **kw)
            a = eval_q4(C, NET4, cases); b = eval_q4(C, NET7, cases)
            rows.append(dict(v=v, 方案四=a, 方案七=b))
            log('  %-6s = %-8s  方案四 %7.1f   方案七 %7.1f   (%+.1f%%)' % (key, v, a, b, 100*(b/a-1)))
        res[key] = rows
    return res

# ---------------- S4 保证假设 ----------------
def run_guard(net, C, cases, ef, salt0=0):
    """返回 (全清局数, 总局数, 已清源比例均值, 完成局的每源平均时间)。"""
    ok = 0; ratios = []; times = []
    for i, s in enumerate(cases):
        w = R6.W(copy.deepcopy(s), salt0+i, ef)
        try:
            R6.solve6(w, net, C); ok += 1; times.append(w.time/len(s))
        except AssertionError:
            pass
        ratios.append(sum(1 for v in w.sources.values() if v['cleared'])/len(s))
    return ok, len(cases), st.mean(ratios), (st.mean(times) if times else float('nan'))
def s4():
    log('\n=== S4 保证假设的裕度与破坏（问题四训练集 30 局，方案七）===')
    C = L.cfg(**L.CFG4); cases = L.cases(1)[1]; res = {}

    log('  (a) 真实误差幅度超过假设的 δ=1.005°')
    rows = []
    for e in (0.5, 1.0, 1.005, 1.2, 1.5, 2.0, 3.0):
        ef = (lambda ee: (lambda p, c, s: ee if R6.h01(round(p[0], 3), round(p[1], 3), c, s) < .5 else -ee))(e)
        ok, tot, ratio, t = run_guard(NET7, C, cases, ef)
        rows.append(dict(e=e, ok=ok, tot=tot, ratio=ratio, t=t))
        log('      真实误差 ±%.3f°  全清 %2d/%d 局  平均清除率 %.3f  每源 %.0f s' % (e, ok, tot, ratio, t))
    res['true_error'] = rows

    log('  (b) 把假设的误差界 δ 抬高（买保险的价钱），真实误差固定为 ±1°')
    rows = []; d0 = J.DELTA
    ef1 = lambda p, c, s: 1.0 if R6.h01(round(p[0], 3), round(p[1], 3), c, s) < .5 else -1.0
    for dg in (1.005, 1.1, 1.3, 1.6, 2.0, 3.0):
        J.DELTA = math.radians(dg)
        ok, tot, ratio, t = run_guard(NET7, C, cases, ef1)
        rows.append(dict(delta=dg, ok=ok, tot=tot, ratio=ratio, t=t))
        log('      假设 δ=%.3f°  全清 %2d/%d 局  每源 %.0f s' % (dg, ok, tot, t))
    J.DELTA = d0
    res['assumed_delta'] = rows

    log('  (c) 清除方格边长（理论阈值 20√2 ≈ 28.284 m）')
    rows = []; occ = L.cover_centers
    for cell in (24., 26., 28., 28.2, 28.5, 30., 32., 36.):
        L.cover_centers = (lambda cc, c=cell: lambda poly, s=c: occ(poly, s))(occ)
        ok, tot, ratio, t = run_guard(NET7, C, cases, ef1)
        rows.append(dict(cell=cell, ok=ok, tot=tot, ratio=ratio, t=t))
        log('      方格边长 %.1f m  全清 %2d/%d 局  平均清除率 %.4f  每源 %.0f s' % (cell, ok, tot, ratio, t))
    L.cover_centers = occ
    res['cell'] = rows

    log('  (d) 抬高 δ 能不能救回真实误差超界的情形（全清局数 / 30）')
    rows = []
    for dg in (1.005, 1.3, 1.6, 2.0, 2.5):
        J.DELTA = math.radians(dg); line = []
        for e in (1.0, 1.2, 1.5, 2.0, 2.4):
            ef = (lambda ee: (lambda p, c, s: ee if R6.h01(round(p[0], 3), round(p[1], 3), c, s) < .5 else -ee))(e)
            ok, tot, ratio, tt = run_guard(NET7, C, cases, ef)
            line.append(dict(e=e, ok=ok, tot=tot, ratio=ratio, t=tt))
        rows.append(dict(delta=dg, cells=line))
        log('      假设 δ=%.3f°   ' % dg + '   '.join('真实±%.1f°:%2d/%d' % (c['e'], c['ok'], c['tot']) for c in line))
    J.DELTA = d0
    res['delta_vs_error'] = rows
    return res

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument('--only', default='S1,S2,S3,S4')
    only = set(ap.parse_args().only.split(','))
    t0 = time.time()
    for key, fn in (('S1', s1), ('S2', s2), ('S3', s3), ('S4', s4)):
        if key not in only: continue
        if key != 'S1' and key in DATA:
            log('\n=== %s 已有结果，跳过 ===' % key); continue
        DATA[key] = fn(); save()
    log('\n用时 %.1f 分钟' % ((time.time()-t0)/60))
    f = HERE/'results'/'方案七_敏感性分析输出.txt'
    old = f.read_text(encoding='utf-8') if f.exists() else ''
    f.write_text(old + '\n'.join(OUT) + '\n', encoding='utf-8')
