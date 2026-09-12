"""图 14：问题四（方案七）的频道状态机与主循环。

左边是频道状态机：20 个频道各自独立地在"未定 → 已发现 → 已清除"之间迁移，
其中"未定 → 判定为空"有两条**并列**的依据：覆盖证书（该频道在覆盖网所有点上都测过且全无信号）
与计数提前停（已清除 + 已发现达到 16，题目保证总数 ≤16 且每频道至多一个源）。
右边是主循环：不再用"固定巡回 + 绕行阈值 x"，而是每一步把"还有未定频道的覆盖点"和"可以去清的源"
放在一起重排路线，只执行排在最前的那个节点，然后重排。
运行：python 图14_策略流程与频道状态机.py   输出：figures/图14_策略流程与频道状态机.pdf / .png
"""
import importlib.util
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib import font_manager
HERE = Path(__file__).resolve().parent
try: font_manager.fontManager.addfont('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
except Exception: pass
def _m(n, f):
    s = importlib.util.spec_from_file_location(n, str(f)); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
S = _m('S', HERE/'_绘图样式.py'); C = S.C
BLUE, ORANGE, GREEN, GREY = ('#eaf2fc', C['blue']), ('#fdece5', C['orange']), ('#e9f3ea', '#3f8a50'), (S.C['fill'], C['ink2'])

if __name__ == '__main__':
    S.use_style()
    fig, axes = plt.subplots(1, 2, figsize=(13.6, 6.2), gridspec_kw=dict(width_ratios=[1, 1.18], wspace=.06))

    # ---- (a) 频道状态机 ----
    ax = axes[0]; S.blank_axes(ax)
    unk = S.box(ax, (.50, .88), .46, .085, '未定 unknown', fc=BLUE[0], ec=BLUE[1])
    act = S.box(ax, (.24, .53), .42, .11, '已发现 active\n（持有可能区域）', fc=ORANGE[0], ec=ORANGE[1], fs=9)
    emp = S.box(ax, (.78, .53), .40, .11, '判定为空\n（不再测这个频道）', fc=GREY[0], ec=GREY[1], fs=9)
    cle = S.box(ax, (.50, .17), .46, .085, '已清除 cleared', fc=GREEN[0], ec=GREEN[1])
    S.arrow(ax, (.38, .845), (.28, .59), color=ORANGE[1])
    ax.text(.255, .715, '测到 direction', fontsize=8.8, color=ORANGE[1], ha='center',
            bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='none'))
    S.arrow(ax, (.62, .845), (.74, .59), color=GREY[1])
    ax.text(.775, .725, '① 覆盖证书：网上每点都无信号\n② 计数提前停：已清+已发 = 16',
            fontsize=8.4, color=GREY[1], ha='center', linespacing=1.5,
            bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='none'))
    S.arrow(ax, (.545, .835), (.545, .215), color=GREEN[1])
    ax.text(.545, .345, '测到 near（≤5 m）\n原地清除', fontsize=8.8, color=GREEN[1], ha='center', linespacing=1.5,
            bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='none'))
    S.arrow(ax, (.26, .475), (.44, .215), color=GREEN[1])
    ax.text(.255, .32, '局部清除：\n半径 ≤19.5 m → 到中心清\n≤6 格 → 逐格清\n否则补测 ≤2 次 / 75×3 兜底',
            fontsize=8.4, color=GREEN[1], ha='center', linespacing=1.5,
            bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='none'))
    ax.set_title('(a) 频道状态机（20 个频道各自独立）', pad=10)
    ax.text(.5, .035, '两条判空依据并列，缺一不可：证书管"网走完了"，计数停管"源已找齐"',
            ha='center', fontsize=8.8, color=C['ink2'])

    # ---- (b) 主循环 ----
    ax = axes[1]; S.blank_axes(ax)
    W = .78
    n0 = S.box(ax, (.50, .945), .50, .07, '从原点出发，测向机频道 1', fc=BLUE[0], ec=BLUE[1], fs=9.5)
    n1 = S.box(ax, (.50, .848), W, .07, '已清除 + 已发现 ≥ 16 ？', fc=GREY[0], ec=GREY[1], fs=9.5)
    n2 = S.box(ax, (.50, .672), W, .115,
               '联合重规划：把"还有未定频道的覆盖点"与"可清的源"放在一起，\n'
               '从当前位置排一条最近邻 + 2-opt 开放路线（源用服务簇表示）', fc=BLUE[0], ec=BLUE[1], fs=8.8)
    n3 = S.box(ax, (.50, .565), .50, .07, '执行排在最前的那个节点', fc='white', ec=C['edge'], fs=9.5)
    n4 = S.box(ax, (.26, .400), .42, .135, '覆盖点\n测完该点所有未定频道\n（当前频道优先）+ 顺带补测',
               fc=ORANGE[0], ec=ORANGE[1], fs=8.8)
    n5 = S.box(ax, (.74, .400), .42, .135, '可清的源\n按服务簇就近清除\n（局部清除见左图）',
               fc=GREEN[0], ec=GREEN[1], fs=8.8)
    n6 = S.box(ax, (.74, .180), .42, .085, '停止覆盖，集中清除剩余源', fc=GREEN[0], ec=GREEN[1], fs=9)
    n7 = S.box(ax, (.50, .050), .40, .07, '全部清除，结束', fc=GREEN[0], ec=GREEN[1], fs=9.5)
    S.arrow(ax, (.50, .906), (.50, .888))
    S.arrow(ax, (.50, .810), (.50, .734)); ax.text(.532, .772, '否', fontsize=8.8, color=C['ink2'],
            bbox=dict(boxstyle='round,pad=0.15', fc='white', ec='none'))
    S.arrow(ax, (.90, .848), (.965, .848)); S.arrow(ax, (.965, .848), (.965, .200))
    S.arrow(ax, (.965, .200), (.952, .185))
    ax.text(.925, .872, '是', fontsize=8.8, color=C['ink2'])
    S.arrow(ax, (.50, .612), (.50, .602))
    S.arrow(ax, (.44, .530), (.30, .470))
    S.arrow(ax, (.56, .530), (.70, .470))
    S.arrow(ax, (.05, .332), (.05, .700)); S.arrow(ax, (.26, .332), (.05, .332)); S.arrow(ax, (.05, .700), (.10, .700))
    ax.text(.028, .52, '重排', fontsize=8.8, color=C['ink2'], rotation=90, va='center', ha='center',
            bbox=dict(boxstyle='round,pad=0.15', fc='white', ec='none'))
    S.arrow(ax, (.74, .330), (.74, .228))
    S.arrow(ax, (.74, .136), (.60, .086))
    ax.set_title('(b) 主循环（方案七 = 方案六的调度 + 25 点覆盖网）', pad=10)

    fig.suptitle('图 14　问题四策略的两张结构图：频道状态机与主循环', fontsize=13.5, color=C['ink'], y=1.0)
    print('已输出：', S.save(fig, '图14_策略流程与频道状态机'))
