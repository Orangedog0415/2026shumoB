"""【方案四·3.2】覆盖网优化：集合覆盖（贪心 + 局部改进，LP 松弛给下界）与三角格偏移搜索。

结论（见 results/方案四_覆盖网优化输出.txt）：
  问题三：集合覆盖确认“最少点数”约为 7，但按时间目标不划算——8 点正八边形(974 m) 的巡回最短，方案三、四都用它。
  问题四：按抽样做的集合覆盖会漏测（稠密复验有反例），不能当保证；改为在“边长 h≤1000 m 三角格”这一有解析
          证书的族内搜索偏移与旋转，得到 h=950、27 点、巡回 25.1 km，比方案三的 h=990 网短 1.6 km。
需要 numpy 与 scipy。运行：python 方案四_覆盖网优化.py（约 5–8 分钟）
"""
import numpy as np, math, json, sys, importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent
_s=importlib.util.spec_from_file_location('L',str(HERE/'方案四_实验台.py')); L=importlib.util.module_from_spec(_s); _s.loader.exec_module(L)
R,RC=1800.,1000.
OUT=[]
def log(s): OUT.append(s); print(s,flush=True)
def disk_samples(step):
    pts=[(0.,0.)]; r=step
    while r<=R+1e-9:
        n=max(6,int(2*math.pi*r/step))
        pts+= [(r*math.cos(2*math.pi*k/n),r*math.sin(2*math.pi*k/n)) for k in range(n)]
        r+=step
    return np.array(pts)
def cand_grid(step,rmax):
    n=int(rmax/step)
    return np.array([(i*step,j*step) for i in range(-n,n+1) for j in range(-n,n+1) if math.hypot(i*step,j*step)<=rmax])
def greedy(A,k=None,rng=None,rand=0):
    unc=np.ones(A.shape[1],bool); sel=[]
    while unc.any():
        g=A[:,unc].sum(1)
        i=int(rng.choice(np.argsort(-g)[:max(1,rand)])) if (rand and rng is not None) else int(np.argmax(g))
        if g[i]==0: return None
        sel.append(i); unc&=~A[i]
        if k and len(sel)>k: return None
    return sel
def lp_bound(A):
    from scipy.optimize import linprog
    r=linprog(np.ones(A.shape[0]),A_ub=-A.T.astype(float),b_ub=-np.ones(A.shape[1]),bounds=(0,1),method='highs')
    return r.fun if r.success else None
def tour_len(pts):
    T=L.tour_nn2opt([tuple(p) for p in pts])
    return L.dist((0,0),T[0])+sum(L.dist(T[i],T[i+1]) for i in range(len(T)-1))
def improve(A,sel,cand,iters,rng):
    sel=list(sel); best=tour_len(cand[sel])
    for _ in range(iters):
        i=int(rng.integers(len(sel))); j=int(rng.integers(A.shape[0]))
        if j in sel: continue
        t=sel[:]; t[i]=j
        if not A[t].any(0).all(): continue
        Lt=tour_len(cand[t])
        if Lt<best-1e-6: sel,best=t,Lt
    return sel,best
def worst_cover_dist(net,step=8.):
    S=disk_samples(step); N=np.array(net)
    return float(np.sqrt(((S[:,None,:]-N[None,:,:])**2).sum(-1)).min(1).max())
def missed_pairs(net,nang=360,nrad=60,ndir=72):
    N=np.array(net); bad=0
    for i in range(nang):
        a=2*math.pi*i/nang
        rr=np.concatenate([np.linspace(0,1800,nrad),[1799.999,1800.]])
        G=np.stack([rr*math.cos(a),rr*math.sin(a)],1)
        dx=N[None,:,0]-G[:,None,0]; dy=N[None,:,1]-G[:,None,1]; near=(dx**2+dy**2)<=RC**2+1e-6
        for j in range(ndir):
            u=(math.cos(2*math.pi*j/ndir),math.sin(2*math.pi*j/ndir))
            bad+=int((~(near&((dx*u[0]+dy*u[1])>=-1e-9)).any(1)).sum())
    return bad
def q3(rng):
    log('\n[问题三] 距离覆盖的集合覆盖')
    S=disk_samples(30.); C=cand_grid(100.,1900.)
    A=(((C[:,None,0]-S[None,:,0])**2+(C[:,None,1]-S[None,:,1])**2)<=RC**2)
    log('  候选 %d 个，验证点 %d 个，LP 松弛下界 %.2f（整数最优 ≥ %d）'%(len(C),len(S),lp_bound(A),math.ceil(lp_bound(A))))
    for k in (7,8,9,10):
        best=None
        for t in range(40):
            sel=greedy(A,k=k,rng=rng,rand=4 if t else 0)
            if not sel: continue
            while len(sel)<k:
                sel=sel+[min((int(j) for j in rng.integers(0,len(C),40)),key=lambda j:tour_len(C[sel+[j]]))]
            sel,Lt=improve(A,sel,C,250,rng)
            if best is None or Lt<best[1]: best=(sel,Lt)
        if best:
            net=[tuple(map(float,p)) for p in C[best[0]]]
            log('  k=%2d：巡回 %.0f m，稠密复验最坏覆盖距离 %.1f m %s'%(k,best[1],worst_cover_dist(net),'✓' if worst_cover_dist(net)<=RC else '✗ 不满足覆盖'))
        else: log('  k=%2d：贪心未找到覆盖'%k)
    n8=L.NET3(); log('  对照 正八边形 974 m（8 点）：巡回 %.0f m，最坏覆盖距离 %.1f m ✓（解析式给出，余量 %.1f m）'%(tour_len(np.array(n8)),worst_cover_dist(n8),RC-worst_cover_dist(n8)))
def q4_setcover(rng):
    log('\n[问题四] 抽样式集合覆盖（位置 × 朝向）——反例')
    P=disk_samples(80.); C=cand_grid(120.,2900.); nd=16
    U=np.array([[math.cos(2*math.pi*i/nd),math.sin(2*math.pi*i/nd)] for i in range(nd)])
    dx=C[:,None,0]-P[None,:,0]; dy=C[:,None,1]-P[None,:,1]; near=(dx**2+dy**2)<=RC**2
    A=np.empty((len(C),len(P)*nd),bool)
    for d in range(nd): A[:,d::nd]=near&((dx*U[d,0]+dy*U[d,1])>=-1e-9)
    log('  设计样本：位置 %d × 朝向 %d = %d 个元素，候选 %d 个，LP 下界 %.2f'%(len(P),nd,len(P)*nd,len(C),lp_bound(A)))
    sel=greedy(A,rng=rng)
    net=[tuple(map(float,p)) for p in C[sel]]
    log('  贪心得 %d 点，巡回 %.0f m；但在更稠密的“位置×朝向”复验中漏测 %d 组合 → 抽样集合覆盖不能作为保证'%(len(sel),tour_len(C[sel]),missed_pairs(net)))
def q4_lattice():
    log('\n[问题四] 在“边长 h≤1000 m 三角格 + 保留相交三角形全部顶点”族内搜索（证书与最终文档 §5.2 相同）')
    best=[]
    for h in (990,970,950):
        for i in range(6):
            for j in range(6):
                for r in range(4):
                    ox=i*h/6; oy=j*h*math.sqrt(3)/2/6; rot=r*math.pi/12
                    pts=L.lattice(h,ox,oy,rot)
                    if len(pts)>30: continue
                    best.append((tour_len(np.array(pts)),len(pts),h,ox,oy,rot))
    best.sort()
    for Lt,n,h,ox,oy,rot in best[:3]:
        log('  h=%d 偏移(%.0f, %.0f) 旋转 %.0f°：%d 点，巡回 %.0f m'%(h,ox,oy,math.degrees(rot),n,Lt))
    cur=L.NET4_V3(); new=L.NET4_V4()
    log('  方案三 h=990 网：%d 点，巡回 %.0f m；方案四 h=950 网：%d 点，巡回 %.0f m，稠密复验漏测 %d'%(
        len(cur),tour_len(np.array(cur)),len(new),tour_len(np.array(new)),missed_pairs(new)))
if __name__=='__main__':
    rng=np.random.default_rng(0)
    q3(rng); q4_setcover(rng); q4_lattice()
    (HERE/'results'/'方案四_覆盖网优化输出.txt').write_text('\n'.join(OUT)+'\n',encoding='utf-8')
