"""读取 code/experiments/results/绘图数据.json，供图 15~19、22 使用。"""
import json, statistics as st
from pathlib import Path
HERE = Path(__file__).resolve().parent
D = json.load(open(HERE.parent/'experiments'/'results'/'绘图数据.json', encoding='utf-8'))
PER = D['per_case']; TRAJ = D['traj']; STRESS = D['stress']
VER = ['方案一', '方案四', '方案六', '方案七']
SEEDS = ['1', '202', '777']
SEED_NAME = {'1': '训练集', '202': '验证集 A', '777': '验证集 B'}
def t(tag, sd): return [r['t'] for r in PER[tag][sd]]
def mean_t(tag, sd): return st.mean(t(tag, sd))
def share(tag, sd='1'):
    """每源平均的时间分解（秒）。"""
    rows = PER[tag][sd]
    return {k: st.mean(r[k]/r['n'] for r in rows) for k in ('moves', 'detect', 'switch', 'clear')}
