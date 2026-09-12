"""【方案五候选】问题四的三项改进 A / B / C，可单独或组合开关，并与方案四在三批案例上对比 + 保证性压力测试。

A 更短的合格覆盖网：三角格 h=900 m、偏移 (0, 487.0) m、旋转 10°，27 点，巡回 23.9 km
  （方案四为 h=950、25.1 km）。证书与最终文档 §5.2 相同（h≤1000），已用位置×朝向稠密复验：漏测 0。
B 联合重规划：每一步把“还有未确认频道的覆盖点”和“区域半径≤r_ok 的已发现源”放在一起重排最近邻路线，
  执行排在最前的那个节点；不再使用固定巡回 + 绕行阈值 x。
C 计数提前停：一旦“已清除 + 已发现”达到 16，其余频道必为空（题目保证总数≤16，每频道至多一个源），
  立即停止覆盖，转入集中清除。注意这是与覆盖证书并列的另一条判空依据。

问题三不适用：同样的 B 用在问题三上更慢（见文档），问题三保持方案四。
本地仿真，非官方成绩。运行：python 方案五_候选ABC.py（约 6–8 分钟）；--quick 跳过压力测试。
输出：results/方案五_候选ABC输出.txt
"""
import argparse, math, copy, random, hashlib, statistics as st, importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent
_s=importlib.util.spec_from_file_location('L',str(HERE/'方案四_实验台.py')); L=importlib.util.module_from_spec(_s); _s.loader.exec_module(L)
J=L.J; dist=L.dist; CFG=L.cfg(**L.CFG4)
NET_A=lambda: L.lattice(900.,0.,487.0,math.radians(10.))     # A
NET_4=lambda: L.NET4_V4()                                    # 方案四
def solve_v5(world,mixed,net,C,B=True,Cstop=True):
    """B=True 用联合重规划；B=False 用方案四的固定巡回+x；Cstop=True 启用计数提前停。"""
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
        if B:
            ready=[c for c,s in active.items() if s.RC()[1]<=C['r_ok']]
            nodes=[('scan',i,Q[i]) for i in todo]+[('clear',c,active[c].RC()[0]) for c in (ready if todo else list(active))]
            if not nodes:
                ch=min(active,key=lambda c:dist(world.pos,active[c].RC()[0])); L.local_clear(world,ch,active.pop(ch),C); cleared+=1; continue
            pts=[p for _,_,p in nodes]; seq=L.tour_nn2opt(pts,world.pos)
            kind,key,_=nodes[pts.index(seq[0])]
            if kind=='clear': L.local_clear(world,key,active.pop(key),C); cleared+=1
            else: scan(key); rem.remove(key)
        else:
            if not todo:
                cs={c:active[c].RC()[0] for c in active}
                seq=L.alns_order(list(cs.values()),world.pos,C['alns_iter']); inv={v:k for k,v in cs.items()}
                for pt in seq:
                    ch=inv[pt]
                    if ch in active: L.local_clear(world,ch,active.pop(ch),C); cleared+=1
                continue
            nxt=Q[todo[0]]; best=None
            for ch,s in active.items():
                c,r=s.RC()
                if r>C['r_ok']: continue
                det=dist(world.pos,c)+dist(c,nxt)-dist(world.pos,nxt)
                if det<=C['x'] and (best is None or det<best[0]): best=(det,ch)
            if best: L.local_clear(world,best[1],active.pop(best[1]),C); cleared+=1; continue
            scan(todo[0]); rem.remove(todo[0])
    if cleared<16 and not (Cstop and cleared+len(active)>=16):
        for ch in unknown: assert len(measured[ch])==len(Q)   # 覆盖证书
    assert all(s['cleared'] for s in world.sources.values()),'漏清'
    return world
def h01(*k): return int(hashlib.md5(repr(k).encode()).hexdigest()[:12],16)/16**12
ERR={'交接误差场':None,'每点独立均匀':lambda p,c,s:2*h01(round(p[0],3),round(p[1],3),c,s)-1,
     '恒 +1°':lambda p,c,s:1.0,'恒 −1°':lambda p,c,s:-1.0,
     '每点独立 ±1°':lambda p,c,s:1.0 if h01(round(p[0],3),round(p[1],3),c,s)<.5 else -1.0}
class W(J.World):
    def __init__(s,src,salt,ef): super().__init__(src,salt); s.ef=ef
    def measure(s,p,ch):
        if s.ef is None: return super().measure(p,ch)
        s.move(p); sw=int(ch!=s.channel); s.channel=ch; s.time+=5+sw; s.detect+=5; s.switch+=sw; s.actions+=1
        src=s.sources.get(ch)
        if src is None or src['cleared']: return 'no_signal',None
        d=dist(p,src['g'])
        if d>src['r'] or (src['type']=='D' and J.dot((p[0]-src['g'][0],p[1]-src['g'][1]),src['u'])<-1e-10): return 'no_signal',None
        if d<=5: return 'near',None
        ang=math.degrees(math.atan2(src['g'][1]-p[1],src['g'][0]-p[0]))+s.ef(p,ch,s.salt)
        return 'direction',math.radians(round(ang%360,2)%360)
def per_source(C4,net,**kw):
    return [solve_v5(J.World(copy.deepcopy(s),i),True,net,CFG,**kw).time/len(s) for i,s in enumerate(C4)]
if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--quick',action='store_true'); a=ap.parse_args()
    out=[]; log=lambda s:(out.append(s),print(s,flush=True))
    log('覆盖网：方案四 h=950 共 %d 点；A 方案 h=900 共 %d 点'%(len(NET_4()),len(NET_A())))
    log('\n问题四 每源平均定位清除时间 / s')
    log('%-26s %8s %8s %8s'%('组合','训练集','验证集A','验证集B'))
    combos=[('方案四（基准）',NET_4,dict(B=False,Cstop=False)),('A 仅换覆盖网',NET_A,dict(B=False,Cstop=False)),
            ('B 仅联合重规划',NET_4,dict(B=True,Cstop=False)),('C 仅计数提前停',NET_4,dict(B=False,Cstop=True)),
            ('A+B',NET_A,dict(B=True,Cstop=False)),('A+C',NET_A,dict(B=False,Cstop=True)),
            ('B+C',NET_4,dict(B=True,Cstop=True)),('A+B+C',NET_A,dict(B=True,Cstop=True))]
    detail={}
    for name,netf,kw in combos:
        net=netf(); vals=[]
        for seed in (1,202,777):
            ps=per_source(L.cases(seed)[1],net,**kw); vals.append(st.mean(ps))
            if name=='A+B+C' or name=='方案四（基准）':
                detail.setdefault(name,{})[seed]=[st.mean(ps[i*10:(i+1)*10]) for i in range(3)]
        log('%-26s %8.1f %8.1f %8.1f'%(name,*vals))
    log('\n按源数分（每源平均 s；N=10 / 13 / 16）')
    for name in ('方案四（基准）','A+B+C'):
        for seed,tag in ((1,'训练'),(202,'验证A'),(777,'验证B')):
            log('  %-12s %-4s  %5.0f / %5.0f / %5.0f'%(name,tag,*detail[name][seed]))
    if not a.quick:
        log('\n保证性压力测试（问题四，A+B+C）')
        tot=0; fail=0; times=[]
        net=NET_A()
        for en,ef in ERR.items():
            for rmode in ('随机','全 1000 m'):
                for layout in ('圆内均匀','边界朝外'):
                    rng=random.Random(abs(hash(en))%97+len(rmode)+2*len(layout))
                    for n in (10,13,16):
                        for rep in range(2):
                            src={}
                            for k,ch in enumerate(rng.sample(range(1,21),n)):
                                if layout=='圆内均匀':
                                    aa=rng.random()*2*math.pi; rr=1800*math.sqrt(rng.random()); kind='D' if rng.random()<.65 else 'O'; ang=rng.random()*2*math.pi
                                else:
                                    aa=2*math.pi*k/n+rng.uniform(-.05,.05); rr=rng.uniform(1700,1800); kind='D'; ang=aa
                                r=1000. if rmode=='全 1000 m' else rng.uniform(1000,1500)
                                src[ch]=J.source((rr*math.cos(aa),rr*math.sin(aa)),r,kind,ang)
                            tot+=1
                            try:
                                w=solve_v5(W(src,rep,ef),True,net,CFG); times.append(w.time/n)
                            except AssertionError as e:
                                fail+=1; log('  失败：%s %s %s N=%d rep=%d —— %s'%(en,rmode,layout,n,rep,e))
        log('  共 %d 局，未全清 %d 局；每源平均 %.0f s，最大 %.0f s'%(tot,fail,st.mean(times),max(times)))
    (HERE/'results'/'方案五_候选ABC输出.txt').write_text('\n'.join(out)+'\n',encoding='utf-8')
