"""读取 code/experiments/results/敏感性分析.json，供图 28~31 使用。"""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
D = json.load(open(HERE.parent/'experiments'/'results'/'敏感性分析.json', encoding='utf-8'))
S1, S2, S3, S4 = D['S1'], D['S2'], D['S3'], D['S4']
