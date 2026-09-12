"""为图 15~19、22 采集绘图数据：逐局时间、时间分解、单局轨迹、压力测试逐局时间。

一次跑完写到 code/experiments/results/绘图数据.json，后面的出图脚本只读这个文件，不再重跑仿真。
口径与各版本的运行脚本完全一致：
  方案一 = code/baseline/方案一_最终方案验证.py 的 solve（七点网 / 37 点格网）
  方案四 = 实验台 solve + CFG4 + NET4_V4
  方案六 = solve6 + CFG4 + NET4_V6
  方案七 = solve6 + CFG4 + NET4_V7
案例集：L.cases(seed) 的问题四 30 局（N=10/13/16 各 10 局），seed 1 / 202 / 777。
运行：python _绘图数据采集.py（约 10~20 分钟）
"""
import math, copy, json, random, importlib.util, statistics as st
from pathlib import Path
HERE = Path(__file__).resolve().parent
def _m(n, f):
    s = importlib.util.spec_from_file_location(n, str(f)); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
R6 = _m('R6', HERE.parent/'experiments'/'方案六_运行.py')
L = R6.L; J = L.J; CFG = L.cfg(**L.CFG4)
NET = dict(方案四=L.NET4_V4(), 方案六=L.NET4_V6(), 方案七=L.NET4_V7())

class Rec(J.World):
    """带轨迹记录的 World：每个动作记下落点与类型。"""
    def __init__(s, src, salt=0):
        super().__init__(src, salt); s.log = [((0., 0.), 'start', None)]
    def measure(s, p, ch):
        z, a = super().measure(p, ch); s.log.append((tuple(p), 'measure', z)); return z, a
    def clear(s, p, ch):
        ok = super().clear(p, ch); s.log.append((tuple(p), 'clear', ok)); return ok

def stats(w, n):
    return dict(t=w.time/n, moves=w.moves, detect=w.detect, switch=w.switch,
                clear=w.cleartime, actions=w.actions, total=w.time, n=n)

def run(tag, src, rec=False, salt=0):
    W = Rec if rec else J.World
    w = W(copy.deepcopy(src), salt)
    if tag == '方案一': J.solve(w, True)
    elif tag == '方案四': L.solve(w, True, NET['方案四'], CFG)
    else: R6.solve6(w, NET[tag], CFG)
    return w

if __name__ == '__main__':
    out = {}
    # 1) 逐局时间与时间分解
    per = {}
    for tag in ('方案一', '方案四', '方案六', '方案七'):
        per[tag] = {}
        for sd in (1, 202, 777):
            rows = []
            for i, s in enumerate(L.cases(sd)[1]):
                w = run(tag, s, salt=i); rows.append(stats(w, len(s)))
            per[tag][str(sd)] = rows
            print('%s seed %d: %.1f s/源' % (tag, sd, st.mean(r['t'] for r in rows)), flush=True)
    out['per_case'] = per

    # 2) 单局轨迹（训练集第 21 局，N=16）：方案一 与 方案七
    case = L.cases(1)[1][20]
    out['traj'] = {}
    for tag in ('方案一', '方案七'):
        w = run(tag, case, rec=True, salt=20)
        out['traj'][tag] = dict(log=[[list(p), k, (v if isinstance(v, (str, bool, type(None))) else str(v))] for p, k, v in w.log],
                                time=w.time, n=len(case), **{k: getattr(w, k) for k in ('moves','detect','switch','cleartime','actions')})
    out['traj']['sources'] = [dict(ch=ch, g=list(v['g']), r=v['r'], type=v['type'],
                                   u=list(v['u']) if v['type'] == 'D' else None) for ch, v in case.items()]
    print('轨迹：方案一 %.0f s，方案七 %.0f s' % (out['traj']['方案一']['time'], out['traj']['方案七']['time']), flush=True)

    # 3) 压力测试逐局（方案七，与 方案七_运行.py 同一批 180 局）
    rows = []
    for en, ef in R6.ERR.items():
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
                        w = R6.W(src, rep, ef)
                        R6.solve6(w, NET['方案七'], CFG)
                        rows.append(dict(err=en, rmode=rmode, layout=layout, n=n, t=w.time/n))
    out['stress'] = rows
    print('压力测试 %d 局，每源平均 %.0f s' % (len(rows), st.mean(r['t'] for r in rows)), flush=True)

    f = HERE.parent/'experiments'/'results'/'绘图数据.json'
    json.dump(out, open(f, 'w', encoding='utf-8'), ensure_ascii=False)
    print('已写出', f)
