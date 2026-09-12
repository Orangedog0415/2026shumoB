"""【5.2】可认证的非规则三角网 + 路线联合优化（模拟退火）。

证书：对点集 Q 做 Delaunay 三角剖分；要求 (1) conv(Q) 包住半径 1800 m 的目标圆盘；
      (2) 每个与圆盘相交的三角形三边都 ≤1000 m。于是任一源 G∈D 落在某三角形内，
      到三顶点的距离 ≤ 最长边 ≤1000 m（三角形的直径就是最长边），且 G 在三顶点凸包内，
      因此不论定向方向如何，至少一个顶点落在它的覆盖半平面内 —— 与规则格网同构的证明，但允许顶点自由移动。
目标（代理）：T̂ = 巡回/5 + 42·k，其中 42 s ≈ 一个覆盖点上 7 个空频道 ×(5 s 检测+1 s 切换)。
结果：从 h=900 规则格网（27 点、23.9 km）退火到 27 点、17.8 km，代理目标降约 1200 s/局；
      解析证书成立（最长边 998.0 m），稠密“位置×朝向”复验漏测 0。该网已写入 方案四_实验台.py 的 NET4_V6。
需要 numpy、scipy。运行：python 方案五_5.2_非规则三角网优化.py（约 2–4 分钟）；输出 results/方案五_5.2_输出.txt
"""
import math, random, sys, json, time
import numpy as np
from scipy.spatial import Delaunay, ConvexHull

R=1800.; EMAX=1000.
def seg_pt_dist(p,a,b):
    ax,ay=a; bx,by=b; px,py=p; dx,dy=bx-ax,by-ay
    t=0. if dx==dy==0 else max(0,min(1,((px-ax)*dx+(py-ay)*dy)/(dx*dx+dy*dy)))
    return math.hypot(px-(ax+t*dx),py-(ay+t*dy))
def tri_hits_disk(V):
    s=[(V[(i+1)%3][0]-V[i][0])*(-V[i][1])-(V[(i+1)%3][1]-V[i][1])*(-V[i][0]) for i in range(3)]
    if all(z>=0 for z in s) or all(z<=0 for z in s): return True      # 原点在三角形内
    return min(seg_pt_dist((0,0),V[i],V[(i+1)%3]) for i in range(3))<R
def feasible(Q):
    P=np.array(Q)
    if len(P)<3: return False,None
    try:
        hull=ConvexHull(P); tri=Delaunay(P)
    except Exception: return False,None
    for a,b,c in hull.equations:              # a*x+b*y+c<=0 内部
        n=math.hypot(a,b)
        if c>=0: return False,None            # 原点不在内部
        if -c/n < R-1e-9: return False,None   # conv(Q) 必须包住整个圆盘
    for simp in tri.simplices:
        V=[tuple(P[i]) for i in simp]
        if tri_hits_disk(V):
            if max(math.dist(V[i],V[(i+1)%3]) for i in range(3))>EMAX+1e-9: return False,None
    return True,tri
def _plen(seq,start=(0.,0.)):
    return math.dist(start,seq[0])+sum(math.dist(seq[i],seq[i+1]) for i in range(len(seq)-1))
def tour_len(Q):
    import importlib.util
    from pathlib import Path
    global _L
    T=_L.tour_nn2opt([tuple(q) for q in Q])
    return _plen(T),T
def obj(Q,per_point=42.):
    l,_=tour_len(Q); return l/5+per_point*len(Q),l
def anneal(Q0,iters=2500,T0=60.,T1=2.,seed=0,per_point=42.):
    rng=random.Random(seed)
    Q=[tuple(q) for q in Q0]; ok,_=feasible(Q); assert ok,'初始网不合格'
    f,l=obj(Q,per_point); best=(f,l,Q[:])
    for it in range(iters):
        T=T0*(T1/T0)**(it/iters)
        m=rng.random(); C=[list(q) for q in Q]
        if m<.55:                      # 移动一个点
            i=rng.randrange(len(C)); s=rng.choice([20,60,150,300])
            C[i]=[C[i][0]+rng.gauss(0,s),C[i][1]+rng.gauss(0,s)]
        elif m<.8 and len(C)>12:       # 删除一个点
            C.pop(rng.randrange(len(C)))
        elif m<.9:                     # 增加一个点（在某条长边中点附近）
            i,j=rng.sample(range(len(C)),2)
            C.append([(C[i][0]+C[j][0])/2+rng.gauss(0,60),(C[i][1]+C[j][1])/2+rng.gauss(0,60)])
        else:                          # 把两个近点合并
            if len(C)>12:
                i=rng.randrange(len(C))
                j=min((k for k in range(len(C)) if k!=i),key=lambda k:math.dist(C[i],C[k]))
                C[i]=[(C[i][0]+C[j][0])/2,(C[i][1]+C[j][1])/2]; C.pop(j)
        C=[tuple(c) for c in C]
        ok,_=feasible(C)
        if not ok: continue
        f2,l2=obj(C,per_point)
        if f2<f or rng.random()<math.exp(-(f2-f)/T):
            Q,f,l=C,f2,l2
            if f<best[0]: best=(f,l,Q[:])
    return best

if __name__=='__main__':
    import importlib.util, json
    from pathlib import Path
    HERE=Path(__file__).resolve().parent
    _s=importlib.util.spec_from_file_location('L',str(HERE/'方案四_实验台.py')); _L=importlib.util.module_from_spec(_s); _s.loader.exec_module(_L)
    globals()['_L']=_L
    _c=importlib.util.spec_from_file_location('C',str(HERE/'方案四_覆盖网优化.py')); CN=importlib.util.module_from_spec(_c); _c.loader.exec_module(CN)
    out=[]; log=lambda s:(out.append(s),print(s,flush=True))
    A=[tuple(p) for p in _L.lattice(900.,0.,487.0,math.radians(10.))]
    ok,_=feasible(A); f0,l0=obj(A)
    log('起点（h=900 规则格网）：%d 点，巡回 %.0f m，代理目标 %.0f s，解析证书 %s'%(len(A),l0,f0,ok))
    best=None
    for seed in range(4):
        f,l,Q=anneal(A,iters=1800,seed=seed)
        log('  退火 seed %d：%d 点，巡回 %.0f m，代理 %.0f s'%(seed,len(Q),l,f))
        if best is None or f<best[0]: best=(f,l,Q)
    f,l,Q=best
    ok,tri=feasible(Q)
    import numpy as np
    P=np.array(Q)
    maxe=max(max(math.dist(tuple(P[i]),tuple(P[j])) for i,j in ((s[0],s[1]),(s[1],s[2]),(s[2],s[0]))) for s in tri.simplices if tri_hits_disk([tuple(P[k]) for k in s]))
    log('最优：%d 点，巡回 %.0f m，代理 %.0f s（起点 %.0f s）；解析证书 %s，相交三角形最长边 %.1f m'%(len(Q),l,f,f0,ok,maxe))
    log('稠密“位置×朝向”复验漏测：%d'%CN.missed_pairs(Q,nang=360,nrad=60,ndir=72))
    log('参考：仓库里 NET4_V6 是同一方法多跑几轮后的结果（27 点，17 830 m）。退火有随机性，单次运行未必复现同一张网。')
    json.dump([list(q) for q in Q],open(HERE/'results'/'方案五_5.2_新网.json','w'))
    (HERE/'results'/'方案五_5.2_输出.txt').write_text('\n'.join(out)+'\n',encoding='utf-8')
