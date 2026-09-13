"""图 14a / 14b 共用的「频道状态机」面板与排版常量。

两问的状态机结构完全一样（未定 → 已发现 → 已清除，另有「判定为空」），
只有判空的两条依据里的数字不同：
    问题三：8 个覆盖点的覆盖证书 + 已清满 16 个
    问题四：25 个覆盖点的覆盖证书 + 计数提前停（已清除 + 已发现 = 16）
注意 S.box 的圆角框在 h 之外还有 0.02 的内边距，排版时每个框上下各多占 0.02。
"""
import importlib.util
from pathlib import Path
HERE = Path(__file__).resolve().parent
def _m(n, f):
    s = importlib.util.spec_from_file_location(n, str(f)); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
S = _m('S', HERE/'_绘图样式.py'); C = S.C
BLUE = ('#eaf2fc', C['blue'])
ORANGE = ('#fdece5', C['orange'])
GREEN = ('#e9f3ea', '#3f8a50')
GREY = (C['fill'], C['ink2'])

LADDER = ('局部清除：发现一个源后，按「可能区域还有多大」四选一，能用便宜的档就不用贵的\n'
          '①  半径 ≤19.5 m  →  到区域中心清一次，必成功（区域内任一点到中心 <20 m）\n'
          '②  能被 ≤6 个 20 m 清除圆盖住  →  不再测，就近逐个试清（清空一次只花 3 s）\n'
          '③  区域仍太大  →  换个位置补测一次方位缩小区域，最多 2 次，然后回 ① ②\n'
          '④  仍未清掉  →  沿首条示向线铺 75×3＝225 格兜底网逐格清，保证成功（≤675 s）')

NOTE_NEAR = 'near＝信号太强（距离 ≤5 m）、拿不到示向度；此时不必定位，原地清除即可'


def state_panel(ax, empty_text, title):
    """画频道状态机面板。empty_text 是「判定为空」两条依据的文字（两行）。"""
    S.blank_axes(ax)
    S.box(ax, (.50, .950), .46, .050, '未定 unknown', fc=BLUE[0], ec=BLUE[1])
    S.box(ax, (.24, .735), .42, .090, '已发现 active\n（持有可能区域 P）', fc=ORANGE[0], ec=ORANGE[1], fs=9)
    S.box(ax, (.80, .735), .38, .090, '判定为空\n（不再测这个频道）', fc=GREY[0], ec=GREY[1], fs=9)
    S.box(ax, (.50, .530), .46, .050, '已清除 cleared', fc=GREEN[0], ec=GREEN[1])
    S.box(ax, (.50, .285), .98, .200, LADDER, fc='#f7faf7', ec=GREEN[1], fs=8.4, tc=C['ink'])

    S.arrow(ax, (.40, .908), (.30, .802), color=ORANGE[1])
    ax.text(.150, .876, '测到 direction', fontsize=8.6, color=ORANGE[1], ha='center',
            zorder=8, bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='none'))
    S.arrow(ax, (.60, .908), (.71, .802), color=GREY[1])
    ax.text(.805, .872, empty_text, fontsize=8.1, color=GREY[1], ha='center', linespacing=1.5,
            zorder=8, bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='none'))
    S.arrow(ax, (.52, .908), (.52, .572), color=GREEN[1])
    ax.text(.520, .622, '测到 near\n原地清除', fontsize=8.4, color=GREEN[1], ha='center', linespacing=1.5,
            zorder=8, bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='none'))
    S.arrow(ax, (.26, .692), (.41, .578), color=GREEN[1])
    ax.text(.268, .632, '局部清除 ↓', fontsize=8.6, color=GREEN[1], ha='center',
            zorder=8, bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='none'))
    ax.text(.50, .098, NOTE_NEAR, ha='center', fontsize=8.3, color=C['ink2'])
    ax.set_title(title, pad=10)
