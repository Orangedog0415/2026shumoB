"""【方案二】审查原型（非正式策略）：批量扫描 + 顺路插入清除 + 垂直补测 + h=990 格网。主循环为 solve_v2()。
注意：本文件中的 local_v2()、net990()、tour()、Src 也被【方案三】复用（见 方案三_参数扫描.py）。
仅用于验证《最终方案审查.md》中的改进方向；复用 code/baseline/方案一_最终方案验证.py 的几何函数和 World 仿真，
不连接模拟器。参数未调优。运行：python 方案二_调度改进原型.py（约数分钟）。
"""
import math, random, copy, importlib.util, pickle, sys
from pathlib import Path
_BASE=Path(__file__).resolve().parents[1]/'baseline'/'方案一_最终方案验证.py'   # 复用交接脚本中的几何函数与 World 仿真
spec=importlib.util.spec_from_file_location('jqx',str(_BASE)); J=importlib.util.module_from_spec(spec); spec.loader.exec_module(J)
dist=J.dist; DELTA=J.DELTA

def pruned_lattice(h=900):
    """keep only vertices of lattice triangles that intersect D (sufficient for convex-hull certificate)."""
    keep=set()
    def P(k,l): return (h*(k+(l%2)/2), math.sqrt(3)*h*l/2)
    def tri_hits(V):
        # triangle intersects disk radius 1800?
        def segd(A,B):
            ax,ay=A;bx,by=B;dx,dy=bx-ax,by-ay
            t=max(0,min(1,-(ax*dx+ay*dy)/(dx*dx+dy*dy))); return math.hypot(ax+t*dx,ay+t*dy)
        s=[ (V[(i+1)%3][0]-V[i][0])*(0-V[i][1])-(V[(i+1)%3][1]-V[i][1])*(0-V[i][0]) for i in range(3)]
        inside = all(x>=0 for x in s) or all(x<=0 for x in s)
        return inside or min(segd(V[i],V[(i+1)%3]) for i in range(3))<1800
    for l in range(-5,6):
        for k in range(-5,6):
            # two triangles per rhombus in offset coords
            if l%2==0:
                tris=[((k,l),(k+1,l),(k,l+1)),((k+1,l),(k+1,l+1),(k,l+1))]
            else:
                tris=[((k,l),(k+1,l),(k+1,l+1)),((k,l),(k+1,l+1),(k,l+1))]
            for t in tris:
                V=[P(*v) for v in t]
                if tri_hits(V): keep.update(V)
    return sorted(keep,key=lambda p:(dist(p,(0,0)),p[0],p[1]))

def tour(points,start=(0.,0.)):
    rem=list(range(len(points))); order=[]; cur=start
    while rem:
        i=min(rem,key=lambda i:dist(cur,points[i])); order.append(i); rem.remove(i); cur=points[i]
    # 2-opt on open path from start
    def L(o): 
        s=dist(start,points[o[0]]); 
        return s+sum(dist(points[o[i]],points[o[i+1]]) for i in range(len(o)-1))
    improved=True
    while improved:
        improved=False
        for i in range(len(order)-1):
            for j in range(i+1,len(order)):
                o=order[:i]+order[i:j+1][::-1]+order[j+1:]
                if L(o)<L(order)-1e-9: order=o; improved=True
    return [points[i] for i in order]

def axis_info(poly):
    c=J.centroid(poly)
    # principal axis via farthest vertex pair
    a,b=max(((a,b) for a in poly for b in poly),key=lambda ab:dist(*ab))
    ang=math.atan2(b[1]-a[1],b[0]-a[0])
    return c,ang,dist(a,b)

def cover_centers(poly):
    """20m-disk cover of poly using 28m squares in its axis frame (cell half-diag 19.8<20)."""
    c,ang,L=axis_info(poly); u=(math.cos(ang),math.sin(ang)); w=(-u[1],u[0])
    xs=[J.dot((p[0]-c[0],p[1]-c[1]),u) for p in poly]; ys=[J.dot((p[0]-c[0],p[1]-c[1]),w) for p in poly]
    s=28.0; out=[]
    nx=max(1,math.ceil((max(xs)-min(xs))/s)); ny=max(1,math.ceil((max(ys)-min(ys))/s))
    x0=(max(xs)+min(xs))/2-nx*s/2; y0=(max(ys)+min(ys))/2-ny*s/2
    for i in range(nx):
        for j in range(ny):
            cx,cy=x0+(i+.5)*s,y0+(j+.5)*s
            cell=[(x0+i*s,y0+j*s),(x0+(i+1)*s,y0+j*s),(x0+(i+1)*s,y0+(j+1)*s),(x0+i*s,y0+(j+1)*s)]
            # intersect test: clip poly by cell (in world coords)
            p=poly
            for n,b in [(u,J.dot(u,c)+x0+(i+1)*s),((-u[0],-u[1]),-J.dot(u,c)-(x0+i*s)),(w,J.dot(w,c)+y0+(j+1)*s),((-w[0],-w[1]),-J.dot(w,c)-(y0+j*s))]:
                p=J.clip(p,n,b)
            if p: out.append((c[0]+cx*u[0]+cy*w[0],c[1]+cx*u[1]+cy*w[1]))
    return out

class Src:
    def __init__(s,first,theta):
        s.first=first; s.theta=theta; s.P=J.update(J.initial_poly(),first,theta); s.detect=[first]; s.bearings=[theta]
    def add(s,p,a):
        new=J.update(s.P,p,a)
        if new: s.P=new; s.detect.append(p); s.bearings.append(a)
    def RC(s):
        c=J.centroid(s.P); return c,J.radius(s.P,c)

def good_geometry(src,p):
    c,_=src.RC(); a=math.atan2(c[1]-p[1],c[0]-p[0])
    return all(abs(math.sin(a-b))>math.sin(math.radians(25)) for b in src.bearings)

def local_v2(world,ch,src,force_fb=False):
    probes=0
    while not force_fb:
        c,r=src.RC()
        if r<=19.5:
            if world.clear(c,ch): return True
            raise AssertionError('certified clear failed')
        cc=cover_centers(src.P)
        if len(cc)<=3:
            # clear-cover the whole region (guaranteed since P contains source)
            cc.sort(key=lambda p:dist(world.pos,p))
            cur=world.pos; order=[]
            rem=cc[:]
            while rem:
                q=min(rem,key=lambda q:dist(cur,q)); order.append(q); rem.remove(q); cur=q
            for q in order:
                if world.clear(q,ch): return True
            raise AssertionError('cover failed')
        if probes>=4: break
        # probe: perpendicular-ish to long axis, distance chosen so new wedge width ~<=25m at C
        _,ang,L=axis_info(src.P)
        dp=max(r+15, min(700, dist(world.pos,c)))
        cand=[]
        for k in range(36):
            phi=2*math.pi*k/36
            if abs(math.sin(phi-ang))<math.sin(math.radians(55)): continue
            p=(c[0]+dp*math.cos(phi),c[1]+dp*math.sin(phi))
            if all(dist(p,d)>=1 for d in src.detect): cand.append(p)
        # prefer candidates whose bearing lies within the angular hull of past detecting points (safer for directional)
        def angdiff(a,b): return abs(math.atan2(math.sin(a-b),math.cos(a-b)))
        dets=[math.atan2(d[1]-c[1],d[0]-c[0]) for d in src.detect]
        def risk(p):
            a=math.atan2(p[1]-c[1],p[0]-c[0]); return min(angdiff(a,b) for b in dets)
        p=min(cand,key=lambda p:(dist(world.pos,p)/5+ (0 if risk(p)<math.radians(60) else 60), p[0],p[1]))
        probes+=1
        z,a=world.measure(p,ch)
        if z=='near':
            assert world.clear(p,ch); return True
        if z=='direction': src.add(p,a)
    # finite fallback identical in spirit to jqx: strip from first bearing, pruned by current P
    for cpt,_ in J.fallback_cells(src.P,src.first,src.theta):
        if world.clear(cpt,ch): return True
    for cpt,_ in J.fallback_cells(None,src.first,src.theta):
        if world.clear(cpt,ch): return True
    raise AssertionError('exhausted')

def solve_v2(world,mixed,Q=None,small=150,force_fb=False):
    if Q is None: Q=pruned_lattice() if mixed else J.omni_points()
    Q=tour(Q)
    unknown=set(range(1,21)); active={}; cleared=0
    measured={ch:set() for ch in unknown}
    todo=list(range(len(Q)))
    def clear_src(ch):
        nonlocal cleared
        local_v2(world,ch,active.pop(ch),force_fb); cleared+=1
    while True:
        if cleared==16: break
        todo=[i for i in todo if any(i not in measured[ch] for ch in unknown)]
        # tasks: next coverage point in tour order, or an active source whose region is small / whose detour is cheap
        if not todo and not active: break
        nxt=Q[todo[0]] if todo else None
        best=None
        for ch,s in active.items():
            c,r=s.RC()
            if nxt is None: cost=dist(world.pos,c)
            else:
                detour=dist(world.pos,c)+dist(c,nxt)-dist(world.pos,nxt)
                if r>small and todo: continue   # wait for more coverage bearings
                cost=detour
            if nxt is None or cost<=dist(world.pos,nxt)*0.6+200:
                if best is None or cost<best[0]: best=(cost,ch)
        if best is not None:
            clear_src(best[1]); continue
        i=todo.pop(0); q=Q[i]
        chans=sorted([ch for ch in unknown if i not in measured[ch]],key=lambda ch:(ch!=world.channel,ch))
        # also re-measure active sources with useful geometry and in plausible range
        extra=[ch for ch,s in active.items() if s.RC()[1]>19.5 and J.radius(s.P,q)<=1500 and good_geometry(s,q)]
        for ch in chans+extra:
            if ch in unknown: measured[ch].add(i)
            z,a=world.measure(q,ch)
            if z=='near':
                assert world.clear(q,ch); cleared+=1
                unknown.discard(ch); active.pop(ch,None)
            elif z=='direction':
                if ch in unknown:
                    unknown.discard(ch); active[ch]=Src(q,a)
                else: active[ch].add(q,a)
        if cleared==16: break
    # certificate: every remaining unknown channel measured at all Q
    for ch in unknown: assert len(measured[ch])==len(Q)
    assert all(s['cleared'] for s in world.sources.values()), 'missed source'
    return world.time


def lattice(h,ox=0,oy=0,rot=0):
    keep=set()
    e1=(h,0); e2=(h/2,h*math.sqrt(3)/2)
    cr,sr=math.cos(rot),math.sin(rot)
    def P(k,l):
        x=ox+k*e1[0]+l*e2[0]; y=oy+k*e1[1]+l*e2[1]
        return (round(cr*x-sr*y,6),round(sr*x+cr*y,6))
    def segd(A,B):
        ax,ay=A;bx,by=B;dx,dy=bx-ax,by-ay
        t=max(0,min(1,-(ax*dx+ay*dy)/(dx*dx+dy*dy))); return math.hypot(ax+t*dx,ay+t*dy)
    for k in range(-8,9):
        for l in range(-8,9):
            for t in (((k,l),(k+1,l),(k,l+1)),((k+1,l),(k+1,l+1),(k,l+1))):
                V=[P(*v) for v in t]
                s=[(V[(i+1)%3][0]-V[i][0])*(-V[i][1])-(V[(i+1)%3][1]-V[i][1])*(-V[i][0]) for i in range(3)]
                if all(x>=0 for x in s) or all(x<=0 for x in s) or min(segd(V[i],V[(i+1)%3]) for i in range(3))<1800:
                    keep.update(V)
    return sorted(keep)

def tour_len(Q):
    T=tour(Q); return dist((0,0),T[0])+sum(dist(T[i],T[i+1]) for i in range(len(T)-1))

def net990():
    """h=990 三角格网，偏移(0, 214.34)使保留点数最少；990<1000，三角形凸包证明原样成立。"""
    return lattice(990,0.0,990*math.sqrt(3)/2*2/8)

def check_certificate(Q):
    bad=0
    for i in range(720):
        a=2*math.pi*i/720
        for rr in [0]+[25*k for k in range(1,72)]+[1799.999,1800]:
            g=(rr*math.cos(a),rr*math.sin(a))
            for j in range(72):
                u=(math.cos(j*math.pi/36),math.sin(j*math.pi/36))
                if not any(dist(p,g)<=1000 and (p[0]-g[0])*u[0]+(p[1]-g[1])*u[1]>=-1e-9 for p in Q): bad+=1
    return bad

def gen(rng,n,mixed,pD=.65):
    src={}
    for ch in rng.sample(range(1,21),n):
        a=rng.random()*2*math.pi; rr=1800*math.sqrt(rng.random())
        src[ch]=J.source((rr*math.cos(a),rr*math.sin(a)),rng.uniform(1000,1500),'D' if mixed and rng.random()<pD else 'O',rng.random()*2*math.pi)
    return src

if __name__=='__main__':
    Q=net990()
    print('37点格网巡回 %.0f m；h=990 格网 %d 点，巡回 %.0f m，漏测组合 %d'%(tour_len(J.mixed_points()),len(Q),tour_len(Q),check_certificate(Q)))
    rng=random.Random(1)
    C3=[gen(rng,n,False) for n in (10,13,16) for _ in range(10)]
    C4=[gen(rng,n,True) for n in (10,13,16) for _ in range(10)]
    for label,C,mixed,QQ in (('Q3',C3,False,None),('Q4(37点)',C4,True,J.mixed_points()),('Q4(27点)',C4,True,Q)):
        a=[];b=[]
        for i,s in enumerate(C):
            w1=J.World(copy.deepcopy(s),i); J.solve(w1,mixed); a.append(w1.time/len(s))
            w2=J.World(copy.deepcopy(s),i); solve_v2(w2,mixed,QQ); b.append(w2.time/len(s))
        n=len(C)
        print('%s 每源平均：方案一 %.0f s，方案二 %.0f s（-%.0f%%），方案二更快 %d/%d 局'%(label,sum(a)/n,sum(b)/n,100*(1-sum(b)/sum(a)),sum(y<x for x,y in zip(a,b)),n))
