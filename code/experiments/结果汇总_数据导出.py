"""导出《最优结果与数据汇总》文档所需的逐局原始数据。

对同一批案例（L.cases(seed)，问题三/四各 30 局，N=10/13/16 各 10 局）运行：
  问题三：方案一（基线）与方案四（策略 B 采用版）
  问题四：方案一（基线）与方案七（策略 B 采用版）
记录每局的虚拟总时长、每源平均、时间分解（移动/检测/切换/清除）与动作数。
全部为本地仿真，非官方成绩。

运行：python 结果汇总_数据导出.py --seed 1        （每个种子约 1 分钟）
输出：results/结果汇总数据.json（按种子累加）
"""
import argparse, copy, json, statistics as st, importlib.util
from pathlib import Path
HERE = Path(__file__).resolve().parent
def _m(n, f):
    s = importlib.util.spec_from_file_location(n, str(f)); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
R6 = _m('R6', HERE/'方案六_运行.py'); L = R6.L; J = L.J
CFG = L.cfg(**L.CFG4); NET3 = L.NET3(); NET7 = L.NET4_V7()

def stats(w, n, **kw):
    return dict(n=n, total=round(w.time, 3), t=round(w.time/n, 3), moves=round(w.moves, 3),
                detect=w.detect, switch=w.switch, clear=w.cleartime, actions=w.actions, **kw)

def run(problem, version, src, i):
    w = J.World(copy.deepcopy(src), i)
    if problem == 3 and version == '方案一': J.solve(w, False)
    elif problem == 3: L.solve(w, False, NET3, CFG)
    elif version == '方案一': J.solve(w, True)
    else: R6.solve6(w, NET7, CFG)
    return w

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--seed', type=int, default=1); a = ap.parse_args()
    f = HERE/'results'/'结果汇总数据.json'
    out = json.load(open(f, encoding='utf-8')) if f.exists() else {}
    C3, C4 = L.cases(a.seed)
    for problem, C, vers in ((3, C3, ('方案一', '方案四')), (4, C4, ('方案一', '方案七'))):
        for v in vers:
            rows = [stats(run(problem, v, s, i), len(s), case=i) for i, s in enumerate(C)]
            out.setdefault('问题%d' % problem, {}).setdefault(v, {})[str(a.seed)] = rows
            print('seed %d 问题%d %s: %.1f s/源' % (a.seed, problem, v, st.mean(r['t'] for r in rows)), flush=True)
    json.dump(out, open(f, 'w', encoding='utf-8'), ensure_ascii=False)
    print('已写出', f)
