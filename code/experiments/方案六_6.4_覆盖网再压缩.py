"""【6.4】覆盖网再压缩：在“环族枚举 + 退火”里把每个覆盖点的真实边际代价放回目标，27 点降到 25 点。

动机：6.1 把 GT06 的 37 点分级环网接进仿真后慢 15.5%，说明问题四的粗探代价几乎线性于
      “覆盖点数 x 每点检测时间 + 巡回长度 / 5”。而 5.2 退火用的每点权重 42 s（7 个空频道 x 6 s）偏小：
      实测一次覆盖扫描平均仍有 10 个以上未定频道，每点边际代价接近 60~80 s。
      另一方面 5.2 是从 h=900 规则格网出发的，退火困在 27 点的局部极小（本脚本第一段复现了这一点）。
做法：
  (a) 借 GT06 的“中心 + 同心环”参数化，但把零漏测判据换成我们更强的三角网证书，枚举 (n2,R2,相位,n3,R3)
      得到可行环构型，最少 25 点（中心 + 12@950 + 12@1880，巡回 18 057 m）；
  (b) 以该 25 点构型为起点再退火（自由移动顶点），得到 25 点、巡回 17 547 m 的网 —— 点数和巡回都优于方案六。
证书与 5.2 一致：Delaunay 三角剖分，conv(Q) 包住 1800 m 圆盘，与圆盘相交的三角形三边 <=1000 m；
另报告 GT06 式 (31) 的“全域最大方位间隔”与稠密“位置 x 朝向”复验作为独立交叉检查。
需要 numpy、scipy。运行：python 方案六_6.4_覆盖网再压缩.py（约 15 分钟）
输出：results/方案六_6.4_输出.txt、results/方案六_6.4_新网.json
"""
import math, json, copy, statistics as st, importlib.util
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
_r=importlib.util.spec_from_file_location('R6',str(HERE/'方案六_运行.py')); R6=importlib.util.module_from_spec(_r); _r.loader.exec_module(R6)
L=R6.L; J=L.J; dist=L.dist; NET6=L.NET4_V6()
_f=importlib.util.spec_from_file_location('F',str(HERE/'方案五_5.2_非规则三角网优化.py')); F=importlib.util.module_from_spec(_f); _f.loader.exec_module(F)
setattr(F,'_L',L)
_c=importlib.util.spec_from_file_location('CN',str(HERE/'方案四_覆盖网优化.py')); CN=importlib.util.module_from_spec(_c); _c.loader.exec_module(CN)
_g=importlib.util.spec_from_file_location('G1',str(HERE/'方案六_6.1_GT06分级环网.py')); G1=importlib.util.module_from_spec(_g); _g.loader.exec_module(G1)

def ring(rho,n,ph=0.): return [(rho*math.cos(2*math.pi*k/n+ph),rho*math.sin(2*math.pi*k/n+ph)) for k in range(n)]
def tl(net):
    T=L.tour_nn2opt([tuple(p) for p in net]); return dist((0,0),T[0])+sum(dist(T[i],T[i+1]) for i in range(len(T)-1))
def ring_search():
    """环族枚举：外环需同时满足 2R3 sin(pi/n3)<=1000（边长）与 R3 cos(pi/n3)>=1800（凸包含圆）。"""
    out=[]
    for n3 in (12,13,14):
        for R3 in range(1860,1960,20):
            if 2*R3*math.sin(math.pi/n3)>1000 or R3*math.cos(math.pi/n3)<1800: continue
            for n2 in range(6,13):
                for R2 in range(700,1500,50):
                    for ph2 in (0.,math.pi/n2):
                        Q=[(0.,0.)]+ring(R2,n2,ph2)+ring(R3,n3,math.pi/n3)
                        if F.feasible(Q)[0]: out.append((len(Q),tl(Q),(n2,R2,ph2,n3,R3),Q))
    out.sort(key=lambda b:(b[0],b[1])); return out
def report(tag,Q,log):
    ok,tri=F.feasible(Q); P=np.array(Q)
    maxe=max(max(math.dist(tuple(P[i]),tuple(P[j])) for i,j in ((s[0],s[1]),(s[1],s[2]),(s[2],s[0])))
             for s in tri.simplices if F.tri_hits_disk([tuple(P[k]) for k in s]))
    g,_=G1.maxgap(Q)
    log('%-18s %2d 点  巡回 %6.0f m  解析证书 %s（相交三角形最长边 %.1f m）  最大方位间隔 %6.2f 度  稠密复验漏测 %d'
        %(tag,len(Q),tl(Q),ok,maxe,g,CN.missed_pairs(Q)))
def q4(Q,seeds=(1,202,777)):
    CFG=L.cfg(**L.CFG4)
    return [st.mean([R6.solve6(J.World(copy.deepcopy(s),i),Q,CFG).time/len(s)
                     for i,s in enumerate(L.cases(sd)[1])]) for sd in seeds]

if __name__=='__main__':
    out=[];log=lambda s:(out.append(s),print(s,flush=True))
    log('【6.4】覆盖网再压缩\n(1) 直接从方案六的 27 点网出发加大每点权重再退火 —— 复现“困在局部极小”')
    for w in (70.,100.):
        f,l,Q=F.anneal([tuple(p) for p in NET6],iters=2200,seed=0,per_point=w)
        log('    每点权重 %.0f s：%d 点，巡回 %.0f m（起点 27 点 %.0f m，没有变化）'%(w,len(Q),l,tl(NET6)))
    log('\n(2) 环族枚举（GT06 的“中心 + 同心环”参数化 + 我们的三角网证书）')
    cand=ring_search()
    log('    可行构型 %d 个，按点数与巡回排序的前 4 个：'%len(cand))
    for n,l,cfgp,_ in cand[:4]:
        log('      %2d 点 巡回 %6.0f m  中心 + %d@%.0f(相位 %.2f) + %d@%d'%(n,l,cfgp[0],cfgp[1],cfgp[2],cfgp[3],cfgp[4]))
    A=cand[0][3]
    log('\n(3) 以最小环构型为起点自由退火')
    best=None
    for w in (60.,80.,300.):
        for seed in range(4):
            f,l,Q=F.anneal(A,iters=2500,seed=seed,per_point=w)
            if best is None or (len(Q),l)<best[0]: best=((len(Q),l),Q)
    Q7=[(round(x,1),round(y,1)) for x,y in best[1]]
    log('    最优：%d 点，巡回 %.0f m（坐标取到 0.1 m 后仍需复验）'%(len(Q7),tl(Q7)))
    log('    注：退火有随机性，单次运行未必复现仓库里的 NET4_V7（25 点、17 547 m）。')
    log('')
    for tag,Q in (('方案六 27 点',[tuple(p) for p in NET6]),('环族最小 25 点',[tuple(p) for p in A]),('6.4 退火后 25 点',Q7)):
        report(tag,Q,log)
    log('\n问题四 每源平均定位清除时间 / s（solve6 求解器，只换覆盖网）')
    log('%-18s %8s %8s %8s'%('','训练集','验证A','验证B'))
    base=None
    for tag,Q in (('方案六 27 点',[tuple(p) for p in NET6]),('环族最小 25 点',[tuple(p) for p in A]),('6.4 退火后 25 点',Q7)):
        r=q4(Q)
        if base is None: base=r
        log('%-18s %8.1f %8.1f %8.1f   (%+.1f%% / %+.1f%% / %+.1f%%)'%(tag,*r,*[100*(r[k]/base[k]-1) for k in range(3)]))
    json.dump({'ring25':[list(p) for p in A],'net25':[list(p) for p in Q7]},open(HERE/'results'/'方案六_6.4_新网.json','w'))
    (HERE/'results'/'方案六_6.4_输出.txt').write_text('\n'.join(out)+'\n',encoding='utf-8')
