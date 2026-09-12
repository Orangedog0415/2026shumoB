"""【方案四】实验台：参数化的调度 / 局部清除 / 覆盖网 / 最终清除顺序，供方案 3.x 迭代与方案四复现。

版本对照（每源平均时间，本地仿真，问题三+问题四各 30 局训练集）：
  方案三   基线（x=600、r_ok=150、8 边形 974 m、h=990 格网、最终最近邻）      335.7 / 745.0
  3.1     贝叶斯优化标定策略参数                                          305.5 / 715.8
  3.2     覆盖网优化（问题四改 h=950 偏移优化格网，27 点，巡回 25.1 km）        335.7 / 709.4
  3.3a    任务选择改两步前瞻 beam                                        357.7 / 776.0  （变差，未采用）
  3.3b    最终清除顺序改 ALNS                                            328.1 / 740.4
  方案四   3.1 + 3.2 + 3.3b                                            300.6 / 688.9
"""
import math, copy, random, statistics as st, importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('J',str(HERE.parent/'baseline'/'方案一_最终方案验证.py'))
J=importlib.util.module_from_spec(spec); spec.loader.exec_module(J)
dist=J.dist
DEF=dict(x=600.,r_ok=150.,probe_angle=25.,lp_cap=700.,lp_angle=55.,lp_max=4,cover_k=3,
         select='fixed',final='nn',alns_iter=200)
# 方案四采用的参数（由 方案四_参数标定.py 的贝叶斯优化得到，取整）
CFG4=dict(x=530.,r_ok=130.,probe_angle=12.,lp_cap=540.,lp_angle=40.,lp_max=2,cover_k=6,final='alns')
def cfg(**kw):
    c=dict(DEF); c.update(kw); return c
# ---------- nets ----------
def ring(n,rho): return [(rho*math.cos(2*math.pi*k/n),rho*math.sin(2*math.pi*k/n)) for k in range(n)]
def lattice(h,ox,oy,rot):
    """边长 h 的三角格，保留与目标圆相交的三角形的全部顶点。h<=1000 时凸包证书成立（最终文档 §5.2）。"""
    cr,sr=math.cos(rot),math.sin(rot); keep=set()
    def Pt(k,l):
        x=ox+k*h+l*h/2; y=oy+l*h*math.sqrt(3)/2
        return (round(cr*x-sr*y,6),round(sr*x+cr*y,6))
    def segd(A,B):
        ax,ay=A;bx,by=B;dx,dy=bx-ax,by-ay
        t=max(0,min(1,-(ax*dx+ay*dy)/(dx*dx+dy*dy))); return math.hypot(ax+t*dx,ay+t*dy)
    m=int(2*1800/h)+3
    for k in range(-m,m+1):
        for l in range(-m,m+1):
            for tri in (((k,l),(k+1,l),(k,l+1)),((k+1,l),(k+1,l+1),(k,l+1))):
                V=[Pt(*v) for v in tri]
                s=[(V[(i+1)%3][0]-V[i][0])*(-V[i][1])-(V[(i+1)%3][1]-V[i][1])*(-V[i][0]) for i in range(3)]
                if all(z>=0 for z in s) or all(z<=0 for z in s) or min(segd(V[i],V[(i+1)%3]) for i in range(3))<1800:
                    keep.update(V)
    return sorted(keep)
NET3=lambda: ring(8,974.)                      # 问题三覆盖网（方案三、方案四相同）
NET4_V3=lambda: net990()                       # 问题四：方案三的 h=990 格网（27 点，巡回 26.7 km）
NET4_V4=lambda: lattice(950.,950/2,950*math.sqrt(3)/4,math.radians(30.))  # 问题四：方案四的 h=950 格网（27 点，巡回 25.1 km）

# ---- 方案六（问题四）覆盖网：非规则三角网，27 点，巡回 17 830 m ----
# 由 方案五_5.2_非规则三角网优化.py 的模拟退火得到。解析证书：Delaunay 三角剖分的凸包包住半径 1800 m 圆盘，
# 且与圆盘相交的三角形三边均 ≤1000 m（实测最长 998.0 m）⇒ 任一源到其所在三角形的三个顶点距离 ≤1000 m 且被三顶点围住。
# 另用“位置×朝向”稠密复验（360×62×72）：漏测 0。
NET4_V6_PTS=[
    (-1820.0, -428.9), (-1818.2, 229.7), (-1414.6, -1211.2),
    (-1607.4, 924.5), (-1214.6, -528.3), (-930.9, 1642.1),
    (-664.0, -1767.5), (-995.6, 437.3), (-419.9, -1131.9),
    (-748.8, 1074.3), (-308.7, -159.7), (-62.1, -1840.0),
    (-123.9, 366.0), (223.7, 1295.3), (596.7, 1753.2),
    (814.1, -1682.9), (852.7, 542.7), (1021.9, -846.8),
    (1104.7, 1493.6), (1275.2, 97.8), (1206.9, -1478.4),
    (1673.8, 831.6), (1735.5, -643.3), (-333.2, 1853.8),
    (1862.7, -101.8), (145.8, -952.1), (373.4, -305.0),
]
NET4_V6=lambda: [tuple(p) for p in NET4_V6_PTS]

def net990():
    h=990; ox,oy=0.0,990*math.sqrt(3)/2*2/8; keep=set()
    def Pt(k,l): return (round(ox+k*h+l*h/2,6),round(oy+l*h*math.sqrt(3)/2,6))
    def segd(A,B):
        ax,ay=A;bx,by=B;dx,dy=bx-ax,by-ay
        t=max(0,min(1,-(ax*dx+ay*dy)/(dx*dx+dy*dy))); return math.hypot(ax+t*dx,ay+t*dy)
    for k in range(-8,9):
        for l in range(-8,9):
            for tri in (((k,l),(k+1,l),(k,l+1)),((k+1,l),(k+1,l+1),(k,l+1))):
                V=[Pt(*v) for v in tri]
                s=[(V[(i+1)%3][0]-V[i][0])*(-V[i][1])-(V[(i+1)%3][1]-V[i][1])*(-V[i][0]) for i in range(3)]
                if all(z>=0 for z in s) or all(z<=0 for z in s) or min(segd(V[i],V[(i+1)%3]) for i in range(3))<1800:
                    keep.update(V)
    return sorted(keep)
# ---------- routing ----------
def tour_nn2opt(pts,start=(0.,0.)):
    rem=list(range(len(pts))); order=[]; cur=start
    while rem:
        i=min(rem,key=lambda i:dist(cur,pts[i])); order.append(i); rem.remove(i); cur=pts[i]
    def L(o): return dist(start,pts[o[0]])+sum(dist(pts[o[i]],pts[o[i+1]]) for i in range(len(o)-1))
    imp=True
    while imp:
        imp=False
        for i in range(len(order)-1):
            for j in range(i+1,len(order)):
                o=order[:i]+order[i:j+1][::-1]+order[j+1:]
                if L(o)<L(order)-1e-9: order=o; imp=True
    return [pts[i] for i in order]
def alns_order(pts,start,iters=200,seed=0):
    """开放路径 ALNS：随机/最差移除 + 最小插入修复 + 2-opt 接受改进解。"""
    if len(pts)<=2: return tour_nn2opt(pts,start)
    rng=random.Random(seed)
    cur=[p for p in tour_nn2opt(pts,start)]
    def L(o): return dist(start,o[0])+sum(dist(o[i],o[i+1]) for i in range(len(o)-1))
    best=cur[:]; bl=L(best)
    for it in range(iters):
        cand=cur[:]
        k=max(1,min(len(cand)-1,rng.randint(1,max(1,len(cand)//3))))
        if rng.random()<.5: rem=rng.sample(cand,k)
        else:
            gain=[]
            for i,p in enumerate(cand):
                a=start if i==0 else cand[i-1]; b=cand[i+1] if i+1<len(cand) else None
                g=dist(a,p)+(dist(p,b) if b else 0)-(dist(a,b) if b else 0); gain.append((g,i))
            gain.sort(reverse=True); rem=[cand[i] for _,i in gain[:k]]
        for p in rem: cand.remove(p)
        for p in rem:
            bi,bc=0,None
            for i in range(len(cand)+1):
                t=cand[:i]+[p]+cand[i:]; c=L(t)
                if bc is None or c<bc: bc,bi=c,i
            cand=cand[:bi]+[p]+cand[bi:]
        imp=True
        while imp:
            imp=False
            for i in range(len(cand)-1):
                for j in range(i+1,len(cand)):
                    t=cand[:i]+cand[i:j+1][::-1]+cand[j+1:]
                    if L(t)<L(cand)-1e-9: cand=t; imp=True
        if L(cand)<bl-1e-9: best,bl=cand[:],L(cand); cur=cand[:]
        elif rng.random()<.1: cur=cand[:]
    return best
# ---------- localisation state ----------
class Src:
    def __init__(s,first,theta):
        s.first=first; s.theta=theta; s.P=J.update(J.initial_poly(),first,theta); s.det=[first]; s.bear=[theta]
    def add(s,p,a):
        new=J.update(s.P,p,a)
        if new: s.P=new; s.det.append(p); s.bear.append(a)
    def RC(s):
        c=J.centroid(s.P); return c,J.radius(s.P,c)
def axis(poly):
    c=J.centroid(poly); a,b=max(((a,b) for a in poly for b in poly),key=lambda ab:dist(*ab))
    return c,math.atan2(b[1]-a[1],b[0]-a[0])
def cover_centers(poly,s=28.0):
    c,ang=axis(poly); u=(math.cos(ang),math.sin(ang)); w=(-u[1],u[0])
    xs=[J.dot((p[0]-c[0],p[1]-c[1]),u) for p in poly]; ys=[J.dot((p[0]-c[0],p[1]-c[1]),w) for p in poly]
    out=[]; nx=max(1,math.ceil((max(xs)-min(xs))/s)); ny=max(1,math.ceil((max(ys)-min(ys))/s))
    x0=(max(xs)+min(xs))/2-nx*s/2; y0=(max(ys)+min(ys))/2-ny*s/2
    for i in range(nx):
        for j in range(ny):
            p=poly
            for n,b in [(u,J.dot(u,c)+x0+(i+1)*s),((-u[0],-u[1]),-J.dot(u,c)-(x0+i*s)),(w,J.dot(w,c)+y0+(j+1)*s),((-w[0],-w[1]),-J.dot(w,c)-(y0+j*s))]:
                p=J.clip(p,n,b)
            if p:
                cx,cy=x0+(i+.5)*s,y0+(j+.5)*s
                out.append((c[0]+cx*u[0]+cy*w[0],c[1]+cx*u[1]+cy*w[1]))
    return out
def good_geom(src,p,ang_deg):
    c,_=src.RC(); a=math.atan2(c[1]-p[1],c[0]-p[0])
    return all(abs(math.sin(a-b))>math.sin(math.radians(ang_deg)) for b in src.bear)
def local_clear(world,ch,src,C):
    probes=0
    while True:
        c,r=src.RC()
        if r<=19.5:
            if world.clear(c,ch): return
            raise AssertionError('certified clear failed')
        cc=cover_centers(src.P)
        if len(cc)<=C['cover_k']:
            cur=world.pos; rem=cc[:]
            while rem:
                q=min(rem,key=lambda q:dist(cur,q)); rem.remove(q); cur=q
                if world.clear(q,ch): return
            raise AssertionError('cover failed')
        if probes>=C['lp_max']: break
        _,ang=axis(src.P)
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
        p=min(cand,key=lambda p:(dist(p,world.pos)/5+(0 if risk(p)<math.radians(60) else 60),p[0],p[1]))
        probes+=1
        z,a=world.measure(p,ch)
        if z=='near':
            assert world.clear(p,ch); return
        if z=='direction': src.add(p,a)
    for cpt,_ in J.fallback_cells(src.P,src.first,src.theta):
        if world.clear(cpt,ch): return
    for cpt,_ in J.fallback_cells(None,src.first,src.theta):
        if world.clear(cpt,ch): return
    raise AssertionError('exhausted')
# ---------- solver ----------
def solve(world,mixed,net,C=None):
    C=C or cfg()
    Q=tour_nn2opt(net) if C['select']=='fixed' else list(net)
    order=list(range(len(Q)))
    unknown=set(range(1,21)); active={}; cleared=0
    measured={ch:set() for ch in unknown}
    pend=lambda i:[ch for ch in unknown if i not in measured[ch]]
    def scan(i):
        nonlocal cleared
        q=Q[i]
        chans=sorted(pend(i),key=lambda ch:(ch!=world.channel,ch))
        extra=[ch for ch,s in active.items() if s.RC()[1]>19.5 and J.radius(s.P,q)<=1500 and good_geom(s,q,C['probe_angle'])]
        for ch in chans+extra:
            if ch in unknown: measured[ch].add(i)
            z,a=world.measure(q,ch)
            if z=='near':
                assert world.clear(q,ch); cleared+=1; unknown.discard(ch); active.pop(ch,None)
            elif z=='direction':
                if ch in unknown: unknown.discard(ch); active[ch]=Src(q,a)
                else: active[ch].add(q,a)
            if cleared==16: return
    def do_clear(ch):
        nonlocal cleared
        local_clear(world,ch,active.pop(ch),C); cleared+=1
    def cost_scan(p,i): return dist(p,Q[i])/5+6*len(pend(i))
    def cost_clear(p,ch):
        c,r=active[ch].RC(); return dist(p,c)/5+(5 if r<=19.5 else 11)
    while cleared<16:
        todo=[i for i in order if pend(i)]
        if not todo:
            if not active: break
            if C['final']=='alns':
                cs={ch:active[ch].RC()[0] for ch in active}
                seq=alns_order(list(cs.values()),world.pos,C['alns_iter'])
                inv={v:k for k,v in cs.items()}
                for pt in seq:
                    ch=inv[pt]
                    if ch in active: do_clear(ch)
            else:
                ch=min(active,key=lambda c:dist(world.pos,active[c].RC()[0])); do_clear(ch)
            continue
        if C['select']=='fixed':
            nxt=Q[todo[0]]; best=None
            for ch,s in active.items():
                c,r=s.RC()
                if r>C['r_ok']: continue
                det=dist(world.pos,c)+dist(c,nxt)-dist(world.pos,nxt)
                if det<=C['x'] and (best is None or det<best[0]): best=(det,ch)
            if best: do_clear(best[1]); continue
            scan(todo[0]); order.remove(todo[0])
        else:  # beam / 2-step lookahead
            acts=[('scan',i,cost_scan(world.pos,i)) for i in todo]+[('clear',ch,cost_clear(world.pos,ch)) for ch,s in active.items() if s.RC()[1]<=C['r_ok']]
            acts.sort(key=lambda a:a[2]); acts=acts[:C.get('beam_w',4)]
            best=None
            for kind,key,c1 in acts:
                p2=Q[key] if kind=='scan' else active[key].RC()[0]
                rest=[('scan',i,dist(p2,Q[i])/5+6*len(pend(i))) for i in todo if not(kind=='scan' and i==key)]
                rest+=[('clear',ch,dist(p2,active[ch].RC()[0])/5+(5 if active[ch].RC()[1]<=19.5 else 11)) for ch in active if not(kind=='clear' and ch==key) and active[ch].RC()[1]<=C['r_ok']]
                c2=min([c for _,_,c in rest],default=0)
                tot=c1+c2
                if best is None or tot<best[0]: best=(tot,kind,key)
            _,kind,key=best
            if kind=='clear': do_clear(key)
            else:
                scan(key); order.remove(key)
    if cleared<16:
        for ch in unknown: assert len(measured[ch])==len(Q)
    assert all(s['cleared'] for s in world.sources.values()),'漏清'
    return world
# ---------- cases ----------
def gen(rng,n,mixed,pD=.65):
    src={}
    for ch in rng.sample(range(1,21),n):
        a=rng.random()*2*math.pi; rr=1800*math.sqrt(rng.random())
        src[ch]=J.source((rr*math.cos(a),rr*math.sin(a)),rng.uniform(1000,1500),'D' if mixed and rng.random()<pD else 'O',rng.random()*2*math.pi)
    return src
def cases(seed,per=10):
    rng=random.Random(seed)
    return ([gen(rng,n,False) for n in (10,13,16) for _ in range(per)],
            [gen(rng,n,True) for n in (10,13,16) for _ in range(per)])
def evaluate(C,net3,net4,C3,C4):
    p3=[solve(J.World(copy.deepcopy(s),i),False,net3,C).time/len(s) for i,s in enumerate(C3)]
    p4=[solve(J.World(copy.deepcopy(s),i),True,net4,C).time/len(s) for i,s in enumerate(C4)]
    return st.mean(p3),st.mean(p4)
