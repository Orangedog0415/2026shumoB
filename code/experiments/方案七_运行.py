"""【方案七】问题四：在方案六（非规则三角网 + 联合重规划 + 计数提前停 + 服务簇）上再换更小的覆盖网。

相对方案六的唯一改动（编号见 docs/review/方案六_6x实验与方案七.md）：
  6.4  覆盖网从 27 点、17 830 m 的非规则三角网换成 25 点、17 547 m 的 NET4_V7
       （先在 GT06 式的“中心 + 同心环”族里枚举出可行的最小构型，再自由退火缩短巡回）
调度与保证层与方案六完全一致：三角网证书（相交三角形三边 ≤1000 m + 凸包含圆）、频道状态机、
75×3 有限兜底、1.005°/999 m/19.5 m。6.1（GT06 37 点分级环网）、6.2（自适应补测）、6.3（可检测锥选点）
都试过但没有增益，未纳入，记录见同一份文档。
本地仿真，非官方成绩。运行：python 方案七_运行.py（约 6 分钟）；--quick 跳过压力测试。
输出：results/方案七_运行输出.txt
"""
import argparse, math, copy, random, statistics as st, importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent
_r=importlib.util.spec_from_file_location('R6',str(HERE/'方案六_运行.py')); R6=importlib.util.module_from_spec(_r); _r.loader.exec_module(R6)
L=R6.L; J=L.J; dist=L.dist; solve6=R6.solve6; W=R6.W; ERR=R6.ERR
CFG=L.cfg(**L.CFG4); NET7=L.NET4_V7(); NET6=L.NET4_V6(); NET4=L.NET4_V4(); NET3=L.NET3()
def tl(net):
    T=L.tour_nn2opt([tuple(p) for p in net]); return dist((0,0),T[0])+sum(dist(T[i],T[i+1]) for i in range(len(T)-1))
if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--quick',action='store_true'); a=ap.parse_args()
    out=[]; log=lambda s:(out.append(s),print(s,flush=True))
    log('方案七：问题四覆盖网 %d 点、巡回 %.0f m（方案六 %d 点 %.0f m，方案四 %d 点 %.0f m）；问题三沿用方案四（正八边形 974 m）'
        %(len(NET7),tl(NET7),len(NET6),tl(NET6),len(NET4),tl(NET4)))
    log('\n问题四 每源平均定位清除时间 / s')
    log('%-10s %8s %8s %8s'%('','训练集','验证集A','验证集B'))
    R={}
    for tag,net,fn in (('方案四',NET4,lambda w,n:L.solve(w,True,n,CFG)),('方案六',NET6,lambda w,n:solve6(w,n,CFG)),('方案七',NET7,lambda w,n:solve6(w,n,CFG))):
        R[tag]={}
        for sd in (1,202,777):
            R[tag][sd]=[fn(J.World(copy.deepcopy(s),i),net).time/len(s) for i,s in enumerate(L.cases(sd)[1])]
        log('%-10s %8.1f %8.1f %8.1f'%(tag,*[st.mean(R[tag][sd]) for sd in (1,202,777)]))
    log('%-10s %7.1f%% %7.1f%% %7.1f%%'%('七 vs 六',*[100*(st.mean(R['方案七'][sd])/st.mean(R['方案六'][sd])-1) for sd in (1,202,777)]))
    log('%-10s %7.1f%% %7.1f%% %7.1f%%'%('七 vs 四',*[100*(st.mean(R['方案七'][sd])/st.mean(R['方案四'][sd])-1) for sd in (1,202,777)]))
    log('\n按源数分（N=10 / 13 / 16）')
    for sd,tag in ((1,'训练'),(202,'验证A'),(777,'验证B')):
        f=lambda r:'%.0f / %.0f / %.0f'%(st.mean(r[:10]),st.mean(r[10:20]),st.mean(r[20:]))
        log('  %-5s 方案六 %s → 方案七 %s'%(tag,f(R['方案六'][sd]),f(R['方案七'][sd])))
    q3=[st.mean([L.solve(J.World(copy.deepcopy(s),i),False,NET3,CFG).time/len(s) for i,s in enumerate(L.cases(sd)[0])]) for sd in (1,202,777)]
    log('\n问题三（沿用方案四，未改动）：%.1f / %.1f / %.1f s/源'%tuple(q3))
    if not a.quick:
        log('\n保证性压力测试（问题四·方案七）')
        tot=fail=0; times=[]
        for en,ef in ERR.items():
            for rmode in ('随机','全 1000 m'):
                for layout in ('圆内均匀','边界朝外'):
                    rng=random.Random(abs(hash(en))%97+len(rmode)+2*len(layout))
                    for n in (10,13,16):
                        for rep in range(3):
                            src={}
                            for k,ch in enumerate(rng.sample(range(1,21),n)):
                                if layout=='圆内均匀':
                                    aa=rng.random()*2*math.pi; rr=1800*math.sqrt(rng.random()); kind='D' if rng.random()<.65 else 'O'; ang=rng.random()*2*math.pi
                                else:
                                    aa=2*math.pi*k/n+rng.uniform(-.05,.05); rr=rng.uniform(1700,1800); kind='D'; ang=aa
                                r=1000. if rmode=='全 1000 m' else rng.uniform(1000,1500)
                                src[ch]=J.source((rr*math.cos(aa),rr*math.sin(aa)),r,kind,ang)
                            tot+=1
                            try: times.append(solve6(W(src,rep,ef),NET7,CFG).time/n)
                            except AssertionError as e: fail+=1; log('  失败：%s %s %s N=%d rep=%d —— %s'%(en,rmode,layout,n,rep,e))
        log('  共 %d 局，未全清 %d 局；每源平均 %.0f s，最大 %.0f s'%(tot,fail,st.mean(times),max(times)))
    (HERE/'results'/'方案七_运行输出.txt').write_text('\n'.join(out)+'\n',encoding='utf-8')
