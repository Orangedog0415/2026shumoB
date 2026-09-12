# -*- coding: utf-8 -*-
"""本地 mock 模拟器 —— 真值世界（服务端私有，策略不得直接导入使用）。

规则来源：docs/problem/附件1.docx §1-§3 与 附件2.docx §1、§2、§4、§7、§8。
物理与计时口径与 code/baseline/方案一_最终方案验证.py 的 World 保持一致，
差别只在于本模块按微秒整数累计虚拟时间（附件2 §4.1：模拟器内部按微秒累计）。
"""

import hashlib
import math
import random

# ---------------- 题目固定参数（不可调） ----------------
AREA_R = 1800.0            # 目标区域半径 m（附件2 §1.1）
SPEED = 5.0                # 移动速度 m/s（附件2 §4.2）
T_MEASURE = 5.0            # 检测动作耗时 s（附件2 §4.3）
T_SWITCH = 1.0             # 切换频道耗时 s（附件2 §4.3）
T_LOCATE_ONLY = 3.0        # /clear 未发现可清除目标 s（附件2 §4.4）
T_LOCATE_CLEAR = 5.0       # /clear 成功清除 s = 定位3 + 清除2（附件1 §2.3）
NEAR_M = 5.0               # 近距离阈值 m（附件2 §2.4）
CLEAR_M = 20.0             # 清除半径 m（附件2 §2.4）
RECV_MIN = 1000.0          # 有效接收半径下限 m（附件2 §2.1）
RECV_MAX = 1500.0          # 有效接收半径上限 m
SVD_ERR_DEG = 1.0          # 示向度误差界 度（附件2 §2.3）
MAX_VIRTUAL_S = 360000.0   # 虚拟世界限时 s（附件2 §4.5）
N_MIN, N_MAX = 10, 16      # 干扰源数量范围（附件2 §1.3）
CHANNEL_MIN, CHANNEL_MAX = 1, 20


def _h01(*key):
    """由 key 决定的 [0,1) 伪随机数：同一点、同一频道恒定。"""
    return int(hashlib.md5(repr(key).encode()).hexdigest()[:12], 16) / 16 ** 12


# 5 种误差模型，全部满足“同一点、同一频道误差固定”（题目要求，不能靠原地重测降噪）。
# 与 code/experiments/方案一_压力测试.py 的 ERR 表一一对应。
ERROR_MODELS = {
    # 交接版使用的空间相关正弦场
    'orig_sin': lambda p, ch, salt: math.sin(.007 * p[0] + .011 * p[1] + ch * 1.7 + salt),
    # 每点独立均匀分布 [-1,1]
    'iid_uniform': lambda p, ch, salt: 2 * _h01(round(p[0], 3), round(p[1], 3), ch, salt) - 1,
    # 恒 +1 度 / 恒 -1 度（最坏系统误差）
    'const_+1': lambda p, ch, salt: 1.0,
    'const_-1': lambda p, ch, salt: -1.0,
    # 每点独立取 ±1 度（最坏随机误差）
    'iid_pm1': lambda p, ch, salt: 1.0 if _h01(round(p[0], 3), round(p[1], 3), ch, salt) < .5 else -1.0,
    # 无误差，仅用于调试几何，不作为验收场景
    'zero': lambda p, ch, salt: 0.0,
}


def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def generate_sources(n=None, problem=3, seed=None, layout='uniform',
                     radius='rand', p_directional=0.65):
    """生成一局的真实干扰源。

    problem      : 3 = 全部全向；4 = 混合（按 p_directional 出现定向源）
    layout       : uniform  区域内均匀分布
                   boundary 全部贴近边界（1700-1800 m），朝向随机
                   outward  全部贴近边界且定向源一律朝外（问题四最难场景）
    radius       : rand 接收半径 U(1000,1500)；min 全部取下限 1000 m
    """
    rng = random.Random(seed)
    if n is None:
        n = rng.randint(N_MIN, N_MAX)
    if not (N_MIN <= n <= N_MAX):
        raise ValueError('干扰源数量必须在 %d..%d 之间' % (N_MIN, N_MAX))
    mixed = (problem == 4)

    channels = rng.sample(range(CHANNEL_MIN, CHANNEL_MAX + 1), n)
    sources = []
    for k, ch in enumerate(sorted(channels)):
        if layout == 'uniform':
            a = rng.random() * 2 * math.pi
            rr = AREA_R * math.sqrt(rng.random())
        else:
            a = 2 * math.pi * k / n + rng.uniform(-.05, .05)
            rr = rng.uniform(1700.0, AREA_R)
        recv = RECV_MIN if radius == 'min' else rng.uniform(RECV_MIN, RECV_MAX)
        if layout == 'outward' and mixed:
            kind, face = 'D', a                      # 朝外
        elif mixed and rng.random() < p_directional:
            kind, face = 'D', rng.random() * 2 * math.pi
        else:
            kind, face = 'O', 0.0
        sources.append({
            'ch': ch,
            'x': rr * math.cos(a),
            'y': rr * math.sin(a),
            'recv': recv,
            'kind': kind,
            'face_deg': math.degrees(face) % 360.0,
            'cleared': False,
        })
    return sources


class World:
    """真值世界。只有模拟器进程持有；接口层不会把源坐标/数量/半径/朝向/清除状态泄漏出去。"""

    def __init__(self, sources, error_model='orig_sin', salt=0):
        if error_model not in ERROR_MODELS:
            raise ValueError('未知误差模型：%s' % error_model)
        self.sources = {s['ch']: s for s in sources}
        self.error_name = error_model
        self.error = ERROR_MODELS[error_model]
        self.salt = salt
        # 初始状态（附件2 §1.4）
        self.pos = (0.0, 0.0)
        self.channel = 1
        self.us = 0                       # 虚拟时钟，微秒整数
        self.move_us = 0
        self.measure_us = 0
        self.switch_us = 0
        self.clear_us = 0
        self.n_measure = 0
        self.n_clear = 0
        self.n_cleared = 0

    # ---------------- 计时 ----------------
    @property
    def virtual_us(self):
        return self.us

    def _advance(self, seconds):
        d = int(round(seconds * 1_000_000))
        self.us += d
        return d

    def _move_to(self, p):
        d = _dist(self.pos, p)
        us = self._advance(d / SPEED)
        self.move_us += us
        self.pos = (float(p[0]), float(p[1]))
        return d, us

    # ---------------- 物理 ----------------
    def _receivable(self, s, p):
        """返回 (能否收到该频道信号, 距离)。定向源覆盖角 180°，含边界。"""
        d = _dist(p, (s['x'], s['y']))
        if d > s['recv']:
            return False, d
        if s['kind'] == 'D':
            u = math.radians(s['face_deg'])
            # 检测点相对源的方向与源朝向夹角 <= 90°（含边界）
            if (p[0] - s['x']) * math.cos(u) + (p[1] - s['y']) * math.sin(u) < -1e-10:
                return False, d
        return True, d

    def measure(self, p, ch):
        """执行一次合法 /measure，返回 (结果字典, 计时分项)。"""
        dist_m, move_us = self._move_to(p)
        switch = (ch != self.channel)
        sw_us = self._advance(T_SWITCH) if switch else 0
        self.switch_us += sw_us
        self.channel = ch                      # 合法 /measure 后测向机频道更新
        m_us = self._advance(T_MEASURE)
        self.measure_us += m_us
        self.n_measure += 1

        s = self.sources.get(ch)
        out = {'measure_result': 'no_signal'}
        if s is not None and not s['cleared']:
            ok, d = self._receivable(s, self.pos)
            if ok and d <= NEAR_M:
                out = {'measure_result': 'near'}
            elif ok:
                true_deg = math.degrees(math.atan2(s['y'] - self.pos[1], s['x'] - self.pos[0]))
                e = self.error(self.pos, ch, self.salt)
                e = max(-SVD_ERR_DEG, min(SVD_ERR_DEG, e))
                out = {'measure_result': 'direction',
                       'svd_deg': round((true_deg + e) % 360.0, 2) % 360.0}
        timing = {'move_m': dist_m, 'move_us': move_us, 'switch_us': sw_us,
                  'action_us': m_us, 'total_us': move_us + sw_us + m_us}
        return out, timing

    def clear(self, p, ch):
        """执行一次合法 /clear。/clear 不切换测向机频道，也不产生切换耗时。"""
        dist_m, move_us = self._move_to(p)
        s = self.sources.get(ch)
        ok = (s is not None and not s['cleared']
              and _dist(self.pos, (s['x'], s['y'])) <= CLEAR_M)
        a_us = self._advance(T_LOCATE_CLEAR if ok else T_LOCATE_ONLY)
        self.clear_us += a_us
        self.n_clear += 1
        if ok:
            s['cleared'] = True
            self.n_cleared += 1
        out = {'clear_result': 'success' if ok else 'no_target_in_range'}
        timing = {'move_m': dist_m, 'move_us': move_us, 'switch_us': 0,
                  'action_us': a_us, 'total_us': move_us + a_us}
        return out, timing

    # ---------------- 统计（仅模拟器自用） ----------------
    def summary(self):
        n = len(self.sources)
        nd = sum(1 for s in self.sources.values() if s['kind'] == 'D')
        return {
            'source_total': n,
            'source_omni': n - nd,
            'source_directional': nd,
            'cleared': self.n_cleared,
            'remaining': n - self.n_cleared,
            'virtual_time_s': self.us / 1_000_000,
            'measure_count': self.n_measure,
            'clear_count': self.n_clear,
            'move_s': self.move_us / 1_000_000,
            'measure_s': self.measure_us / 1_000_000,
            'switch_s': self.switch_us / 1_000_000,
            'clear_s': self.clear_us / 1_000_000,
            'error_model': self.error_name,
        }

    def truth(self):
        return {'sources': [dict(s) for s in sorted(self.sources.values(), key=lambda s: s['ch'])],
                'error_model': self.error_name, 'salt': self.salt}
