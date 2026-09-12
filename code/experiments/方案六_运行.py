"""【方案六】问题四：非规则三角网（17.8 km）+ 联合重规划 + 计数提前停 + 服务簇；问题三沿用方案四。

相对方案四的三处改动（编号见 docs/review/方案五_5x实验与方案六.md）：
  5.2  覆盖网从 h=950 规则格网（27 点、25.1 km）换成可认证的非规则三角网（27 点、17.8 km）
  5.3a 路线决策里把每个待清源表示成“服务簇”（≤6 个 20 m 清除圆中心），取离当前位置最近的那个作为节点
  B/C  联合重规划（每步对“未测完的覆盖点 + 可清源”重排路线，执行第一个节点）+ 计数提前停（发现满 16 个即停覆盖）
保证层不变：三角网证书（三边 ≤1000 m + 凸包含圆）、频道状态机、75×3 有限兜底、1.005°/999 m/19.5 m。
本地仿真，非官方成绩。运行：python 方案六_运行.py（约 5 分钟）；--quick 跳过压力测试。
输出：results/方案六_运行输出.txt
"""
import argparse, math, copy, random, hashlib, statistics as st, importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent
_s=importlib.util.spec_from_file_location('L',str(HERE/'方案四_实验台.py')); L=importlib.util.module_from_spec(_s); _s.loader.exec_module(L)
J=L.J; dist=L.dist; CFG=L.cfg(**L.CFG4); NET6=L.NET4_V6(); NET4=L.NET4_V4(); NET3=L.NET3()
def service_points(src,C):
    c,r=src.RC()
    if r<=19.5: return [c]
    cc=L.cover_centers(src.P)
    return cc if len(cc)<=C['cover_k'] else [c]
def solve6(world,net,C,cluster=True,joint=True,count_stop=True):
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
            if cleared==16 or (count_stop and cleared+len(active)>=16): return
    while cleared<16:
        todo=[] if (count_stop and cleared+len(active)>=16) else [i for i in rem if pend(i)]
        if not todo and not active: break
        ready=[c for c,s in active.items() if s.RC()[1]<=C['r_ok']]
        nodes=[(('scan',i),[Q[i]]) for i in todo]+[(('clear',c),(service_points(active[c],C) if cluster else [active[c].RC()[0]])) for c in (ready if todo else list(active))]
        if not nodes:
            ch=min(active,key=lambda c:dist(world.pos,active[c].RC()[0])); L.local_clear(world,ch,active.pop(ch),C); cleared+=1; continue
        pts=[min(p,key=lambda q:dist(world.pos,q)) for _,p in nodes]
        order=L.tour_nn2opt(pts,world.pos) if joint else [pts[0]]
        kind,key=nodes[pts.index(order[0])][0]
        if kind=='clear': L.local_clear(world,key,active.pop(key),C); cleared+=1
        else: scan(key); rem.remove(key)
    if cleared<16 and not (count_stop and cleared+len(active)>=16):
        for ch in unknown: assert len(measured[ch])==len(Q)      # 覆盖证书
    assert all(s['cleared'] for s in world.sources.values()),'漏清'
    return world
def h01(*k): return int(hashlib.md5(repr(k).encode()).hexdigest()[:12],16)/16**12
ERR={'交接误差场':None,'每点独立均匀':lambda p,c,s:2*h01(round(p[0],3),round(p[1],3),c,s)-1,
     '恒 +1°':lambda p,c,s:1.0,'恒 −1°':lambda p,c,s:-1.0,'每点独立 ±1°':lambda p,c,s:1.0 if h01(round(p[0],3),round(p[1],3),c,s)<.5 else -1.0}
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
if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--quick',action='store_true'); a=ap.parse_args()
    out=[]; log=lambda s:(out.append(s),print(s,flush=True))
    T=L.tour_nn2opt(NET6); route=dist((0,0),T[0])+sum(dist(T[i],T[i+1]) for i in range(len(T)-1))
    log('方案六：问题四覆盖网 %d 点、巡回 %.0f m（方案四 %d 点、25 111 m）；问题三沿用方案四（正八边形 974 m）'%(len(NET6),route,len(NET4)))
    log('\n问题四 每源平均定位清除时间 / s')
    log('%-14s %8s %8s %8s'%('','训练集','验证集A','验证集B'))
    r4={}; r6={}
    for sd in (1,202,777):
        C4=L.cases(sd)[1]
        r4[sd]=[L.solve(J.World(copy.deepcopy(s),i),True,NET4,CFG).time/len(s) for i,s in enumerate(C4)]
        r6[sd]=[solve6(J.World(copy.deepcopy(s),i),NET6,CFG).time/len(s) for i,s in enumerate(C4)]
    log('%-14s %8.1f %8.1f %8.1f'%('方案四',*[st.mean(r4[sd]) for sd in (1,202,777)]))
    log('%-14s %8.1f %8.1f %8.1f'%('方案六',*[st.mean(r6[sd]) for sd in (1,202,777)]))
    log('%-14s %7.1f%% %7.1f%% %7.1f%%'%('变化',*[100*(st.mean(r6[sd])/st.mean(r4[sd])-1) for sd in (1,202,777)]))
    log('\n按源数分（N=10 / 13 / 16）')
    for sd,tag in ((1,'训练'),(202,'验证A'),(777,'验证B')):
        f=lambda r:'%.0f / %.0f / %.0f'%(st.mean(r[:10]),st.mean(r[10:20]),st.mean(r[20:]))
        log('  %-5s 方案四 %s → 方案六 %s'%(tag,f(r4[sd]),f(r6[sd])))
    q3=[st.mean([L.solve(J.World(copy.deepcopy(s),i),False,NET3,CFG).time/len(s) for i,s in enumerate(L.cases(sd)[0])]) for sd in (1,202,777)]
    log('\n问题三（沿用方案四，未改动）：%.1f / %.1f / %.1f s/源'%tuple(q3))
    if not a.quick:
        log('\n保证性压力测试（问题四·方案六）')
        tot=fail=0; times=[]
        for en,ef in ERR.items():
            for rmode in ('随机','全 1000 m'):
                for layout in ('圆内均匀','边界朝外'):
                    rng=random.Random(abs(hash(en))%97+len(rmode)+2*len(layout))
                    for n in (10,13,16):
                        for rep in range(3):
                            src={}
                            for k,ch in enumerate(rng.sample(range(1,21),n)):
                                if layout=='圆内均匀':
                                    aa=rng.random()*2*math.pi; rr=1800*math.sqrt(rng.random()); kind='D' if rng.random()<.65 else 'O'; ang=rng.random()*2*math.pi
                                else:
                                    aa=2*math.pi*k/n+rng.uniform(-.05,.05); rr=rng.uniform(1700,1800); kind='D'; ang=aa
                                r=1000. if rmode=='全 1000 m' else rng.uniform(1000,1500)
                                src[ch]=J.source((rr*math.cos(aa),rr*math.sin(aa)),r,kind,ang)
                            tot+=1
                            try: times.append(solve6(W(src,rep,ef),NET6,CFG).time/n)
                            except AssertionError as e: fail+=1; log('  失败：%s %s %s N=%d rep=%d —— %s'%(en,rmode,layout,n,rep,e))
        log('  共 %d 局，未全清 %d 局；每源平均 %.0f s，最大 %.0f s'%(tot,fail,st.mean(times),max(times)))
    (HERE/'results'/'方案六_运行输出.txt').write_text('\n'.join(out)+'\n',encoding='utf-8')
