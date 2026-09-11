"""【方案一】交接版压力测试：换误差模型、接收半径取下限、源全在边界（问题四朝外），检查是否全清并统计时间。
只读调用 code/baseline/方案一_最终方案验证.py 中的 solve()/World，不修改交接文件；结果写到 results/。运行约 30–60 s。"""
import math, random, copy, hashlib, zlib, importlib.util, statistics as st, json, time
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('J',str(HERE.parent/'baseline'/'方案一_最终方案验证.py')); J=importlib.util.module_from_spec(spec); spec.loader.exec_module(J)
dist=J.dist
def h01(*k):
    return int(hashlib.md5(repr(k).encode()).hexdigest()[:12],16)/16**12
ERR={
 'orig_sin': None,
 'iid_uniform': lambda p,ch,salt: 2*h01(round(p[0],3),round(p[1],3),ch,salt)-1,
 'const_+1': lambda p,ch,salt: 1.0,
 'const_-1': lambda p,ch,salt: -1.0,
 'iid_extreme±1': lambda p,ch,salt: 1.0 if h01(round(p[0],3),round(p[1],3),ch,salt)<.5 else -1.0,
}
class W(J.World):
    def __init__(s,src,salt,ef): super().__init__(src,salt); s.ef=ef; s.fb=0
    def measure(s,p,ch):
        if s.ef is None: return super().measure(p,ch)
        s.move(p); sw=int(ch!=s.channel); s.channel=ch; s.time+=5+sw; s.detect+=5; s.switch+=sw; s.actions+=1
        src=s.sources.get(ch)
        if src is None or src['cleared']: return 'no_signal',None
        d=dist(p,src['g'])
        if d>src['r'] or (src['type']=='D' and J.dot((p[0]-src['g'][0],p[1]-src['g'][1]),src['u'])<-1e-10): return 'no_signal',None
        if d<=5: return 'near',None
        a=math.degrees(math.atan2(src['g'][1]-p[1],src['g'][0]-p[0]))+s.ef(p,ch,s.salt)
        return 'direction',math.radians(round(a%360,2)%360)
FB=[0]
_orig=J.fallback_cells
def cells(poly,anchor,theta):
    if poly is not None: FB[0]+=1
    return _orig(poly,anchor,theta)
J.fallback_cells=cells
def gen(rng,n,mixed,rmode,layout='uniform',pD=.65):
    src={}
    for k,ch in enumerate(rng.sample(range(1,21),n)):
        if layout=='uniform':
            a=rng.random()*2*math.pi; rr=1800*math.sqrt(rng.random())
        else:  # boundary ring, facing outward
            a=2*math.pi*k/n+rng.uniform(-.05,.05); rr=rng.uniform(1700,1800)
        r=1000.0 if rmode=='min' else rng.uniform(1000,1500)
        if layout=='outward': kind,ang=('D',a) if mixed else ('O',0)
        else: kind,ang=('D' if mixed and rng.random()<pD else 'O'), rng.random()*2*math.pi
        src[ch]=J.source((rr*math.cos(a),rr*math.sin(a)),r,kind,ang)
    return src
res=[]; t0=time.time()
for mixed in (False,True):
  for layout in ('uniform','outward'):
    for rmode in ('rand','min'):
      for en,ef in ERR.items():
        rng=random.Random(zlib.crc32(repr((mixed,layout,rmode)).encode()))  # 确定性种子（内置hash对字符串随进程随机）
        for n in (10,13,16):
          for rep in range(8):
            src=gen(rng,n,mixed,rmode,layout)
            w=W(copy.deepcopy(src),rep,ef); FB[0]=0
            try:
                J.solve(w,mixed); ok=True; err=''
            except AssertionError as e:
                ok=False; err=str(e)
            res.append(dict(mixed=mixed,layout=layout,rmode=rmode,err=en,n=n,ok=ok,why=err,
                            t=w.time,per=w.time/n,act=w.actions,move=w.moves/w.time,fb=FB[0]/n))
print('runs',len(res),'failures',sum(not r['ok'] for r in res),'elapsed %.0fs'%(time.time()-t0))
for r in res:
    if not r['ok']: print('FAIL',r)
def summ(sel,label):
    s=[r for r in res if sel(r)]
    per=[r['per'] for r in s]; T=[r['t'] for r in s]
    print('%-34s n=%3d 全清%3d | 每源 均%4.0f 中%4.0f P90 %4.0f 最大%4.0f | 总 均%6.0f 最大%6.0f | 动作最大%4d | 移动占比%3.0f%% | 兜底率%3.0f%%'%(
        label,len(s),sum(r['ok'] for r in s),st.mean(per),st.median(per),sorted(per)[int(.9*len(per))-1],max(per),st.mean(T),max(T),max(r['act'] for r in s),
        100*st.mean(r['move'] for r in s),100*st.mean(r['fb'] for r in s)))
for mixed in (False,True):
    q='Q4' if mixed else 'Q3'
    summ(lambda r:r['mixed']==mixed and r['layout']=='uniform' and r['rmode']=='rand' and r['err']=='orig_sin', q+' 基准(交接误差模型)')
    for en in ERR:
        if en!='orig_sin': summ(lambda r,en=en:r['mixed']==mixed and r['layout']=='uniform' and r['rmode']=='rand' and r['err']==en, q+' 误差='+en)
    summ(lambda r:r['mixed']==mixed and r['layout']=='uniform' and r['rmode']=='min', q+' 接收半径全=1000')
    summ(lambda r:r['mixed']==mixed and r['layout']=='outward', q+' 源全在边界'+('且朝外' if mixed else ''))
    for n in (10,13,16):
        summ(lambda r,n=n:r['mixed']==mixed and r['n']==n and r['layout']=='uniform' and r['rmode']=='rand', q+' N=%d(均匀布源,各误差)'%n)
json.dump(res,open(HERE/'results'/'方案一_压力测试结果.json','w',encoding='utf-8'),ensure_ascii=False,indent=0)
