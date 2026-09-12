# -*- coding: utf-8 -*-
"""2026 国赛 B 题 · 官方模拟器正式测试主程序（策略 B）

一个文件即可对接官方模拟器：**问题三用方案四、问题四用方案七**，只依赖 Python 3 标准库。

    python 官方测试_策略B.py --problem 3 --robot-id 你的参赛队号
    python 官方测试_策略B.py --problem 4 --robot-id 你的参赛队号
    python 官方测试_策略B.py --selfcheck            # 不联网，只做覆盖网证书自检

文件结构
    第 1 段  几何与保证层        逐字节取自 code/baseline/方案一_最终方案验证.py
    第 2 段  覆盖网/路线/局部清除/问题三调度   逐字节取自 code/experiments/方案四_实验台.py
    第 3 段  问题四调度（联合重规划+服务簇+计数提前停） 逐字节取自 code/experiments/方案六_运行.py
    第 4 段  官方 HTTP 客户端（附件2）、远程世界适配器、覆盖网自检、兜底与主程序

算法本体与本地仿真跑出 300.5 s/源（问题三）、529.1 s/源（问题四）的代码完全一致，
由 code/experiments/结果汇总_数据导出.py 所用的同一批函数抽取而来，未作任何改写。

保证性参数（不可改）：δ=1.005°、可探测余量 999 m、保证清除半径 19.5 m、75×3 有限兜底、
清满 16 个即停、按频道累计的覆盖证书。策略参数见 CFG4。
"""
import argparse
import json
import math
import random
import socket
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# ===== 几何与保证层（逐字节取自 code/baseline/方案一_最终方案验证.py）=====
DELTA = math.radians(1.005)

EPS = 1e-7

def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

def dot(a, b):
    return a[0] * b[0] + a[1] * b[1]

def clip(poly, n, b):
    if not poly:
        return []
    out = []
    for a, c in zip(poly, poly[1:] + poly[:1]):
        fa, fc = dot(n, a) - b, dot(n, c) - b
        ia, ic = fa <= EPS, fc <= EPS
        if ia != ic:
            t = fa / (fa - fc)
            out.append((a[0] + t * (c[0] - a[0]), a[1] + t * (c[1] - a[1])))
        if ic:
            out.append(c)
    return out

def disk_outer(poly, center, r):
    for i in range(64):
        a = 2 * math.pi * i / 64
        n = math.cos(a), math.sin(a)
        poly = clip(poly, n, r + dot(n, center))
    return poly

def update(poly, s, theta):
    poly = wedge(poly, s, theta)
    return disk_outer(poly, s, 1500)

def wedge(poly, s, theta):
    for a, sign in [(theta - DELTA, -1), (theta + DELTA, 1)]:
        n = -sign * math.sin(a), sign * math.cos(a)
        poly = clip(poly, n, dot(n, s))
    return poly

def diameter(poly):
    if not poly:
        return 0., None
    a, b = max(((a, b) for a in poly for b in poly), key=lambda ab: dist(*ab))
    return dist(a, b), (a, b)

def initial_poly():
    return disk_outer([(-1810, -1810), (1810, -1810), (1810, 1810), (-1810, 1810)], (0, 0), 1800)

def centroid(poly):
    # Vertex average is inside every nonempty convex polygon, including degeneracy.
    return tuple(sum(p[i] for p in poly) / len(poly) for i in (0, 1))

def contains(poly, p):
    return all((b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0]) >= -EPS*max(1,dist(a,b))
               for a,b in zip(poly,poly[1:]+poly[:1]))

def radius(poly, c):
    return max(dist(p, c) for p in poly)

def fallback_cells(poly, anchor, theta):
    u = math.cos(theta), math.sin(theta)
    w = -u[1], u[0]
    cells = []
    for i in range(75):
        for j in (range(3) if i % 2 == 0 else reversed(range(3))):
            x0, y0 = 20 * i, -30 + 20 * j
            cell = [tuple(anchor[t] + x * u[t] + y * w[t] for t in (0, 1))
                    for x, y in [(x0, y0), (x0 + 20, y0), (x0 + 20, y0 + 20), (x0, y0 + 20)]]
            p = poly if poly is not None else cell
            for n, b in [(u, dot(u, anchor) + x0 + 20), ((-u[0], -u[1]), -dot(u, anchor) - x0),
                         (w, dot(w, anchor) + y0 + 20), ((-w[0], -w[1]), -dot(w, anchor) - y0)]:
                p = clip(p, n, b)
            if p:
                c = tuple(anchor[t] + (x0 + 10) * u[t] + (y0 + 10) * w[t] for t in (0, 1))
                cells.append((c, cell))
    return cells


# ===== 覆盖网、路线、局部清除与问题三调度（逐字节取自 code/experiments/方案四_实验台.py）=====
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

# ---- 方案七（问题四）覆盖网：25 点，巡回 17 547 m ----
# 由 方案六_6.4_覆盖网再压缩.py 得到：先在“中心 + 同心环”族里枚举出可行的最小构型（25 点：中心 + 12@950 + 12@1880），
# 再以它为起点自由退火缩短巡回。证书与 NET4_V6 同构：Delaunay 三角剖分的凸包包住半径 1800 m 圆盘，
# 且与圆盘相交的三角形三边均 ≤1000 m（实测最长 995.8 m）；GT06 式(31) 的全域最大方位间隔 179.86°<180°；
# 稠密“位置×朝向”复验（360×62×72）漏测 0。
NET4_V7_PTS=[
    (-1805.9, 459.1), (-1804.6, -516.7), (-1335.7, 1305.9),
    (-1287.0, -1361.6), (-960.4, -63.1), (-876.6, -481.9),
    (-812.4, 464.1), (-500.9, 1791.8), (-461.7, 833.2),
    (-446.4, -832.7), (-437.6, -1806.8), (-90.2, 1676.2),
    (6.7, -22.1), (21.4, -923.0), (459.9, 860.1),
    (460.0, -1799.1), (479.7, 1827.4), (494.3, -881.5),
    (880.9, 431.6), (958.7, -10.6), (1318.9, 1320.5),
    (1323.1, -1339.9), (1484.5, -849.8), (1798.8, 504.1),
    (1806.7, -478.6),
]

NET4_V7=lambda: [tuple(p) for p in NET4_V7_PTS]

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


# ===== 问题四调度：联合重规划 + 服务簇 + 计数提前停（逐字节取自 code/experiments/方案六_运行.py）=====
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


# ===== 第 4 段：官方 HTTP 客户端（附件2）、远程世界适配器、覆盖网自检与主程序 =====
# 上面三段逐字节保留了原文件里的 J. / L. 前缀，这里让它们都指向本模块自身。
J = L = sys.modules[__name__]

ARENA_ID = 'default'                 # 附件2 §5.1：必须是 ASCII 字符串 "default"
DEFAULT_BASE = 'http://127.0.0.1:2026'   # 附件2 §1.5：模拟器默认服务地址（只监听回环）
MAX_COORD = 2_000_000.0              # 附件2 §1.1
# 409 也放进重试集：本程序每个新动作都用全新的 request_id（m-序号 / c-序号），
# 不可能出现“同 ID 不同内容”，因此 409 只可能是服务端把串行请求误判成并发。
# 它不占用幂等键，原样重发同一 request_id 与同一请求体是安全的。
RETRYABLE_HTTP = (409, 429, 500, 502, 503, 504)


class Fatal(RuntimeError):
    """协议、身份或测试状态错误：不能靠重试修正，必须停机并保留现场。"""


class Stop(RuntimeError):
    """现实时间预算用尽：立刻停止发新动作并收尾。"""


class Client:
    """附件2 的官方客户端：串行单未决动作、幂等重放、同时检查 HTTP 状态与 accepted。"""

    def __init__(self, base, robot_id, timeout=5.0, reserve=25.0, retries=4,
                 logfile=None, verbose=True):
        self.base = base.rstrip('/')
        self.robot_id = robot_id
        self.timeout = timeout
        self.reserve = reserve           # 为收尾（/exit、写日志）预留的现实秒数
        self.retries = retries
        self.verbose = verbose
        self.logfile = logfile
        self.seq = 0
        self.vt = 0.0                    # 最近一次 accepted=true 的 virtual_time_s
        self.enter_mono = None
        self.deadline = None
        self.n_http = 0
        self.n_retry = 0
        if self.logfile:
            Path(self.logfile).parent.mkdir(parents=True, exist_ok=True)
            Path(self.logfile).write_text('', encoding='utf-8')

    # ---------------- 日志 ----------------
    def _log(self, rec):
        rec = dict(rec)
        rec['wall_ms'] = int(time.time() * 1000)
        rec['mono_s'] = round(time.monotonic() - (self.enter_mono or time.monotonic()), 3)
        if self.logfile:
            with open(self.logfile, 'a', encoding='utf-8') as f:
                f.write(json.dumps(rec, ensure_ascii=False) + '\n')

    def _say(self, text):
        if self.verbose:
            print(text, flush=True)

    # ---------------- 发送 ----------------
    def _payload(self, request_id):
        return {'arena_id': ARENA_ID, 'robot_id': self.robot_id, 'request_id': request_id}

    def _post(self, path, payload):
        """发送一条请求。网络故障时复用同一请求体与同一 request_id 重放（附件2 §5.3）。"""
        data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        headers = {'Content-Type': 'application/json; charset=utf-8'}
        for attempt in range(self.retries + 1):
            t0 = time.monotonic()
            try:
                req = Request(self.base + path, data=data, headers=headers, method='POST')
                with urlopen(req, timeout=self.timeout) as resp:
                    http, raw = resp.getcode(), resp.read().decode('utf-8', 'replace')
            except HTTPError as e:                      # 有 JSON 体的错误响应
                http = e.code
                try:
                    raw = e.read().decode('utf-8', 'replace')
                except Exception:
                    raw = ''
            except (URLError, socket.timeout, OSError) as e:
                # 连接失败 / 超时 / 响应丢失：服务端可能已经执行，必须原样重放同一 request_id。
                self.n_retry += 1
                self._log({'ev': 'net_error', 'path': path, 'request_id': payload['request_id'],
                           'attempt': attempt, 'error': repr(e)})
                self._say('  网络异常（%s），复用 request_id=%s 重放第 %d 次'
                          % (e.__class__.__name__, payload['request_id'], attempt + 1))
                if attempt >= self.retries:
                    raise Fatal('网络重试 %d 次仍失败：%r' % (self.retries, e))
                time.sleep(min(2.0, 0.25 * 2 ** attempt))
                continue
            self.n_http += 1
            try:
                body = json.loads(raw)
                if not isinstance(body, dict):
                    raise ValueError('响应不是 JSON 对象')
            except ValueError as e:
                self.n_retry += 1
                self._log({'ev': 'bad_json', 'path': path, 'http': http, 'raw': raw[:500],
                           'request_id': payload['request_id'], 'attempt': attempt})
                self._say('  响应不是 JSON（%s, request_id=%s），原样重发第 %d 次'
                          % (path, payload['request_id'], attempt + 1))
                if attempt >= self.retries:
                    raise Fatal('响应不是合法 JSON：HTTP %d %r' % (http, raw[:200]))
                time.sleep(min(2.0, 0.25 * 2 ** attempt))
                continue
            self._log({'ev': 'http', 'path': path, 'request': payload, 'http': http,
                       'response': body, 'rtt_ms': round(1000 * (time.monotonic() - t0), 1)})
            # 附件2 §5.3：必须同时检查 HTTP 状态与 accepted。
            if http == 200 and body.get('accepted') is True:
                vt = body.get('virtual_time_s')
                if isinstance(vt, (int, float)) and not isinstance(vt, bool):
                    self.vt = float(vt)
                return body
            if http in RETRYABLE_HTTP:
                # 这类拒绝不占用幂等键，同 ID 同内容重试是安全的。
                self.n_retry += 1
                self._say('  HTTP %d（%s, request_id=%s），原样重发第 %d 次'
                          % (http, path, payload['request_id'], attempt + 1))
                if attempt >= self.retries:
                    raise Fatal('HTTP %d 重试 %d 次仍失败' % (http, self.retries))
                time.sleep(min(3.0, 0.5 * 2 ** attempt))
                continue
            # 400/404/405/409/413/415 或 200+accepted=false：不能自动修正，停机保留现场。
            raise Fatal('请求未执行：path=%s http=%d body=%s request_id=%s'
                        % (path, http, json.dumps(body, ensure_ascii=False), payload['request_id']))
        raise Fatal('重试耗尽：%s' % path)

    # ---------------- 四条指令 ----------------
    def enter(self):
        body = self._post('/enter', self._payload('enter-1'))
        self.enter_mono = time.monotonic()
        rem = body.get('remaining_real_duration_s')
        rem = float(rem) if isinstance(rem, (int, float)) and not isinstance(rem, bool) else 1200.0
        self.deadline = self.enter_mono + rem
        self._say('/enter 成功：本局可用现实时间 %.0f s，虚拟上限 %s s'
                  % (rem, body.get('max_virtual_duration_s')))
        return body

    def remaining_real_s(self):
        return float('inf') if self.deadline is None else self.deadline - time.monotonic()

    def act(self, path, p, ch):
        left = self.remaining_real_s()
        if left <= self.reserve:
            raise Stop('现实时间只剩 %.1f s（预留 %.0f s 收尾）' % (left, self.reserve))
        x, y = float(p[0]), float(p[1])
        if not (math.isfinite(x) and math.isfinite(y)) or abs(x) > MAX_COORD or abs(y) > MAX_COORD:
            raise Fatal('坐标非法：(%r, %r)' % (x, y))
        ch = int(ch)
        if not 1 <= ch <= 20:
            raise Fatal('频道非法：%r' % ch)
        self.seq += 1
        payload = self._payload('%s-%d' % ('m' if path == '/measure' else 'c', self.seq))
        payload['position'] = {'x': x, 'y': y}
        payload['channel'] = ch
        return self._post(path, payload)

    def leave(self):
        body = self._post('/exit', self._payload('exit-1'))
        self._say('/exit 成功：exit_reason=%s，虚拟时刻 %s s'
                  % (body.get('exit_reason'), body.get('virtual_time_s')))
        return body


class RemoteWorld:
    """把官方接口包装成与本地仿真 World 完全相同的接口，上面三段算法代码因此无需改动。

    策略只能看到 measure/clear 的返回值：没有源坐标、数量、半径、类型或朝向。
    self.sources 恒为空字典，算法末尾的 all(...) 对空集合成立（正式测试没有真值可查）。
    """

    def __init__(self, client):
        self.c = client
        self.sources = {}
        self.pos = (0., 0.)
        self.channel = 1
        self.time = 0.
        self.moves = self.detect = self.switch = self.cleartime = 0.
        self.actions = 0
        self.first = {}          # ch -> (首次测点, 示向度弧度)，兜底用
        self.cleared = set()     # 已确认清除的频道
        self.n_direction = self.n_near = self.n_nosignal = 0

    def _move(self, p):
        d = dist(self.pos, p) / 5.
        self.time += d
        self.moves += d
        self.pos = (float(p[0]), float(p[1]))

    def measure(self, p, ch):
        body = self.c.act('/measure', p, ch)
        ch = int(ch)
        sw = 1. if ch != self.channel else 0.
        self._move(p)
        self.time += 5. + sw
        self.detect += 5.
        self.switch += sw
        self.channel = ch
        self.actions += 1
        z = body.get('measure_result')
        if z == 'direction':
            deg = body.get('svd_deg')
            if not isinstance(deg, (int, float)) or isinstance(deg, bool) or not math.isfinite(float(deg)):
                raise Fatal('direction 未返回合法 svd_deg：%r' % (deg,))
            a = math.radians(float(deg) % 360.)
            self.n_direction += 1
            self.first.setdefault(ch, (self.pos, a))
            return 'direction', a
        if z == 'near':
            self.n_near += 1
            return 'near', None
        if z == 'no_signal':
            self.n_nosignal += 1
            return 'no_signal', None
        raise Fatal('未知 measure_result：%r' % (z,))

    def clear(self, p, ch):
        body = self.c.act('/clear', p, ch)
        ch = int(ch)
        self._move(p)
        z = body.get('clear_result')
        if z not in ('success', 'no_target_in_range'):
            raise Fatal('未知 clear_result：%r' % (z,))
        ok = z == 'success'
        dt = 5. if ok else 3.
        self.time += dt
        self.cleartime += dt
        self.actions += 1
        if ok:
            self.cleared.add(ch)
        return ok

    def drift(self):
        """本地按附件2 §4 复算的虚拟时间与模拟器返回值之差，用于核对计时口径。"""
        return self.time - self.c.vt


# ---------------------------------------------------------------- 覆盖网自检

def convex_hull(pts):
    P = sorted(set((round(x, 6), round(y, 6)) for x, y in pts))
    if len(P) < 3:
        return P
    def half(seq):
        out = []
        for p in seq:
            while len(out) >= 2 and ((out[-1][0]-out[-2][0])*(p[1]-out[-2][1])
                                     - (out[-1][1]-out[-2][1])*(p[0]-out[-2][0])) <= 0:
                out.pop()
            out.append(p)
        return out
    return half(P)[:-1] + half(P[::-1])[:-1]


def hull_covers_disk(pts, R=1800.):
    """凸包是否包住半径 R 的圆盘：原点在包内，且每条包边所在直线到原点距离 ≥ R。"""
    H = convex_hull(pts)
    if len(H) < 3:
        return False, 0.
    worst = float('inf')
    for a, b in zip(H, H[1:] + H[:1]):
        ex, ey = b[0]-a[0], b[1]-a[1]
        n = math.hypot(ex, ey)
        if n < 1e-9:
            continue
        d = ((b[0]-a[0])*(0-a[1]) - (b[1]-a[1])*(0-a[0])) / n   # 原点到直线 ab 的有向距离
        worst = min(worst, d)
    return worst >= R - 1e-6, worst


def _seg_dist_origin(A, B):
    dx, dy = B[0]-A[0], B[1]-A[1]
    dd = dx*dx + dy*dy
    t = 0. if dd < 1e-12 else max(0., min(1., -(A[0]*dx + A[1]*dy) / dd))
    return math.hypot(A[0]+t*dx, A[1]+t*dy)


def _tri_hits_disk(V, R=1800.):
    if any(math.hypot(*v) <= R for v in V):
        return True
    s = [(V[(i+1) % 3][0]-V[i][0])*(-V[i][1]) - (V[(i+1) % 3][1]-V[i][1])*(-V[i][0]) for i in range(3)]
    if all(z >= 0 for z in s) or all(z <= 0 for z in s):     # 原点在三角形内
        return True
    return min(_seg_dist_origin(V[i], V[(i+1) % 3]) for i in range(3)) <= R


def delaunay_triangles(pts):
    """暴力 Delaunay：对每个三元组做空外接圆检验。n≤30 时足够快，且不依赖 scipy。
    共圆退化时可能多留下三角形，只会让后面的边长检查更严，不会漏检。"""
    n = len(pts)
    tri = []
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                A, B, C = pts[i], pts[j], pts[k]
                ar = (B[0]-A[0])*(C[1]-A[1]) - (B[1]-A[1])*(C[0]-A[0])
                if abs(ar) < 1e-6:
                    continue
                if ar < 0:
                    A, C = C, A
                    ar = -ar
                ok = True
                for m in range(n):
                    if m in (i, j, k):
                        continue
                    D = pts[m]
                    ax, ay = A[0]-D[0], A[1]-D[1]
                    bx, by = B[0]-D[0], B[1]-D[1]
                    cx, cy = C[0]-D[0], C[1]-D[1]
                    det = ((ax*ax+ay*ay)*(bx*cy-by*cx)
                           - (bx*bx+by*by)*(ax*cy-ay*cx)
                           + (cx*cx+cy*cy)*(ax*by-ay*bx))
                    if det > 1e-6:          # D 严格在外接圆内
                        ok = False
                        break
                if ok:
                    tri.append((A, B, C))
    return tri


def max_bearing_gap(pts, g, reach=1000.):
    """源在 g 时，1000 m 邻域内观测点相对 g 的最大方位间隔（<180° ⟺ g 被围住 ⟺ 任何朝向都能被测到）。"""
    ang = sorted(math.atan2(p[1]-g[1], p[0]-g[0]) for p in pts if dist(p, g) <= reach + 1e-9)
    if not ang:
        return 360.
    gaps = [(b - a) for a, b in zip(ang, ang[1:])] + [ang[0] + 2*math.pi - ang[-1]]
    return math.degrees(max(gaps))


def certify_net(pts, R=1800., edge_max=1000., dense=True, nr=37, na=360):
    """覆盖网证书自检：解析边长检查 + 凸包含圆 +（可选）稠密最大方位间隔复验。"""
    info = {'points': len(pts)}
    ok_hull, margin = hull_covers_disk(pts, R)
    info['hull_min_edge_distance_m'] = round(margin, 2)
    info['hull_covers_disk'] = ok_hull
    longest = 0.
    ntri = 0
    for V in delaunay_triangles(pts):
        if not _tri_hits_disk(V, R):
            continue
        ntri += 1
        longest = max(longest, max(dist(V[i], V[(i+1) % 3]) for i in range(3)))
    info['triangles_hitting_disk'] = ntri
    info['longest_edge_m'] = round(longest, 2)
    ok_edge = ntri > 0 and longest <= edge_max + 1e-6
    info['edges_within_1000m'] = ok_edge
    ok_dense = True
    if dense:
        worst = 0.
        for ir in range(nr):
            r = R * ir / (nr - 1)
            for ia in range(na):
                a = 2 * math.pi * ia / na
                worst = max(worst, max_bearing_gap(pts, (r*math.cos(a), r*math.sin(a))))
                if r == 0.:
                    break
        info['max_bearing_gap_deg'] = round(worst, 2)
        ok_dense = worst < 180. - 1e-9
        info['dense_gap_below_180'] = ok_dense
    info['ok'] = bool(ok_hull and ok_edge and ok_dense)
    return info['ok'], info


def pick_net4(prefer='auto', dense=True, say=print):
    """启动前自检问题四覆盖网；不通过就依次退回 NET4_V6 与 h=950 规则格网（两者也都验证过）。"""
    table = [('NET4_V7（25 点，17 547 m，方案七）', NET4_V7),
             ('NET4_V6（27 点，17 830 m，方案六）', NET4_V6),
             ('h=950 规则格网（27 点，25 111 m，方案四）', NET4_V4)]
    if prefer == 'v6':
        table = table[1:]
    elif prefer == 'lat950':
        table = table[2:]
    for name, fn in table:
        pts = [tuple(p) for p in fn()]
        ok, info = certify_net(pts, dense=dense)
        say('  覆盖网自检 %s：%s' % (name, json.dumps(info, ensure_ascii=False)))
        if ok:
            return pts, name
    raise Fatal('所有问题四覆盖网都没有通过启动自检，拒绝开跑')


# ---------------------------------------------------------------- 兜底

def emergency_clear(world, say=print):
    """算法层抛异常后的最后一道兜底：对拿到过示向度但仍未清除的频道，原样执行 75×3 有限清除网格。"""
    for ch, (p0, theta) in sorted(world.first.items()):
        if ch in world.cleared:
            continue
        say('  兜底清除频道 %d（首测点 %.1f, %.1f，示向度 %.2f°）'
            % (ch, p0[0], p0[1], math.degrees(theta)))
        poly = update(initial_poly(), p0, theta)
        done = False
        for c, _ in fallback_cells(poly, p0, theta):
            if world.clear(c, ch):
                done = True
                break
        if done:
            continue
        for c, _ in fallback_cells(None, p0, theta):
            if world.clear(c, ch):
                break


# ---------------------------------------------------------------- 主程序

def run(args):
    C = cfg(**CFG4)
    say = print
    say('策略 B：问题%s ——%s' % (args.problem,
        ' 方案四（正八边形 974 m 八点覆盖网 + 顺路清除 + ALNS 收尾）' if args.problem == 3
        else ' 方案七（可认证非规则三角网 + 联合重规划 + 服务簇 + 计数提前停）'))
    say('参数：' + json.dumps(C, ensure_ascii=False))

    if args.problem == 3:
        net = [tuple(p) for p in NET3()]
        net_name = '正八边形 974 m（8 点）'
        say('  覆盖半径 %.4f m < 1000 m（余量 %.2f m）'
            % (max(974., math.sqrt(1800**2 + 974**2 - 2*1800*974*math.cos(math.radians(22.5)))),
               1000 - max(974., math.sqrt(1800**2 + 974**2 - 2*1800*974*math.cos(math.radians(22.5))))))
    else:
        net, net_name = pick_net4(args.net, dense=not args.quick_check, say=say)
    say('  使用覆盖网：%s，%d 个点' % (net_name, len(net)))

    log = args.log or ('官方测试日志_问题%d_%s.jsonl' % (args.problem, time.strftime('%Y%m%d_%H%M%S')))
    client = Client(args.base, args.robot_id, timeout=args.timeout, reserve=args.reserve,
                    retries=args.retries, logfile=log)
    world = RemoteWorld(client)
    say('连接 %s，robot_id=%s，日志 %s' % (args.base, args.robot_id, log))

    t_wall = time.monotonic()
    status, detail = 'unknown', ''
    client.enter()
    try:
        if args.problem == 3:
            solve(world, False, net, C)
        else:
            solve6(world, net, C)
        status = 'completed'
    except Stop as e:
        status, detail = 'real_time_budget', str(e)
        say('！现实时间预算用尽：%s' % e)
    except Fatal:
        status = 'protocol_error'
        raise
    except BaseException as e:
        status, detail = 'fallback_after_error', '%s: %s' % (e.__class__.__name__, e)
        say('！算法层异常：%s —— 转入有限兜底' % detail)
        client._log({'ev': 'algo_error', 'error': detail})
        try:
            emergency_clear(world, say)
            status = 'fallback_done'
        except Stop as e2:
            status, detail = 'fallback_truncated', str(e2)
        except BaseException as e2:
            status, detail = 'fallback_failed', '%s: %s' % (e2.__class__.__name__, e2)
    finally:
        try:
            client.leave()
        except BaseException as e:
            say('！/exit 未成功：%r' % e)
        summary = {
            'problem': args.problem, 'status': status, 'detail': detail,
            'net': net_name, 'points': len(net),
            'robot_id': args.robot_id, 'base': args.base,
            'cleared_channels': sorted(world.cleared), 'cleared_count': len(world.cleared),
            'server_virtual_time_s': client.vt,
            'local_virtual_time_s': round(world.time, 3),
            'virtual_time_drift_s': round(world.drift(), 6),
            'time_breakdown_s': {'move': round(world.moves, 3), 'detect': world.detect,
                                 'switch': world.switch, 'clear': world.cleartime},
            'actions': world.actions, 'http_requests': client.n_http, 'retries': client.n_retry,
            'measure_results': {'direction': world.n_direction, 'near': world.n_near,
                                'no_signal': world.n_nosignal},
            'real_seconds_used': round(time.monotonic() - t_wall, 1),
            'real_seconds_left': round(client.remaining_real_s(), 1),
            'log': log,
        }
        client._log({'ev': 'summary', **summary})
        Path(log).with_suffix('.summary.json').write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
        say('\n===== 本局小结 =====')
        say(json.dumps(summary, ensure_ascii=False, indent=2))
        if abs(world.drift()) > 1e-3:
            say('！本地复算的虚拟时间与模拟器相差 %.3f s，请核对计时口径' % world.drift())
    return summary


def main():
    ap = argparse.ArgumentParser(description='2026 国赛 B 题 · 官方模拟器正式测试主程序（策略 B）')
    ap.add_argument('--problem', type=int, choices=(3, 4), help='3=全向源；4=混合定向/全向源')
    ap.add_argument('--robot-id', dest='robot_id', help='参赛队号，必须与模拟器当前登录队号逐字节一致')
    ap.add_argument('--base', default=DEFAULT_BASE, help='模拟器地址，默认 %s' % DEFAULT_BASE)
    ap.add_argument('--timeout', type=float, default=5.0, help='单次 HTTP 超时秒数，默认 5')
    ap.add_argument('--reserve', type=float, default=25.0, help='为收尾预留的现实秒数，默认 25')
    ap.add_argument('--retries', type=int, default=4, help='网络故障时的重放次数，默认 4')
    ap.add_argument('--net', choices=('auto', 'v6', 'lat950'), default='auto', help='问题四覆盖网，默认自检后用方案七')
    ap.add_argument('--log', help='动作日志文件名（JSONL），默认按时间生成')
    ap.add_argument('--quick-check', action='store_true', help='跳过覆盖网的稠密复验，只做解析证书')
    ap.add_argument('--selfcheck', action='store_true', help='不联网，只验证三张覆盖网并退出')
    args = ap.parse_args()

    if args.selfcheck:
        print('覆盖网证书自检（不连接模拟器）')
        pts3 = [tuple(p) for p in NET3()]
        rho = max(974., math.sqrt(1800**2 + 974**2 - 2*1800*974*math.cos(math.radians(22.5))))
        print('  问题三 正八边形 974 m：%d 点，覆盖半径 %.4f m，余量 %.2f m，%s'
              % (len(pts3), rho, 1000-rho, '通过' if rho < 1000 else '不通过'))
        for name, fn in (('NET4_V7（方案七）', NET4_V7), ('NET4_V6（方案六）', NET4_V6),
                         ('h=950 规则格网（方案四）', NET4_V4)):
            ok, info = certify_net([tuple(p) for p in fn()], dense=not args.quick_check)
            print('  问题四 %s：%s %s' % (name, '通过' if ok else '不通过',
                                        json.dumps(info, ensure_ascii=False)))
        return 0

    if args.problem is None or not args.robot_id:
        ap.error('正式测试必须同时给出 --problem 与 --robot-id（先用 --selfcheck 做离线自检）')
    try:
        run(args)
    except Fatal as e:
        print('！停机：%s' % e, file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
