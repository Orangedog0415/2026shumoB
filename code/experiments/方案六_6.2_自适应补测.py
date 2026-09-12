"""【6.2】GT06 的“自适应补测”两段式策略：先用稀疏网粗探，只对未解频道再走加密点。

来源：GT06《B 题解题文档》§4.4.4（表 17）。其推理是：七点网对定向源平均漏测 65%，但被漏测的
      频道只占少数，只对这批频道沿加密环复测即可，静态零漏测网当兜底。
移植方式：把覆盖网拆成“粗探集 A + 加密集 B”，A 走完之前不解锁 B；仍未检出的频道才继续走 B，
      因此最终证书与方案六完全一致（未检出频道必定被覆盖网的全部点测过）。
三种粗探集：
  A1  从 NET4_V6 里贪心选出的“半径 1000 m 距离覆盖”子集（加密集 = 其余点，全集仍是 27 点）
  A2  问题三的正八边形 974 m 网（GT06 原味：粗探网不是冗余网的子集，全集 = 8+27 = 35 点）
  A3  GT06 的七点网（中心 + 半径 1122.96 m 六边形），全集 = 7+27 = 34 点
运行：python 方案六_6.2_自适应补测.py   输出：results/方案六_6.2_输出.txt
"""
import math, copy, statistics as st, importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent
_s=importlib.util.spec_from_file_location('L',str(HERE/'方案四_实验台.py')); L=importlib.util.module_from_spec(_s); _s.loader.exec_module(L)
J=L.J; dist=L.dist; CFG=L.cfg(**L.CFG4); NET6=L.NET4_V6()

def service_points(src,C):
    c,r=src.RC()
    if r<=19.5: return [c]
    cc=L.cover_centers(src.P)
    return cc if len(cc)<=C['cover_k'] else [c]

def solve62(world,stages,C,count_stop=True):
    """stages = [粗探集, 加密集, ...]；前一阶段的点全部测完才解锁下一阶段。stages=[net] 即方案六。"""
    Q=[];bound=[]
    for s in stages:
        Q+=[tuple(p) for p in s]; bound.append(len(Q))
    unknown=set(range(1,21)); active={}; cleared=0; measured={c:set() for c in unknown}
    stage=0; rem=list(range(bound[0]))
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
        stop=count_stop and cleared+len(active)>=16
        todo=[] if stop else [i for i in rem if pend(i)]
        while not todo and not stop and stage+1<len(bound):      # 解锁下一阶段
            stage+=1; rem=list(range(bound[stage-1],bound[stage]))
            todo=[i for i in rem if pend(i)]
        if not todo and not active: break
        ready=[c for c,s in active.items() if s.RC()[1]<=C['r_ok']]
        nodes=[(('scan',i),[Q[i]]) for i in todo]+[(('clear',c),service_points(active[c],C)) for c in (ready if todo else list(active))]
        if not nodes:
            ch=min(active,key=lambda c:dist(world.pos,active[c].RC()[0])); L.local_clear(world,ch,active.pop(ch),C); cleared+=1; continue
        pts=[min(p,key=lambda q:dist(world.pos,q)) for _,p in nodes]
        order=L.tour_nn2opt(pts,world.pos)
        kind,key=nodes[pts.index(order[0])][0]
        if kind=='clear': L.local_clear(world,key,active.pop(key),C); cleared+=1
        else: scan(key); rem.remove(key)
    if cleared<16 and not (count_stop and cleared+len(active)>=16):
        for ch in unknown: assert len(measured[ch])==len(Q)      # 覆盖证书：全集测完
    assert all(s['cleared'] for s in world.sources.values()),'漏清'
    return world

def cover_subset(net,R=1000.,step=40.):
    """从 net 里贪心选出一个“任一位置到子集某点 <=R”的子集（经典集合覆盖贪心）。"""
    S=[];r=0.
    while r<=1800.+1e-9:
        n=max(6,int(2*math.pi*r/step)) if r>0 else 1
        S+=[(r*math.cos(2*math.pi*k/n),r*math.sin(2*math.pi*k/n)) for k in range(n)]; r+=step
    unc=set(range(len(S))); sel=[]
    cov={i:{j for j in unc if dist(net[i],S[j])<=R} for i in range(len(net))}
    while unc:
        i=max(range(len(net)),key=lambda i:len(cov[i]&unc))
        if not (cov[i]&unc): break
        sel.append(i); unc-=cov[i]
    return [net[i] for i in sel],[net[i] for i in range(len(net)) if i not in sel]

if __name__=='__main__':
    out=[];log=lambda s:(out.append(s),print(s,flush=True))
    A1,B1=cover_subset(NET6)
    NET3=L.NET3()
    GT7=[(0.,0.)]+[(1122.96*math.cos(2*math.pi*k/6),1122.96*math.sin(2*math.pi*k/6)) for k in range(6)]
    def tl(net):
        T=L.tour_nn2opt([tuple(p) for p in net]); return dist((0,0),T[0])+sum(dist(T[i],T[i+1]) for i in range(len(T)-1))
    log('【6.2】自适应补测（粗探 + 按需加密）')
    log('  A1 = NET4_V6 的距离覆盖子集：%d 点、巡回 %.0f m；加密集 %d 点（全集仍 27 点）'%(len(A1),tl(A1),len(B1)))
    log('  A2 = 问题三正八边形 974 m：8 点、巡回 %.0f m；加密集 = 全部 27 点（全集 35 点）'%tl(NET3))
    log('  A3 = GT06 七点网 1122.96 m：7 点、巡回 %.0f m；加密集 = 全部 27 点（全集 34 点）'%tl(GT7))
    VAR=[('方案六（单段 27 点）',[NET6]),('6.2a A1 子集粗探',[A1,B1]),('6.2b A2 八边形粗探',[NET3,NET6]),('6.2c A3 七点网粗探',[GT7,NET6])]
    log('\n问题四 每源平均定位清除时间 / s')
    log('%-20s %8s %8s %8s'%('','训练集','验证A','验证B'))
    base=None
    for tag,stg in VAR:
        row=[]
        for sd in (1,202,777):
            C4=L.cases(sd)[1]
            row.append(st.mean([solve62(J.World(copy.deepcopy(s),i),stg,CFG).time/len(s) for i,s in enumerate(C4)]))
        if base is None: base=row
        log('%-20s %8.1f %8.1f %8.1f   (%+.1f%% / %+.1f%% / %+.1f%%)'%(tag,*row,*[100*(row[k]/base[k]-1) for k in range(3)]))
    log('\n按源数分（训练集 N=10 / 13 / 16）')
    for tag,stg in VAR:
        C4=L.cases(1)[1]
        r=[solve62(J.World(copy.deepcopy(s),i),stg,CFG).time/len(s) for i,s in enumerate(C4)]
        log('  %-20s %.0f / %.0f / %.0f'%(tag,st.mean(r[:10]),st.mean(r[10:20]),st.mean(r[20:])))
    (HERE/'results'/'方案六_6.2_输出.txt').write_text('\n'.join(out)+'\n',encoding='utf-8')
