"""【方案八】= 方案七 + 修订大纲的 7.2（最小包围圆圆心）+ 7.3（补测点记账）。

相对方案七的两处改动，都来自《问题三、四算法修订大纲》，编号与 方案七_7.x_大纲修订实验.py 一致：

  7.2 可能区域的代表圆从"顶点均值中心 + 到顶点最大距离"换成**精确最小包围圆**。
      顶点均值不是最小包围圆圆心，会高估外接半径，错失"半径 ≤19.5 m 直接清除"的机会
      （大纲给的算例：顶点 (-19,0)(19,0)(19,1)(18,2)，均值中心覆盖半径 28.26 m，最小包围圆 19.01 m）。
      正确性不变：真源在多边形内 ⇒ 到最小包围圆圆心距离 ≤ 半径 ≤19.5 m < 20 m 的清除半径。
  7.3 局部清除记录**所有**已测点（含无信号），候选里排除。误差场对同一点是确定的，
      重测同一点不可能带来新信息；方案七实测 121 次局部补测里 39 次是重测（32%）。

大纲里的另外两条经性能验收**未采用**（几何/形式可行不等于更快，这也是大纲自己写的验收口径）：
  7.4 问题三七点环（999 m，覆盖上界 999 m < 1000 m，静态巡回 6200.40 m）：单独用时 +1.16%。
  7.5 完整服务代价的滚动路线（max-over-exit 上界式）：问题四 +1.03%。

覆盖网与保证层完全没动：问题三仍是正八边形 974 m，问题四仍是 25 点非规则三角网（三角形证书 +
凸包含圆 + 稠密复验漏测 0），频道状态机、计数提前停、75×3 有限兜底、δ=1.005°/999 m/19.5 m 均不变。
本地仿真，非官方成绩。运行：python 方案八_运行.py（约 6 分钟）；--quick 跳过压力测试。
输出：results/方案八_运行输出.txt
"""
import argparse, copy, math, random, time, importlib.util, statistics as st
from pathlib import Path
HERE = Path(__file__).resolve().parent
def _m(n, f):
    s = importlib.util.spec_from_file_location(n, str(f)); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
X = _m('X', HERE/'方案七_7.x_大纲修订实验.py')
L, J, R6, CFG = X.L, X.J, X.R6, X.CFG
NET3, NET4 = X.NET3_8, X.NET4
SEEDS_DEV = (1, 202, 777)          # 训练 + 两批开发评价数据（都参与过选型，不能再叫验证集）
SEEDS_HOLD = (31337, 90210)        # 全新留出集：本轮之前从未跑过，不参与任何选择

def apply_patch():
    """方案八 = 在实验台之上打两个补丁；历史脚本不受影响，仍可复现旧结果。"""
    L.Src.RC = X.RC_mec
    L.local_clear = X.local_clear_v2

def run_case(case, salt, problem, W=None):
    w = (W or J.World)(copy.deepcopy(case), salt)
    if problem == 3: L.solve(w, False, NET3, CFG)
    else: R6.solve6(w, NET4, CFG)
    return w

def block(seeds, tag, out):
    for problem in (3, 4):
        rows = []
        for sd in seeds:
            cases = L.cases(sd)[0 if problem == 3 else 1]
            for i, s in enumerate(cases):
                w = run_case(s, i, problem)
                rows.append((w.time/len(s), w.actions, len(s)))
        t = sorted(r[0] for r in rows)
        byN = {n: st.mean(r[0] for r in rows if r[2] == n) for n in sorted({r[2] for r in rows})}
        out('  %s 问题%s：%d 局  每源平均 %.1f s  P90 %.1f s  最大 %.1f s  动作 %.0f  按源数 %s'
            % (tag, '三' if problem == 3 else '四', len(rows), st.mean(t),
               t[int(.9*(len(t)-1))], t[-1], st.mean(r[1] for r in rows),
               ' / '.join('%.0f' % byN[n] for n in sorted(byN))))

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--quick', action='store_true'); a = ap.parse_args()
    out_lines = []; log = lambda s: (out_lines.append(s), print(s, flush=True))
    t0 = time.time()
    log('方案八 = 方案七 + 7.2 最小包围圆 + 7.3 补测点记账（覆盖网与保证层未改动）')

    log('\n[对照] 方案七 基线')
    block(SEEDS_DEV, '开发集(1/202/777)', log)
    apply_patch()
    log('\n[方案八]')
    block(SEEDS_DEV, '开发集(1/202/777)', log)
    log('\n[方案八] 全新留出集（从未参与任何选择）')
    block(SEEDS_HOLD, '留出集(31337/90210)', log)

    log('\n[7.2 的直接效果] 可能区域的代表圆')
    L.Src.RC = X.RC_ORIG
    r_old = []; 
    L.Src.RC = X.RC_mec
    cnt = dict(n=0, better=0, unlock=0)
    orig_lc = L.local_clear
    def probe_lc(world, ch, src, C):
        c0 = J.centroid(src.P); r0 = J.radius(src.P, c0); _, r1 = X.min_circle(src.P)
        cnt['n'] += 1
        if r1 < r0 - 1e-9: cnt['better'] += 1
        if r0 > 19.5 >= r1: cnt['unlock'] += 1
        orig_lc(world, ch, src, C)
    L.local_clear = probe_lc
    for i, s in enumerate(L.cases(1)[1]): R6.solve6(J.World(copy.deepcopy(s), i), NET4, CFG)
    L.local_clear = orig_lc
    log('  训练集 30 局里进入局部清除 %d 次：最小包围圆更小 %d 次（%.0f%%），'
        '其中 %d 次把"不可直接清除"变成"可直接清除"（%.1f%%）'
        % (cnt['n'], cnt['better'], 100*cnt['better']/cnt['n'], cnt['unlock'], 100*cnt['unlock']/cnt['n']))

    if not a.quick:
        log('\n[保证性压力测试] 问题四，180 局（与方案六/七同一批）')
        tot = fail = 0; times = []
        for en, ef in R6.ERR.items():
            for rmode in ('随机', '全 1000 m'):
                for layout in ('圆内均匀', '边界朝外'):
                    rng = random.Random(abs(hash(en)) % 97 + len(rmode) + 2*len(layout))
                    for n in (10, 13, 16):
                        for rep in range(3):
                            src = {}
                            for k, ch in enumerate(rng.sample(range(1, 21), n)):
                                if layout == '圆内均匀':
                                    aa = rng.random()*2*math.pi; rr = 1800*math.sqrt(rng.random())
                                    kind = 'D' if rng.random() < .65 else 'O'; ang = rng.random()*2*math.pi
                                else:
                                    aa = 2*math.pi*k/n + rng.uniform(-.05, .05); rr = rng.uniform(1700, 1800)
                                    kind = 'D'; ang = aa
                                r = 1000. if rmode == '全 1000 m' else rng.uniform(1000, 1500)
                                src[ch] = J.source((rr*math.cos(aa), rr*math.sin(aa)), r, kind, ang)
                            tot += 1
                            try: times.append(R6.solve6(R6.W(src, rep, ef), NET4, CFG).time/n)
                            except AssertionError as e:
                                fail += 1; log('    失败：%s %s %s N=%d rep=%d —— %s' % (en, rmode, layout, n, rep, e))
        log('  共 %d 局，未全清 %d 局；每源平均 %.0f s，最大 %.0f s' % (tot, fail, st.mean(times), max(times)))
    log('\n程序运行时间 %.1f 分钟（本地仿真，与机器狗的虚拟耗时无关）' % ((time.time()-t0)/60))
    (HERE/'results'/'方案八_运行输出.txt').write_text('\n'.join(out_lines)+'\n', encoding='utf-8')
