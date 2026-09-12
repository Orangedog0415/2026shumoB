"""【6.3】用 GT06 的“背向不可测定理 + 朝向可行集”改造两处选点：补测点打分 与 顺路复测的取舍。

来源：GT06《B 题解题文档》式 (29)(34)。要点：定向源在背向半平面完全不可测，且可由历史检出点
      反推朝向的可行集，从而不去背向白测一次（5 s 检测 + 1 s 切换 + 往返移动）。
闭式推导：设已检出点相对源中心的方位为 beta_i，朝向 psi 必满足 |wrap(beta_i-psi)|<=90 度，
      故可行朝向集 = beta_i 的最小包围弧 [lo,hi]（张角 s）两侧各扩 90-s/2，宽度 180-s；
      从方位 phi 补测可检测 <=> psi 落在 [phi-90,phi+90]，于是
            frac(phi) = 1                                (phi 在 [lo,hi] 内)
                      = 1 - d(phi,[lo,hi]) / (180 - s)   (在外侧，线性衰减到 0)
      s >= 180 度时观测点已张成半平面以上，源必为全向，frac = 1。
      混合场景先验 0.35 为全向源，故 p_det(phi) = 0.35 + 0.65*frac(phi)。
两处落点：
  (i)  local_clear 的探测点打分：把原来的“risk<60 度”指示函数换成 (1-p_det)*W；
  (ii) 覆盖点上的“顺路复测”(extra)：原判据只有几何条件 good_geom，加一条 p_det >= tau 才复测。
运行：python 方案六_6.3_可检测锥选点.py   输出：results/方案六_6.3_输出.txt
注意：方案六_运行.py 自己加载了一份实验台模块，打补丁必须打到 R6.L 上（否则改动不生效）。
"""
import math, copy, statistics as st, importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent
_r=importlib.util.spec_from_file_location('R6',str(HERE/'方案六_运行.py')); R6=importlib.util.module_from_spec(_r); _r.loader.exec_module(R6)
L=R6.L; J=L.J; dist=L.dist; NET6=L.NET4_V6(); ORIG_LC=L.local_clear

def det_frac(bears,phi):
    """已检出方位集合 bears 下，从方位 phi 补测的“保证可检测”程度（1 = 必可测，0 = 完全无保证）。"""
    a=sorted(x%(2*math.pi) for x in bears)
    if len(a)==1: lo,s=a[0],0.
    else:
        g=[(a[(i+1)%len(a)]-a[i])%(2*math.pi) for i in range(len(a))]
        k=max(range(len(a)),key=lambda i:g[i]); lo=a[(k+1)%len(a)]; s=2*math.pi-g[k]
    if s>=math.pi: return 1.0
    t=(phi-lo)%(2*math.pi)
    if t<=s: return 1.0
    return max(0.,1.-min(t-s,2*math.pi-t)/(math.pi-s))
def pdet(src,q,pO=0.35):
    c,_=src.RC(); b=[math.atan2(d[1]-c[1],d[0]-c[0]) for d in src.det]
    return pO+(1-pO)*det_frac(b,math.atan2(q[1]-c[1],q[0]-c[0]))

def make_local_clear(W,keep_risk):
    def local_clear(world,ch,src,C):
        probes=0
        while True:
            c,r=src.RC()
            if r<=19.5:
                if world.clear(c,ch): return
                raise AssertionError('certified clear failed')
            cc=L.cover_centers(src.P)
            if len(cc)<=C['cover_k']:
                cur=world.pos; rem=cc[:]
                while rem:
                    q=min(rem,key=lambda q:dist(cur,q)); rem.remove(q); cur=q
                    if world.clear(q,ch): return
                raise AssertionError('cover failed')
            if probes>=C['lp_max']: break
            _,ang=L.axis(src.P)
            dp=max(r+15,min(C['lp_cap'],dist(world.pos,c)))
            cand=[]
            for k in range(36):
                phi=2*math.pi*k/36
                if abs(math.sin(phi-ang))<math.sin(math.radians(C['lp_angle'])): continue
                p=(c[0]+dp*math.cos(phi),c[1]+dp*math.sin(phi))
                if all(dist(p,dd)>=1 for dd in src.det): cand.append(p)
            if not cand: break
            dets=[math.atan2(dd[1]-c[1],dd[0]-c[0]) for dd in src.det]
            ad=lambda a,b:abs(math.atan2(math.sin(a-b),math.cos(a-b)))
            def risk(p):
                a=math.atan2(p[1]-c[1],p[0]-c[0]); return min(ad(a,b) for b in dets)
            def score(p):
                v=dist(p,world.pos)/5
                if keep_risk: v+=0 if risk(p)<math.radians(60) else 60
                if W>0:
                    ph=math.atan2(p[1]-c[1],p[0]-c[0])
                    v+=(1-(0.35+0.65*det_frac(dets,ph)))*W
                return (v,p[0],p[1])
            p=min(cand,key=score); probes+=1
            z,a=world.measure(p,ch)
            if z=='near':
                assert world.clear(p,ch); return
            if z=='direction': src.add(p,a)
        for cpt,_ in J.fallback_cells(src.P,src.first,src.theta):
            if world.clear(cpt,ch): return
        for cpt,_ in J.fallback_cells(None,src.first,src.theta):
            if world.clear(cpt,ch): return
        raise AssertionError('exhausted')
    return local_clear

def solve63(world,net,C,tau=0.):
    """方案六求解器 + 顺路复测的可检测性门槛 tau（tau=0 即方案六原版）。"""
    Q=L.tour_nn2opt(net); rem=list(range(len(Q)))
    unknown=set(range(1,21)); active={}; cleared=0; measured={c:set() for c in unknown}
    pend=lambda i:[c for c in unknown if i not in measured[c]]
    def scan(i):
        nonlocal cleared
        q=Q[i]
        chans=sorted(pend(i),key=lambda c:(c!=world.channel,c))
        extra=[c for c,s in active.items() if s.RC()[1]>19.5 and J.radius(s.P,q)<=1500
               and L.good_geom(s,q,C['probe_angle']) and (tau<=0 or pdet(s,q)>=tau)]
        for ch in chans+extra:
            if ch in unknown: measured[ch].add(i)
            z,a=world.measure(q,ch)
            if z=='near':
                assert world.clear(q,ch); cleared+=1; unknown.discard(ch); active.pop(ch,None)
            elif z=='direction':
                if ch in unknown: unknown.discard(ch); active[ch]=L.Src(q,a)
                else: active[ch].add(q,a)
            if cleared==16 or cleared+len(active)>=16: return
    while cleared<16:
        todo=[] if cleared+len(active)>=16 else [i for i in rem if pend(i)]
        if not todo and not active: break
        ready=[c for c,s in active.items() if s.RC()[1]<=C['r_ok']]
        nodes=[(('scan',i),[Q[i]]) for i in todo]+[(('clear',c),R6.service_points(active[c],C)) for c in (ready if todo else list(active))]
        if not nodes:
            ch=min(active,key=lambda c:dist(world.pos,active[c].RC()[0])); L.local_clear(world,ch,active.pop(ch),C); cleared+=1; continue
        pts=[min(p,key=lambda q:dist(world.pos,q)) for _,p in nodes]
        order=L.tour_nn2opt(pts,world.pos)
        kind,key=nodes[pts.index(order[0])][0]
        if kind=='clear': L.local_clear(world,key,active.pop(key),C); cleared+=1
        else: scan(key); rem.remove(key)
    if cleared<16 and cleared+len(active)<16:
        for ch in unknown: assert len(measured[ch])==len(Q)
    assert all(s['cleared'] for s in world.sources.values()),'漏清'
    return world

def run(W,keep,tau,seeds=(1,202,777)):
    L.local_clear=ORIG_LC if W<=0 and keep else make_local_clear(W,keep)
    try:
        CFG=L.cfg(**L.CFG4)
        return [st.mean([solve63(J.World(copy.deepcopy(s),i),NET6,CFG,tau).time/len(s)
                         for i,s in enumerate(L.cases(sd)[1])]) for sd in seeds]
    finally: L.local_clear=ORIG_LC

if __name__=='__main__':
    out=[];log=lambda s:(out.append(s),print(s,flush=True))
    log('【6.3】可检测锥约束的选点（问题四，覆盖网固定为方案六的 27 点非规则三角网）')
    log('%-30s %8s %8s %8s'%('','训练集','验证A','验证B'))
    VAR=[('方案六原版',(0.,True,0.)),
         ('6.3a 探测点打分 锥 W=60',(60.,False,0.)),('6.3b 探测点打分 锥 W=120',(120.,False,0.)),
         ('6.3c 锥 W=60 + 保留 risk 项',(60.,True,0.)),
         ('6.3d 顺路复测门槛 tau=0.5',(0.,True,0.5)),('6.3e 顺路复测门槛 tau=0.7',(0.,True,0.7)),
         ('6.3f 顺路复测门槛 tau=0.9',(0.,True,0.9)),
         ('6.3g 锥 W=60 + tau=0.7',(60.,True,0.7))]
    base=None
    for tag,(W,k,t) in VAR:
        r=run(W,k,t)
        if base is None: base=r
        log('%-30s %8.1f %8.1f %8.1f   (%+.1f%% / %+.1f%% / %+.1f%%)'%(tag,*r,*[100*(r[j]/base[j]-1) for j in range(3)]))
    (HERE/'results'/'方案六_6.3_输出.txt').write_text('\n'.join(out)+'\n',encoding='utf-8')
