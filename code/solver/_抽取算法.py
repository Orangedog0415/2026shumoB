# -*- coding: utf-8 -*-
"""把已验证的算法逐字节抽进 官方测试_策略B.py，并可随时校验二者是否仍然一致。

    python code\\solver\\_抽取算法.py            # 只校验，不改文件
    python code\\solver\\_抽取算法.py --write     # 用当前算法文件重新生成第 1~3 段

抽取源（都是跑出本地仿真成绩的那套代码，不做任何改写）：
    code/baseline/方案一_最终方案验证.py      几何与保证层
    code/experiments/方案四_实验台.py         覆盖网/路线/局部清除/问题三调度
    code/experiments/方案六_运行.py           问题四调度（联合重规划+服务簇+计数提前停）
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / 'code' / 'solver' / '官方测试_策略B.py'
BEGIN = '# ===== 几何与保证层'
END = '# ===== 第 4 段'

PICK = [
    ('# ===== 几何与保证层（逐字节取自 code/baseline/方案一_最终方案验证.py）=====',
     'code/baseline/方案一_最终方案验证.py',
     ['DELTA', 'EPS', 'dist', 'dot', 'clip', 'disk_outer', 'update', 'wedge', 'diameter',
      'initial_poly', 'centroid', 'contains', 'radius', 'fallback_cells']),
    ('# ===== 覆盖网、路线、局部清除与问题三调度（逐字节取自 code/experiments/方案四_实验台.py）=====',
     'code/experiments/方案四_实验台.py',
     ['DEF', 'CFG4', 'cfg', 'ring', 'lattice', 'NET3', 'NET4_V4', 'NET4_V6_PTS', 'NET4_V6',
      'NET4_V7_PTS', 'NET4_V7', 'tour_nn2opt', 'alns_order', 'Src', 'axis', 'cover_centers',
      'good_geom', 'local_clear', 'solve']),
    ('# ===== 问题四调度：联合重规划 + 服务簇 + 计数提前停（逐字节取自 code/experiments/方案六_运行.py）=====',
     'code/experiments/方案六_运行.py',
     ['service_points', 'solve6']),
]


def blocks(path):
    """把一个模块切成 名字 -> 源码块。只认顶层 def / class / 赋值。"""
    lines = Path(path).read_text(encoding='utf-8').splitlines()
    starts = []
    for i, ln in enumerate(lines):
        m = re.match(r'^(def|class)\s+(\w+)', ln)
        if m:
            starts.append((i, m.group(2)))
            continue
        m = re.match(r'^(\w+)\s*=', ln)
        if m:
            starts.append((i, m.group(1)))
    out = {}
    for k, (i, name) in enumerate(starts):
        j = starts[k + 1][0] if k + 1 < len(starts) else len(lines)
        s = i
        while s - 1 >= 0 and lines[s - 1].startswith('#'):
            s -= 1                                   # 带上紧邻的注释
        while j - 1 > i and (lines[j - 1].strip() == '' or lines[j - 1].startswith('#')):
            j -= 1
        out[name] = '\n'.join(lines[s:j])
    return out


def build():
    parts = []
    for title, rel, names in PICK:
        src = blocks(ROOT / rel)
        parts.append('\n' + title)
        for n in names:
            if n not in src:
                sys.exit('在 %s 里找不到定义：%s' % (rel, n))
            parts.append(src[n] + '\n')
    return '\n'.join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true', help='写回 官方测试_策略B.py 的第 1~3 段')
    a = ap.parse_args()
    text = TARGET.read_text(encoding='utf-8')
    i, j = text.index(BEGIN), text.index(END)
    current, fresh = text[i:j], build().lstrip('\n') + '\n\n'
    if current == fresh:
        print('一致：官方测试_策略B.py 的算法段与已验证的源文件逐字节相同（%d 字符）' % len(fresh))
        return 0
    if not a.write:
        print('不一致！官方测试_策略B.py 的算法段与源文件有差异，加 --write 重新生成。')
        return 1
    TARGET.write_text(text[:i] + fresh + text[j:], encoding='utf-8')
    print('已重新生成算法段（%d 字符）' % len(fresh))
    return 0


if __name__ == '__main__':
    sys.exit(main())
