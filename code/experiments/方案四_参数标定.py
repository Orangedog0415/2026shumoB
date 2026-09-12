"""【方案四·3.1】用贝叶斯优化（高斯过程 + EI 采集函数，仅 numpy）标定策略参数。

目标：0.5·(问题三每源时间/基线 + 问题四每源时间/基线)，基线取方案三（335.7 / 745.0 s）。
训练集为 cases(1)，另用 cases(202) 验证是否过拟合。约 50 次评估，每次评估跑 60 局，全程约 2 分钟。
需要 numpy。运行：python 方案四_参数标定.py ；输出写入 results/方案四_参数标定输出.txt
"""
import numpy as np, math, sys, time, json, importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent
_s=importlib.util.spec_from_file_location('L',str(HERE/'方案四_实验台.py')); lab=importlib.util.module_from_spec(_s); _s.loader.exec_module(lab)
SPACE=[('x',0.,1500.,0),('r_ok',40.,400.,0),('probe_angle',10.,45.,0),('lp_cap',300.,1000.,0),
       ('lp_angle',35.,75.,0),('lp_max',1,6,1),('cover_k',1,6,1)]
def to_cfg(v,**extra):  # 归一化向量 -> 配置
    d={}
    for (n,lo,hi,isint),z in zip(SPACE,v):
        val=lo+z*(hi-lo); d[n]=int(round(val)) if isint else float(val)
    d.update(extra); return lab.cfg(**d)
class GP:
    def __init__(s,l=.35,sig=1.0,noise=1e-4): s.l=l; s.sig=sig; s.noise=noise
    def K(s,A,B):
        d2=((A[:,None,:]-B[None,:,:])**2).sum(-1); return s.sig*np.exp(-.5*d2/s.l**2)
    def fit(s,X,y):
        s.X=X; s.mu=y.mean(); s.y=y-s.mu
        K=s.K(X,X)+s.noise*np.eye(len(X)); s.L=np.linalg.cholesky(K)
        s.a=np.linalg.solve(s.L.T,np.linalg.solve(s.L,s.y))
    def pred(s,Xs):
        Ks=s.K(s.X,Xs); mu=Ks.T@s.a+s.mu
        v=np.linalg.solve(s.L,Ks); var=np.clip(s.sig-(v**2).sum(0),1e-12,None)
        return mu,np.sqrt(var)
def ei(mu,sd,best,xi=.01):
    from math import erf
    z=(best-xi-mu)/sd
    Phi=.5*(1+np.vectorize(erf)(z/np.sqrt(2))); phi=np.exp(-.5*z*z)/np.sqrt(2*np.pi)
    return (best-xi-mu)*Phi+sd*phi
def run(objective,n_init=12,n_iter=38,seed=0,x0=None):
    rng=np.random.default_rng(seed); D=len(SPACE)
    X=[]; y=[]
    pts=[x0] if x0 is not None else []
    pts+= list((rng.random((n_init,D))+np.arange(n_init)[:,None]/n_init)%1.0)  # 粗 LHS
    for p in pts:
        X.append(np.array(p)); y.append(objective(np.array(p)))
    X=np.array(X); y=np.array(y)
    for it in range(n_iter):
        gp=GP(); gp.fit(X,y)
        cand=rng.random((2000,D))
        mu,sd=gp.pred(cand); a=ei(mu,sd,y.min())
        nx=cand[int(np.argmax(a))]
        ny=objective(nx)
        X=np.vstack([X,nx]); y=np.append(y,ny)
    i=int(np.argmin(y)); return X[i],y[i],X,y
if __name__=='__main__':
    C3,C4=lab.cases(1); V3,V4=lab.cases(202)
    N3=lab.NET3(); N4=lab.NET4_V4()
    LOG=[]
    B3,B4=335.658,744.983
    hist=[]
    def obj(v):
        C=to_cfg(v,final='alns'); t=time.time()
        a,b=lab.evaluate(C,N3,N4,C3,C4); s=.5*(a/B3+b/B4)
        hist.append((list(map(float,v)),a,b,s)); line='  eval %5.3f  Q3 %6.1f Q4 %6.1f'%(s,a,b); LOG.append(line); print(line,flush=True)
        return s
    x0=np.array([(600-0)/1500,(150-40)/360,(25-10)/35,(700-300)/700,(55-35)/40,(4-1)/5,(3-1)/5])
    best,bv,X,y=run(obj,x0=x0)  # 12 个初始点 + 38 次 EI 迭代
    C=to_cfg(best); print('\n最优参数',{k:C[k] for k,_,_,_ in SPACE},'score %.4f'%bv)
    a,b=lab.evaluate(C,N3,N4,C3,C4); print('训练集 Q3 %.1f Q4 %.1f'%(a,b))
    va,vb=lab.evaluate(C,N3,N4,V3,V4); print('验证集 Q3 %.1f Q4 %.1f'%(va,vb))
    v0a,v0b=lab.evaluate(lab.cfg(),N3,lab.NET4_V3(),V3,V4); print('验证集 基线 Q3 %.1f Q4 %.1f'%(v0a,v0b))
    par={k:(round(C[k],1) if not isinstance(C[k],int) else C[k]) for k,_,_,_ in SPACE}
    LOG=['方案四·3.1 贝叶斯优化（%d 次评估）'%len(hist)]+LOG+[
        '','最优参数：'+'，'.join('%s=%g'%(k,v) for k,v in par.items()),
        '训练集  问题三 %.1f  问题四 %.1f'%(a,b),'验证集  问题三 %.1f  问题四 %.1f'%(va,vb),
        '验证集（方案三基线参数） 问题三 %.1f  问题四 %.1f'%(v0a,v0b)]
    (HERE/'results'/'方案四_参数标定输出.txt').write_text('\n'.join(LOG)+'\n',encoding='utf-8')
    json.dump({'best':par,'train':[a,b],'val':[va,vb],'val_base':[v0a,v0b]},open(HERE/'results'/'方案四_参数标定.json','w'),ensure_ascii=False,indent=1)
