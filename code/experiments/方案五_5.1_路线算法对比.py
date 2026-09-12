"""【5.1】固定覆盖网，只换更强的开放路径启发式：最近邻+2-opt（现用） vs 2-opt+Or-opt+双桥多起点。
结论：在 27 点规模上没有改进（0.00%），路线优化的收益只能来自“移动/减少覆盖点”，见 5.2。
只用标准库。运行：python 方案五_5.1_路线算法对比.py（约 1 分钟）；输出 results/方案五_5.1_输出.txt
"""
import math, random, importlib.util, time
from pathlib import Path
HERE=Path(__file__).resolve().parent
_s=importlib.util.spec_from_file_location('L',str(HERE/'方案四_实验台.py')); L=importlib.util.module_from_spec(_s); _s.loader.exec_module(L)
def plen(seq,start=(0.,0.)):
    return math.dist(start,seq[0])+sum(math.dist(seq[i],seq[i+1]) for i in range(len(seq)-1))
def nn(pts,start):
    rem=list(pts); out=[]; cur=start
    while rem:
        q=min(rem,key=lambda q:math.dist(cur,q)); out.append(q); rem.remove(q); cur=q
    return out
def two_opt(seq,start):
    P=[start]+list(seq); n=len(seq); imp=True
    while imp:
        imp=False
        for i in range(1,n):
            for j in range(i+1,n+1):
                a,b=P[i-1],P[i]; c=P[j]; d=P[j+1] if j+1<=n else None
                old=math.dist(a,b)+(math.dist(c,d) if d else 0)
                new=math.dist(a,c)+(math.dist(b,d) if d else 0)
                if new<old-1e-9: P[i:j+1]=P[i:j+1][::-1]; imp=True
    return P[1:]
def or_opt(seq,start,maxseg=3):
    P=list(seq); imp=True
    while imp:
        imp=False; base=plen(P,start)
        for l in range(1,maxseg+1):
            for i in range(len(P)-l+1):
                seg=P[i:i+l]; rest=P[:i]+P[i+l:]
                for j in range(len(rest)+1):
                    cand=rest[:j]+seg+rest[j:]
                    if plen(cand,start)<base-1e-9: P=cand; imp=True; base=plen(P,start); break
                if imp: break
            if imp: break
    return P
def strong(pts,start=(0.,0.),restarts=6,iters=80,seed=0):
    rng=random.Random(seed)
    best=or_opt(two_opt(nn(pts,start),start),start); bl=plen(best,start)
    for _ in range(restarts):
        cur=best[:]
        for _ in range(iters):
            s=cur[:]
            if len(s)>=8:
                a,b,c=sorted(rng.sample(range(1,len(s)),3)); s=s[:a]+s[b:c]+s[a:b]+s[c:]
            else:
                i,j=sorted(rng.sample(range(len(s)),2)); s[i],s[j]=s[j],s[i]
            s=or_opt(two_opt(s,start),start); l=plen(s,start)
            if l<bl-1e-9: best,bl,cur=s,l,s
    return bl
if __name__=='__main__':
    out=[]; log=lambda s:(out.append(s),print(s,flush=True))
    for name,net in (('方案四 h=950 格网',L.NET4_V4()),('A 方案 h=900 格网',L.lattice(900.,0.,487.0,math.radians(10.))),
                     ('方案六 非规则三角网',L.NET4_V6()),('问题三 正八边形',L.NET3())):
        T=L.tour_nn2opt(net); cur=plen(T)
        t0=time.time(); best=strong([tuple(p) for p in net])
        log('%-20s %2d 点：最近邻+2opt %8.0f m → 强局部搜索 %8.0f m（%+.2f%%，%.0f s）'%(name,len(net),cur,best,100*(best/cur-1),time.time()-t0))
    log('结论：固定点集上再加 Or-opt / 双桥多起点没有改进，2-opt 已在很强的局部最优；继续投入 LKH 不划算。')
    (HERE/'results'/'方案五_5.1_输出.txt').write_text('\n'.join(out)+'\n',encoding='utf-8')
