"""【方案三】队伍的优化调度＝交接材料中的“策略B”。主循环为 solve_x()：每点扫完、覆盖点顺带补测、
绕行≤x 且区域半径≤r_ok 时顺路清除、覆盖完成后按最近顺序集中清除。本文件同时扫描关键参数。
复用同目录 方案二_调度改进原型.py 中的 local_v2/net990/tour（其又复用 code/baseline/方案一_最终方案验证.py 的几何函数与 World 仿真）。本地仿真，非官方成绩。
参数：
  x      顺路清除阈值：去清该源再回到下一覆盖点，比直接去下一覆盖点多走的距离（绕行，m）
  r_ok   “可确认”阈值：源的可能区域半径（m）不超过它才考虑顺路去清
  probe  覆盖点上是否顺带补测已发现未清除的源
  net    覆盖网：7点（中心+6@1200）或 n 边形环（无中心）
运行：python 方案三_参数扫描.py   （约 1–2 分钟）
"""
import math, copy, random, statistics as st, importlib.util
from pathlib import Path
_p=Path(__file__).resolve().parent/'方案二_调度改进原型.py'
spec=importlib.util.spec_from_file_location('proto',str(_p)); P=importlib.util.module_from_spec(spec); spec.loader.exec_module(P)
J=P.J; dist=P.dist; INF=float('inf')

def ring(n,rho): return [(rho*math.cos(2*math.pi*k/n),rho*math.sin(2*math.pi*k/n)) for k in range(n)]

def solve_x(world,mixed,Q,x=600,r_ok=150,probe=True):
    Q=P.tour(Q); unknown=set(range(1,21)); active={}; cleared=0
    measured={ch:set() for ch in unknown}; todo=list(range(len(Q)))
    while cleared<16:
        todo=[i for i in todo if any(i not in measured[ch] for ch in unknown)]
        if not todo:                              # 覆盖完成：按最近邻依次清剩余
            if not active: break
            ch=min(active,key=lambda c:dist(world.pos,active[c].RC()[0]))
            P.local_v2(world,ch,active.pop(ch)); cleared+=1; continue
        nxt=Q[todo[0]]; best=None
        for ch,s in active.items():               # 顺路清除：区域够小且绕行 <= x
            c,r=s.RC()
            if r>r_ok: continue
            det=dist(world.pos,c)+dist(c,nxt)-dist(world.pos,nxt)
            if det<=x and (best is None or det<best[0]): best=(det,ch)
        if best: P.local_v2(world,best[1],active.pop(best[1])); cleared+=1; continue
        i=todo.pop(0); q=Q[i]
        chans=sorted([ch for ch in unknown if i not in measured[ch]],key=lambda ch:(ch!=world.channel,ch))
        extra=[ch for ch,s in active.items() if probe and s.RC()[1]>19.5 and J.radius(s.P,q)<=1500 and P.good_geometry(s,q)]
        for ch in chans+extra:
            if ch in unknown: measured[ch].add(i)
            z,a=world.measure(q,ch)
            if z=='near':
                assert world.clear(q,ch); cleared+=1; unknown.discard(ch); active.pop(ch,None)
            elif z=='direction':
                if ch in unknown: unknown.discard(ch); active[ch]=P.Src(q,a)
                else: active[ch].add(q,a)
            if cleared==16: break
    if cleared<16:
        for ch in unknown: assert len(measured[ch])==len(Q)   # 覆盖证书
    assert all(s['cleared'] for s in world.sources.values()), '漏清'
    return world

def per_source(C,mixed,Q,**kw):
    return st.mean(solve_x(J.World(copy.deepcopy(s),i),mixed,Q,**kw).time/len(s) for i,s in enumerate(C))

if __name__=='__main__':
    rng=random.Random(1)
    C3=[P.gen(rng,n,False) for n in (10,13,16) for _ in range(10)]
    C4=[P.gen(rng,n,True) for n in (10,13,16) for _ in range(10)]
    base3=st.mean((lambda w:(J.solve(w,False),w.time/len(s))[1])(J.World(copy.deepcopy(s),i)) for i,s in enumerate(C3))
    base4=st.mean((lambda w:(J.solve(w,True),w.time/len(s))[1])(J.World(copy.deepcopy(s),i)) for i,s in enumerate(C4))
    print('方案一每源平均：问题三 %.0f s，问题四 %.0f s'%(base3,base4))
    xs=[0,300,600,1000,2000,INF]; fmt=lambda v:'inf' if v==INF else str(v)
    for label,C,mixed,Q in (('问题三 7点网',C3,False,J.omni_points()),('问题四 27点网',C4,True,P.net990())):
        print('\n%s：每源平均 s（行 r_ok，列 x）'%label)
        print('r_ok\\x '+' '.join('%6s'%fmt(x) for x in xs))
        for r in (80,150,INF):
            print('%6s '%fmt(r)+' '.join('%6.0f'%per_source(C,mixed,Q,x=x,r_ok=r) for x in xs))
        print('关掉覆盖点顺带补测（x=600, r_ok=150）：%.0f'%per_source(C,mixed,Q,x=600,r_ok=150,probe=False))
    print('\n问题三 覆盖网对比（x=600, r_ok=150）')
    for name,Q in (('7点 中心+6@1200',J.omni_points()),('8边形@950',ring(8,950)),('10边形@890',ring(10,890)),('12边形@860',ring(12,860))):
        print('  %-16s %4.0f s/源'%(name,per_source(C3,False,Q,x=600,r_ok=150)))
