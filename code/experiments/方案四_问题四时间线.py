"""【分析】问题四（方案四）全时间线记账：按阶段 × 动作拆解，并统计每源 / 每空频道的开销。

阶段：scan（覆盖巡回与覆盖点扫描）、enroute（顺路清除）、final（覆盖完成后集中清除）、fallback（75×3 兜底）。
动作：move / measure（unknown 扫未确认频道、extra 顺带补测、local_probe 局部补测）/ switch / clear（ok、miss）。
本地仿真，非官方成绩。运行：python 方案四_问题四时间线.py（约 1 分钟）
输出：results/方案四_问题四时间线输出.txt、results/方案四_问题四时间线.json
"""
import math, copy, json, statistics as st, importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent
_s=importlib.util.spec_from_file_location('L',str(HERE/'方案四_实验台.py')); L=importlib.util.module_from_spec(_s); _s.loader.exec_module(L)
J=L.J; dist=L.dist
CFG=L.cfg(**L.CFG4); NET=L.NET4_V4()
PHASE=['scan']
class Prof(J.World):
    def __init__(s,src,salt):
        super().__init__(src,salt); s.acc={}; s.ch={}; s.nmeas={}; s.res={}
    def add(s,k,v,ch=None):
        s.acc[k]=s.acc.get(k,0)+v
        if ch is not None: s.ch[ch]=s.ch.get(ch,0)+v
    def measure(s,p,ch,kind='unknown'):
        d=dist(s.pos,p); sw=int(ch!=s.channel); r=super().measure(p,ch); ph=PHASE[0]
        s.add(f'{ph}_move',d/5,ch if ph!='scan' else None); s.add(f'{ph}_measure_{kind}',5.,ch); s.add('switch',sw,ch)
        s.nmeas[kind]=s.nmeas.get(kind,0)+1; s.res[r[0]]=s.res.get(r[0],0)+1
        return r
    def clear(s,p,ch):
        d=dist(s.pos,p); r=super().clear(p,ch); ph=PHASE[0]
        s.add(f'{ph}_move',d/5,ch); s.add(f'{ph}_clear_{"ok" if r else "miss"}',5. if r else 3.,ch)
        return r
def solve_prof(world,net,C):
    Q=L.tour_nn2opt(net); order=list(range(len(Q)))
    unknown=set(range(1,21)); active={}; cleared=0; measured={c:set() for c in unknown}
    pend=lambda i:[c for c in unknown if i not in measured[c]]
    stat={'probes':0,'fallback':set()}
    def local(ch,src):
        nonlocal cleared
        probes=0
        while True:
            c,r=src.RC()
            if r<=19.5:
                assert world.clear(c,ch); cleared+=1; return
            cc=L.cover_centers(src.P)
            if len(cc)<=C['cover_k']:
                cur=world.pos; rem=cc[:]
                while rem:
                    q=min(rem,key=lambda q:dist(cur,q)); rem.remove(q); cur=q
                    if world.clear(q,ch): cleared+=1; return
                raise AssertionError('cover failed')
            if probes>=C['lp_max']: break
            _,ang=L.axis(src.P); dp=max(r+15,min(C['lp_cap'],dist(world.pos,c)))
            cand=[]
            for k in range(36):
                phi=2*math.pi*k/36
                if abs(math.sin(phi-ang))<math.sin(math.radians(C['lp_angle'])): continue
                p=(c[0]+dp*math.cos(phi),c[1]+dp*math.sin(phi))
                if all(dist(p,dd)>=1 for dd in src.det): cand.append(p)
            if not cand: break
            dets=[math.atan2(dd[1]-c[1],dd[0]-c[0]) for dd in src.det]
            ad=lambda a,b:abs(math.atan2(math.sin(a-b),math.cos(a-b)))
            risk=lambda p:min(ad(math.atan2(p[1]-c[1],p[0]-c[0]),b) for b in dets)
            p=min(cand,key=lambda p:(dist(p,world.pos)/5+(0 if risk(p)<math.radians(60) else 60),p[0],p[1]))
            probes+=1; stat['probes']+=1
            z,a=world.measure(p,ch,'local_probe')
            if z=='near':
                assert world.clear(p,ch); cleared+=1; return
            if z=='direction': src.add(p,a)
        old=PHASE[0]; PHASE[0]='fallback'; stat['fallback'].add(ch)
        try:
            for cpt,_ in J.fallback_cells(src.P,src.first,src.theta):
                if world.clear(cpt,ch): cleared+=1; return
            for cpt,_ in J.fallback_cells(None,src.first,src.theta):
                if world.clear(cpt,ch): cleared+=1; return
            raise AssertionError('exhausted')
        finally: PHASE[0]=old
    def scan(i):
        nonlocal cleared
        q=Q[i]
        for ch in sorted(pend(i),key=lambda c:(c!=world.channel,c)):
            measured[ch].add(i)
            z,a=world.measure(q,ch,'unknown')
            if z=='near':
                assert world.clear(q,ch); cleared+=1; unknown.discard(ch); active.pop(ch,None)
            elif z=='direction': unknown.discard(ch); active[ch]=L.Src(q,a)
            if cleared==16: return
        for ch in [c for c,s in active.items() if s.RC()[1]>19.5 and J.radius(s.P,q)<=1500 and L.good_geom(s,q,C['probe_angle'])]:
            if ch not in active: continue
            z,a=world.measure(q,ch,'extra')
            if z=='near':
                assert world.clear(q,ch); cleared+=1; active.pop(ch,None)
            elif z=='direction': active[ch].add(q,a)
            if cleared==16: return
    while cleared<16:
        todo=[i for i in order if pend(i)]
        if not todo:
            if not active: break
            PHASE[0]='final'
            cs={ch:active[ch].RC()[0] for ch in active}
            seq=L.alns_order(list(cs.values()),world.pos,C['alns_iter']); inv={v:k for k,v in cs.items()}
            for pt in seq:
                ch=inv[pt]
                if ch in active: local(ch,active.pop(ch))
            PHASE[0]='scan'; continue
        nxt=Q[todo[0]]; best=None
        for ch,s in active.items():
            c,r=s.RC()
            if r>C['r_ok']: continue
            det=dist(world.pos,c)+dist(c,nxt)-dist(world.pos,nxt)
            if det<=C['x'] and (best is None or det<best[0]): best=(det,ch)
        if best:
            PHASE[0]='enroute'; local(best[1],active.pop(best[1])); PHASE[0]='scan'; continue
        scan(todo[0]); order.remove(todo[0])
    assert all(s['cleared'] for s in world.sources.values())
    return stat
GROUP={'覆盖巡回·移动':['scan_move'],'覆盖点·扫未确认频道':['scan_measure_unknown'],'覆盖点·顺带补测':['scan_measure_extra'],
 '顺路清除·移动':['enroute_move'],'顺路清除·局部补测':['enroute_measure_local_probe'],'顺路清除·清除动作':['enroute_clear_ok','enroute_clear_miss'],
 '最终集中清除·移动':['final_move'],'最终清除·局部补测':['final_measure_local_probe'],'最终清除·清除动作':['final_clear_ok','final_clear_miss'],
 '兜底·移动':['fallback_move'],'兜底·清除尝试':['fallback_clear_ok','fallback_clear_miss'],
 '近距直接清除':['scan_clear_ok','scan_clear_miss'],'切换频道':['switch']}
if __name__=='__main__':
    rows=[]; C4=L.cases(1)[1]; out=[]
    def log(s): out.append(s); print(s,flush=True)
    for i,src in enumerate(C4):
        PHASE[0]='scan'; w=Prof(copy.deepcopy(src),i); stat=solve_prof(w,NET,CFG)
        empty=[c for c in range(1,21) if c not in src]
        rows.append(dict(n=len(src),time=w.time,acc=dict(w.acc),nmeas=dict(w.nmeas),res=dict(w.res),
                         empty_time=sum(w.ch.get(c,0) for c in empty),src_time=sum(w.ch.get(c,0) for c in src),
                         fallback=len(stat['fallback']),probes=stat['probes']))
    m=lambda f:st.mean(f(r) for r in rows); tot=m(lambda r:r['time'])
    log('问题四 · 方案四 · 30 局（N=10/13/16 各 10 局）  单局平均总虚拟时间 %.0f s'%tot)
    log('\n%-22s %8s %7s'%('分项','秒','占比'))
    for g,ks in GROUP.items():
        v=sum(m(lambda r,k=k:r['acc'].get(k,0)) for k in ks)
        if v>0.5: log('%-22s %8.0f %6.1f%%'%(g,v,100*v/tot))
    log('%-22s %8.0f %6.1f%%'%('合计',tot,100))
    log('\n检测次数：扫未确认频道 %.0f，顺带补测 %.0f，局部补测 %.0f；返回 no_signal %.0f / direction %.0f / near %.0f'%(
        m(lambda r:r['nmeas'].get('unknown',0)),m(lambda r:r['nmeas'].get('extra',0)),m(lambda r:r['nmeas'].get('local_probe',0)),
        m(lambda r:r['res'].get('no_signal',0)),m(lambda r:r['res'].get('direction',0)),m(lambda r:r['res'].get('near',0))))
    log('花在最终判空的频道上 %.0f s（%.0f%%）；花在真实源频道上 %.0f s'%(m(lambda r:r['empty_time']),100*m(lambda r:r['empty_time'])/tot,m(lambda r:r['src_time'])))
    log('进入兜底的源 %.1f 个/局；局部补测 %.1f 次/局'%(m(lambda r:r['fallback']),m(lambda r:r['probes'])))
    log('\n按源数分（秒）')
    log('%-4s %8s %8s %10s %10s %8s %8s %8s %10s'%('N','总时间','每源','覆盖移动','扫未确认','顺路清除','最终清除','兜底','空频道'))
    for n in (10,13,16):
        sub=[r for r in rows if r['n']==n]; f=lambda k:st.mean(r['acc'].get(k,0) for r in sub)
        log('%-4d %8.0f %8.0f %10.0f %10.0f %8.0f %8.0f %8.0f %10.0f'%(n,st.mean(r['time'] for r in sub),st.mean(r['time']/r['n'] for r in sub),
            f('scan_move'),f('scan_measure_unknown'),
            f('enroute_move')+f('enroute_measure_local_probe')+f('enroute_clear_ok')+f('enroute_clear_miss'),
            f('final_move')+f('final_measure_local_probe')+f('final_clear_ok')+f('final_clear_miss'),
            f('fallback_move')+f('fallback_clear_ok')+f('fallback_clear_miss'),st.mean(r['empty_time'] for r in sub)))
    (HERE/'results'/'方案四_问题四时间线输出.txt').write_text('\n'.join(out)+'\n',encoding='utf-8')
    json.dump(rows,open(HERE/'results'/'方案四_问题四时间线.json','w'),ensure_ascii=False)
