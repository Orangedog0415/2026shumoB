"""【方案三】按交接材料第九节采用的参数运行方案三（策略B），并与【方案一】在同一批案例上对比。

  问题三：正八边形 8 点（半径 974 m，不设中心）；问题四：h=990 m 三角格网 27 点
  顺路清除：绕行 ≤ x 且区域半径 ≤ r_ok；覆盖点顺带补测开启；覆盖完成后按最近顺序集中清除
方案三主循环在 方案三_参数扫描.py 的 solve_x()；局部清除、格网、巡回顺序复用 方案二_调度改进原型.py。
全部为本地仿真（交接脚本 World 与误差模型），非官方成绩。

运行：python 方案三_运行.py            （约 1 分钟，默认 x=600 m、r_ok=150 m）
      python 方案三_运行.py --x 300    （改顺路阈值）
输出同时写到 results/方案三_运行输出.txt
"""
import argparse, copy, random, statistics as st, importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('S3',str(HERE/'方案三_参数扫描.py')); S3=importlib.util.module_from_spec(spec); spec.loader.exec_module(S3)
P=S3.P; J=S3.J

NET_Q3=S3.ring(8,974)     # 问题三覆盖网
NET_Q4=P.net990()         # 问题四覆盖网

def main():
    ap=argparse.ArgumentParser(description='运行方案三并与方案一对比（本地仿真）')
    ap.add_argument('--x',type=float,default=600,help='顺路清除绕行阈值 m（默认 600）')
    ap.add_argument('--r_ok',type=float,default=150,help='可确认区域半径 m（默认 150）')
    ap.add_argument('--cases',type=int,default=10,help='每个 N 的局数（默认 10）')
    a=ap.parse_args()
    rng=random.Random(1)
    C3=[P.gen(rng,n,False) for n in (10,13,16) for _ in range(a.cases)]
    C4=[P.gen(rng,n,True) for n in (10,13,16) for _ in range(a.cases)]
    lines=[f'方案三参数：x={a.x:g} m，r_ok={a.r_ok:g} m；问题三 正八边形 974 m（8 点），问题四 h=990 m 格网（{len(NET_Q4)} 点）；每个 N {a.cases} 局']
    for label,C,mixed,NET in (('问题三',C3,False,NET_Q3),('问题四',C4,True,NET_Q4)):
        r1={10:[],13:[],16:[]}; r3={10:[],13:[],16:[]}; t1=[]; t3=[]; mv3=[]
        for i,s in enumerate(C):
            w1=J.World(copy.deepcopy(s),i); J.solve(w1,mixed)
            w3=S3.solve_x(J.World(copy.deepcopy(s),i),mixed,NET,x=a.x,r_ok=a.r_ok)   # 内部断言全部清除
            n=len(s); r1[n].append(w1.time/n); r3[n].append(w3.time/n); t1.append(w1.time); t3.append(w3.time); mv3.append(w3.moves/w3.time)
        all1=[v for l in r1.values() for v in l]; all3=[v for l in r3.values() for v in l]
        wins=sum(y<x for x,y in zip(all1,all3))
        lines.append(f'\n{label}（{len(C)} 局，全部清除）')
        lines.append(f'  每源平均：方案一 {st.mean(all1):.0f} s → 方案三 {st.mean(all3):.0f} s（{100*(st.mean(all3)/st.mean(all1)-1):+.1f}%），方案三更快 {wins}/{len(C)} 局')
        lines.append(f'  单局平均：方案一 {st.mean(t1):.0f} s → 方案三 {st.mean(t3):.0f} s；方案三移动占比 {100*st.mean(mv3):.0f}%')
        lines.append('  按 N：'+'；'.join(f'N={n} {st.mean(r1[n]):.0f}→{st.mean(r3[n]):.0f}' for n in (10,13,16)))
    out='\n'.join(lines); print(out)
    (HERE/'results'/'方案三_运行输出.txt').write_text(out+'\n',encoding='utf-8')

if __name__=='__main__':
    main()
