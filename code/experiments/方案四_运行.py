"""【方案四】按采用配置运行，并与【方案一】【方案三】在同一批案例上对比，最后做保证性压力测试。

方案四 = 方案三 + 三项改进（见 方案四_实验台.py 顶部的版本对照）：
  3.1 贝叶斯优化标定的策略参数        3.2 问题四改用 h=950 偏移优化格网（27 点，巡回 25.1 km）
  3.3b 覆盖完成后的清除顺序改用 ALNS
覆盖证书、频道状态机、75×3 有限兜底与方案一、方案三完全相同。全部为本地仿真，非官方成绩。

运行：python 方案四_运行.py            （约 3–5 分钟）
      python 方案四_运行.py --quick    （跳过压力测试）
输出同时写入 results/方案四_运行输出.txt
"""
import argparse, copy, math, random, statistics as st, importlib.util, hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('L',str(HERE/'方案四_实验台.py')); L=importlib.util.module_from_spec(spec); spec.loader.exec_module(L)
J=L.J
CFG3=L.cfg(); CFG4=L.cfg(**L.CFG4)
N3=L.NET3(); N4_V3=L.NET4_V3(); N4_V4=L.NET4_V4()

def h01(*k): return int(hashlib.md5(repr(k).encode()).hexdigest()[:12],16)/16**12
ERR={'交接误差场':None,
     '每点独立均匀':lambda p,ch,s: 2*h01(round(p[0],3),round(p[1],3),ch,s)-1,
     '恒 +1°':lambda p,ch,s: 1.0, '恒 −1°':lambda p,ch,s: -1.0,
     '每点独立 ±1°':lambda p,ch,s: 1.0 if h01(round(p[0],3),round(p[1],3),ch,s)<.5 else -1.0}
class W(J.World):
    def __init__(s,src,salt,ef): super().__init__(src,salt); s.ef=ef
    def measure(s,p,ch):
        if s.ef is None: return super().measure(p,ch)
        s.move(p); sw=int(ch!=s.channel); s.channel=ch; s.time+=5+sw; s.detect+=5; s.switch+=sw; s.actions+=1
        src=s.sources.get(ch)
        if src is None or src['cleared']: return 'no_signal',None
        d=L.dist(p,src['g'])
        if d>src['r'] or (src['type']=='D' and J.dot((p[0]-src['g'][0],p[1]-src['g'][1]),src['u'])<-1e-10): return 'no_signal',None
        if d<=5: return 'near',None
        ang=math.degrees(math.atan2(src['g'][1]-p[1],src['g'][0]-p[0]))+s.ef(p,ch,s.salt)
        return 'direction',math.radians(round(ang%360,2)%360)

def per_source(C,mixed,net,cfg):
    return [L.solve(J.World(copy.deepcopy(s),i),mixed,net,cfg).time/len(s) for i,s in enumerate(C)]

def compare(tag,C3,C4):
    rows=[]
    for label,cfg,n4 in (('方案一',None,None),('方案三',CFG3,N4_V3),('方案四',CFG4,N4_V4)):
        if cfg is None:
            p3=[(lambda w:(J.solve(w,False),w.time/len(s))[1])(J.World(copy.deepcopy(s),i)) for i,s in enumerate(C3)]
            p4=[(lambda w:(J.solve(w,True),w.time/len(s))[1])(J.World(copy.deepcopy(s),i)) for i,s in enumerate(C4)]
        else:
            p3=per_source(C3,False,N3,cfg); p4=per_source(C4,True,n4,cfg)
        rows.append((label,p3,p4))
    out=[f'\n{tag}（问题三、四各 {len(C3)} 局）  每源平均定位清除时间 / s']
    b3=st.mean(rows[0][1]); b4=st.mean(rows[0][2])
    out.append('  %-6s %8s %8s %10s'%('','问题三','问题四','相对方案一'))
    for label,p3,p4 in rows:
        out.append('  %-6s %8.1f %8.1f   %5.1f%% / %5.1f%%'%(label,st.mean(p3),st.mean(p4),100*(st.mean(p3)/b3-1),100*(st.mean(p4)/b4-1)))
    w3=sum(y<x for x,y in zip(rows[1][1],rows[2][1])); w4=sum(y<x for x,y in zip(rows[1][2],rows[2][2]))
    out.append('  方案四优于方案三：问题三 %d/%d 局，问题四 %d/%d 局'%(w3,len(C3),w4,len(C4)))
    for label,p3,p4 in rows:
        out.append('    %-6s 按 N：'%label+'；'.join('N=%d %.0f/%.0f'%(n,st.mean(p3[i*len(p3)//3:(i+1)*len(p3)//3]),st.mean(p4[i*len(p4)//3:(i+1)*len(p4)//3])) for i,n in enumerate((10,13,16))))
    return '\n'.join(out)

def stress(reps=2):
    out=['\n方案四 保证性压力测试（每局都必须全部清除）']
    tot=0; fail=0; times=[]
    for mixed,net in ((False,N3),(True,N4_V4)):
        for en,ef in ERR.items():
            for rmode in ('随机','全 1000 m'):
                for layout in ('圆内均匀','边界朝外'):
                    rng=random.Random(hash((mixed,en,rmode,layout))%10**6 if False else abs(hash(en))%97+len(rmode)+len(layout))
                    for n in (10,13,16):
                        for rep in range(reps):
                            src={}
                            for k,ch in enumerate(rng.sample(range(1,21),n)):
                                if layout=='圆内均匀':
                                    a=rng.random()*2*math.pi; rr=1800*math.sqrt(rng.random())
                                    kind='D' if mixed and rng.random()<.65 else 'O'; ang=rng.random()*2*math.pi
                                else:
                                    a=2*math.pi*k/n+rng.uniform(-.05,.05); rr=rng.uniform(1700,1800)
                                    kind='D' if mixed else 'O'; ang=a
                                r=1000. if rmode=='全 1000 m' else rng.uniform(1000,1500)
                                src[ch]=J.source((rr*math.cos(a),rr*math.sin(a)),r,kind,ang)
                            tot+=1
                            try:
                                w=L.solve(W(src,rep,ef),mixed,net,CFG4); times.append(w.time/n)
                            except AssertionError as e:
                                fail+=1; out.append('  失败：%s %s %s N=%d rep=%d —— %s'%('问题四' if mixed else '问题三',en,rmode,n,rep,e))
    out.append('  共 %d 局，未全清 %d 局；每源平均 %.0f s，最大 %.0f s'%(tot,fail,st.mean(times),max(times)))
    return '\n'.join(out)

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--quick',action='store_true'); a=ap.parse_args()
    txt=['方案四配置：问题三 正八边形 974 m（8 点）；问题四 三角格 h=950 m、偏移(475.0, 411.4)、旋转 30°（%d 点，巡回 25.1 km）'%len(N4_V4),
         '  参数：'+'，'.join('%s=%g'%(k,v) for k,v in L.CFG4.items() if k!='final')+'，最终清除顺序=ALNS']
    for tag,seed in (('训练集',1),('验证集 A（未参与调参）',202),('验证集 B（未参与调参）',777)):
        C3,C4=L.cases(seed); txt.append(compare(tag,C3,C4))
    if not a.quick: txt.append(stress())
    s='\n'.join(txt); print(s)
    (HERE/'results'/'方案四_运行输出.txt').write_text(s+'\n',encoding='utf-8')
