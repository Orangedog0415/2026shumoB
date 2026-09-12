"""【5.3】把每个待清源表示成“服务簇”（可行清除点集合，TSPN 近似），并试验 regret-2 插入构造路线。

服务簇：区域半径 ≤19.5 m → 只有区域中心一个服务点；否则取覆盖该区域的 ≤6 个 20 m 清除圆中心；
        路线决策时用“离当前位置最近的那个服务点”作为该源的节点坐标（原来一律用区域中心）。
结论：服务簇有小幅收益（约 −0.7%，已并入方案六）；本文实现的 regret-2 反而更慢（+4%），未采用。
只用标准库。运行：python 方案五_5.3_服务簇与regret.py（约 5 分钟）；输出 results/方案五_5.3_输出.txt
"""
import math,copy,json,statistics as st,importlib.util,sys
from pathlib import Path
H=Path(__file__).resolve().parent
_s=importlib.util.spec_from_file_location('L',str(H/'方案四_实验台.py')); L=importlib.util.module_from_spec(_s); _s.loader.exec_module(L)
J=L.J; dist=L.dist; CFG=L.cfg(**L.CFG4)
NET=L.NET4_V6()
def service_points(src,C):
    """模式1：区域半径≤19.5 → 中心；模式2：≤cover_k 个清除格中心；否则退化为中心。"""
    c,r=src.RC()
    if r<=19.5: return [c]
    cc=L.cover_centers(src.P)
    return cc if len(cc)<=C['cover_k'] else [c]
def regret2(nodes,start):
    """nodes: [(key, [candidate points])]；返回访问顺序（key 列表）。"""
    route=[]; pos=start; un=list(nodes)
    seq=[]
    while un:
        best=None
        for idx,(k,pts) in enumerate(un):
            costs=sorted(min(dist(p,q) for q in pts) for p in ([pos] if not seq else [pos]))  # 简化：从当前位置起的最近距离
            d1=min(dist(pos,q) for q in pts)
            d2=min((min(dist(p2,q) for q in pts) for p2 in [n[1][0] for j,n in enumerate(un) if j!=idx]),default=d1)
            regret=d2-d1
            val=(-regret,d1)
            if best is None or val<best[0]: best=(val,idx,d1)
        _,idx,_=best
        k,pts=un.pop(idx); seq.append(k)
        pos=min(pts,key=lambda q:dist(pos,q))
    return seq
def solve_53(world,net,C,cluster=True,regret=True,Cstop=True):
    Q=L.tour_nn2opt(net); rem=list(range(len(Q)))
    unknown=set(range(1,21)); active={}; cleared=0; measured={c:set() for c in unknown}
    pend=lambda i:[c for c in unknown if i not in measured[c]]
    def scan(i):
        nonlocal cleared
        q=Q[i]
        chans=sorted(pend(i),key=lambda c:(c!=world.channel,c))
        extra=[c for c,s in active.items() if s.RC()[1]>19.5 and J.radius(s.P,q)<=1500 and L.good_geom(s,q,C['probe_angle'])]
        for ch in chans+extra:
            if ch in unknown: measured[ch].add(i)
            z,a=world.measure(q,ch)
            if z=='near':
                assert world.clear(q,ch); cleared+=1; unknown.discard(ch); active.pop(ch,None)
            elif z=='direction':
                if ch in unknown: unknown.discard(ch); active[ch]=L.Src(q,a)
                else: active[ch].add(q,a)
            if cleared==16 or (Cstop and cleared+len(active)>=16): return
    while cleared<16:
        todo=[] if (Cstop and cleared+len(active)>=16) else [i for i in rem if pend(i)]
        if not todo and not active: break
        ready=[c for c,s in active.items() if s.RC()[1]<=C['r_ok']]
        nodes=[(('scan',i),[Q[i]]) for i in todo]+[(('clear',c),(service_points(active[c],C) if cluster else [active[c].RC()[0]])) for c in (ready if todo else list(active))]
        if not nodes:
            ch=min(active,key=lambda c:dist(world.pos,active[c].RC()[0])); L.local_clear(world,ch,active.pop(ch),C); cleared+=1; continue
        if regret:
            seq=regret2(nodes,world.pos); kind,key=seq[0]
        else:
            pts=[min(p,key=lambda q:dist(world.pos,q)) for _,p in nodes]
            order=L.tour_nn2opt(pts,world.pos); kind,key=nodes[pts.index(order[0])][0]
        if kind=='clear': L.local_clear(world,key,active.pop(key),C); cleared+=1
        else: scan(key); rem.remove(key)
    if cleared<16 and not (Cstop and cleared+len(active)>=16):
        for ch in unknown: assert len(measured[ch])==len(Q)
    assert all(s['cleared'] for s in world.sources.values())
    return world
if __name__=='__main__':
    def ev(C4,**kw): return st.mean(solve_53(J.World(copy.deepcopy(s),i),NET,CFG,**kw).time/len(s) for i,s in enumerate(C4))
    out=[]; log=lambda t:(out.append(t),print(t,flush=True))
    log('%-30s %8s %8s %8s'%('变体（均用方案六覆盖网 + 计数提前停）','训练','验证A','验证B'))
    for name,kw in (('B（最近邻，区域中心）',dict(cluster=False,regret=False)),
                    ('5.3a 服务簇 + 最近邻',dict(cluster=True,regret=False)),
                    ('5.3b 区域中心 + regret-2',dict(cluster=False,regret=True)),
                    ('5.3c 服务簇 + regret-2',dict(cluster=True,regret=True))):
        vals=[ev(L.cases(sd)[1],**kw) for sd in (1,202,777)]
        log('%-30s %8.1f %8.1f %8.1f'%(name,*vals))
    (H/'results'/'方案五_5.3_输出.txt').write_text('\n'.join(out)+'\n',encoding='utf-8')
