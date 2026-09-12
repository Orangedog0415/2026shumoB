"""【问题二】用差分进化 DE 求第二检测点，与 50 m 网格扫描的结果对照（《优化算法》建议 ①）。

目标与最终文档 §4.2 一致：F(S)=Ĵ(S)+0.05·‖S−S₁‖/5，Ĵ 为“源取遍可行域采样点、误差取 ±1.005°/0”时
第二次交会后定位区域直径的最大值；硬约束是可行域 P 的所有顶点到 S 的距离 ≤999 m（保证收得到信号）。
只用标准库。运行：python 问题二_DE选点.py（约 1 分钟），输出写入 results/问题二_DE选点输出.txt
"""
import math, random, importlib.util, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
_s=importlib.util.spec_from_file_location('L',str(HERE/'方案四_实验台.py')); L=importlib.util.module_from_spec(_s); _s.loader.exec_module(L)
J=L.J; dist=J.dist; D=J.DELTA
first=(0.,0.)
poly=J.update(J.initial_poly(),first,0.)
sample=[]
for a,b in zip(poly,poly[1:]+poly[:1]):
    c=max(1,math.ceil(dist(a,b)/100))
    sample += [(a[0]+i/c*(b[0]-a[0]),a[1]+i/c*(b[1]-a[1])) for i in range(c)]
sample.append(J.centroid(poly))
def F(S):
    """返回 (F, Ĵ, 最远顶点距离)；不可行时 F=+inf。"""
    rad=J.radius(poly,S)
    if rad>999: return float('inf'),None,rad
    worst=0.
    for g in sample:
        if dist(g,S)<=5: worst=max(worst,10.); continue
        ang=math.atan2(g[1]-S[1],g[0]-S[0])
        for e in (-D,0,D):
            worst=max(worst,J.diameter(J.wedge(poly,S,ang+e))[0])
    return worst+.05*dist(first,S)/5, worst, rad
def de(pop=24,gen=40,F_=.7,CR=.9,seed=0,lo=(0.,-1000.),hi=(1500.,1000.),seeds=()):
    rng=random.Random(seed)
    X=[list(s) for s in seeds]
    while len(X)<pop: X.append([rng.uniform(lo[0],hi[0]),rng.uniform(lo[1],hi[1])])
    fx=[F(tuple(x))[0] for x in X]; hist=[]
    for g in range(gen):
        for i in range(len(X)):
            a,b,c=rng.sample([j for j in range(len(X)) if j!=i],3)
            v=[X[a][k]+F_*(X[b][k]-X[c][k]) for k in (0,1)]
            v=[min(max(v[k],lo[k]),hi[k]) for k in (0,1)]
            u=[v[k] if (rng.random()<CR or k==rng.randint(0,1)) else X[i][k] for k in (0,1)]
            fu=F(tuple(u))[0]
            if fu<fx[i]: X[i],fx[i]=u,fu
        hist.append(min(fx))
    i=min(range(len(X)),key=lambda i:fx[i]); return tuple(X[i]),fx[i],hist
if __name__=='__main__':
    out=[]
    def log(s): out.append(s); print(s,flush=True)
    fg,jg,rg=F((850.,-500.))
    log('网格扫描（50 m，最终文档采用）：S₂=(850, −500)，F=%.6f，最坏直径 Ĵ=%.6f，最远顶点 %.1f m'%(fg,jg,rg))
    best=None
    for seed in range(5):
        S,f,hist=de(seed=seed,seeds=[(850.,-500.)] if seed==0 else [])
        fj=F(S); log('  DE 第 %d 次（%s）：S₂=(%.1f, %.1f)，F=%.6f，Ĵ=%.6f'%(seed+1,'含网格解作初始个体' if seed==0 else '纯随机初始',S[0],S[1],f,fj[1]))
        if best is None or f<best[1]: best=(S,f,fj)
    S,f,fj=best
    log('DE 最优：S₂=(%.1f, %.1f)，F=%.6f，最坏直径 %.6f m，最远顶点 %.1f m'%(S[0],S[1],f,fj[1],fj[2]))
    log('相对网格解：F %+.3f%%（网格解已接近最优；DE 的价值是不依赖网格分辨率，且可直接给出连续解）'%(100*(f/fg-1)))
    (HERE/'results'/'问题二_DE选点输出.txt').write_text('\n'.join(out)+'\n',encoding='utf-8')
