"""【6.1】GT06 的“中心 + 分级同心环”零漏测冗余网（37 点）接入本地仿真，与方案六的非规则三角网对比。

来源：GT06《B 题解题文档》§4.4.3 与 问题四_定向源检测清除策略.py 的 net_p4/solve_redundant_net。
构型：中心 1 点 + 半径 1000 m 的 6 边形环 + 半径 1300 m 的 12 边形环 + 半径 1900 m 的 18 边形环，
      环相位各偏 pi/n；GT06 报告全域最大方位间隔 155.67 度、巡回 21 870 m、粗探 8776.9 s。
本脚本做两件事：
  (a) 用我们的稠密“位置×朝向”复验（360 方位 x 62 半径 x 72 朝向）独立检查该网的零漏测证书；
  (b) 用方案六的求解器 solve6 在同一批案例（seed 1/202/777）上跑该网，和 NET4_V6（27 点、17.8 km）比时间。
运行：python 方案六_6.1_GT06分级环网.py   输出：results/方案六_6.1_输出.txt
"""
import math, copy, statistics as st, importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent
_s=importlib.util.spec_from_file_location('L',str(HERE/'方案四_实验台.py')); L=importlib.util.module_from_spec(_s); _s.loader.exec_module(L)
_r=importlib.util.spec_from_file_location('R6',str(HERE/'方案六_运行.py')); R6=importlib.util.module_from_spec(_r); _r.loader.exec_module(R6)
_c=importlib.util.spec_from_file_location('CN',str(HERE/'方案四_覆盖网优化.py')); CN=importlib.util.module_from_spec(_c); _c.loader.exec_module(CN)
J=L.J; dist=L.dist; CFG=L.cfg(**L.CFG4)

def ring(rho,n,ph=0.): return [(rho*math.cos(2*math.pi*k/n+ph),rho*math.sin(2*math.pi*k/n+ph)) for k in range(n)]
def net_gt06(radii=(1000.,1300.,1900.),counts=(6,12,18)):
    pts=[(0.,0.)]
    for d,n in zip(radii,counts): pts+=ring(d,n,math.pi/n)
    return pts
NET_GT=net_gt06()
NET6=L.NET4_V6()

def tourlen(net):
    T=L.tour_nn2opt([tuple(p) for p in net])
    return dist((0,0),T[0])+sum(dist(T[i],T[i+1]) for i in range(len(T)-1))
def maxgap(net,nang=360,nrad=62):
    """全域最大方位间隔（GT06 式 31）：每个位置取 1000 m 内的观测点，算最大方位间隔。"""
    worst=0.;wp=None
    for i in range(nang):
        a=2*math.pi*i/nang
        for j in range(nrad):
            rr=1800.*j/(nrad-1)
            G=(rr*math.cos(a),rr*math.sin(a))
            b=sorted(math.atan2(p[1]-G[1],p[0]-G[0])%(2*math.pi) for p in net if dist(p,G)<=1000.+1e-9)
            if not b: g=360.
            elif len(b)==1: g=360.
            else: g=math.degrees(max([b[k+1]-b[k] for k in range(len(b)-1)]+[b[0]+2*math.pi-b[-1]]))
            if g>worst: worst,wp=g,G
    return worst,wp

if __name__=='__main__':
    out=[];log=lambda s:(out.append(s),print(s,flush=True))
    log('【6.1】GT06 分级同心环冗余网 vs 方案六非规则三角网\n')
    for tag,net in (('GT06 37 点分级环网',NET_GT),('方案六 27 点非规则三角网',NET6)):
        g,wp=maxgap(net)
        log('%-22s 点数 %2d  巡回 %6.0f m  全域最大方位间隔 %6.2f 度（最差位置 %.0f,%.0f）  稠密复验漏测 %d'
            %(tag,len(net),tourlen(net),g,wp[0],wp[1],CN.missed_pairs([tuple(p) for p in net])))
    log('\n粗探（只走覆盖网、每点扫 20 个频道）的纯代价估计：')
    for tag,net in (('GT06 37 点',NET_GT),('方案六 27 点',NET6)):
        l=tourlen(net); log('  %-12s 巡回 %.0f m → 移动 %.0f s + 检测 %d x 20 x 5 s = %.0f s'%(tag,l,l/5,len(net),l/5+len(net)*20*5))
    log('\n问题四 每源平均定位清除时间 / s（solve6 求解器，只换覆盖网）')
    log('%-16s %8s %8s %8s'%('','训练集','验证A','验证B'))
    res={}
    for tag,net in (('方案六(27点)',NET6),('6.1 GT06(37点)',NET_GT)):
        res[tag]=[]
        for sd in (1,202,777):
            C4=L.cases(sd)[1]
            res[tag].append(st.mean([R6.solve6(J.World(copy.deepcopy(s),i),net,CFG).time/len(s) for i,s in enumerate(C4)]))
        log('%-16s %8.1f %8.1f %8.1f'%(tag,*res[tag]))
    log('%-16s %7.1f%% %7.1f%% %7.1f%%'%('变化',*[100*(res['6.1 GT06(37点)'][k]/res['方案六(27点)'][k]-1) for k in range(3)]))
    (HERE/'results'/'方案六_6.1_输出.txt').write_text('\n'.join(out)+'\n',encoding='utf-8')
