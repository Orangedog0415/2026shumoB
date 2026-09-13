"""图 14a：问题三（方案四）的频道状态机与主循环。

(a) 频道状态机：20 个频道各自独立地在「未定 → 已发现 → 已清除」之间迁移；判定为空有两条
    并列依据——覆盖证书（该频道在 8 个覆盖点上全部无信号）与「已清满 16 个」（题目保证总数 ≤16、
    每频道至多一个源）。结构与问题四相同，只是覆盖点数与判空计数不同。
(b) 主循环：固定巡回（正八边形 8 点，最近邻 + 2-opt 定死顺序）+ 顺路清除（绕行 ≤530 m 且区域
    半径 ≤130 m）+ 覆盖走完后用 ALNS 排序集中清除。与问题四（图 14b）的区别只在调度层。
运行：python 图14a_问题三策略流程与频道状态机.py
输出：figures/图14a_问题三策略流程与频道状态机.pdf / .png
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
F = _m('F', HERE/'_流程图公用.py')
BLUE, ORANGE, GREEN, GREY = F.BLUE, F.ORANGE, F.GREEN, F.GREY

def lab(ax, x, y, s, fs=8.6):
    ax.text(x, y, s, fontsize=fs, color=C['ink2'], ha='center', va='center',
            zorder=8, bbox=dict(boxstyle='round,pad=0.15', fc='white', ec='none'))

if __name__ == '__main__':
    S.use_style()
    fig, axes = plt.subplots(1, 2, figsize=(14.0, 7.4), gridspec_kw=dict(width_ratios=[1, 1.14], wspace=.06))

    F.state_panel(axes[0],
                  '① 覆盖证书：8 个覆盖点上该频道全无信号\n② 已清满 16 个 ⇒ 其余频道必空',
                  '(a) 频道状态机（20 个频道各自独立）')

    # ---- (b) 主循环：固定巡回 + 顺路清除 + ALNS 收尾 ----
    ax = axes[1]; S.blank_axes(ax)
    S.box(ax, (.47, .952), .50, .045, '从原点出发，测向机频道 1', fc=BLUE[0], ec=BLUE[1], fs=9.5)
    S.box(ax, (.47, .845), .70, .045, '已清除满 16 个 ？', fc=GREY[0], ec=GREY[1], fs=9.5)
    S.box(ax, (.47, .737), .70, .045, '固定巡回上还有没测完的覆盖点 ？', fc=GREY[0], ec=GREY[1], fs=9.5)
    S.box(ax, (.47, .607), .80, .085,
          '有没有「可能区域半径 ≤130 m、顺路绕一下就到」的已发现源 ？\n'
          '绕行 = d(当前,中心) + d(中心,下一覆盖点) − d(当前,下一覆盖点) ≤ 530 m',
          fc=BLUE[0], ec=BLUE[1], fs=8.2)
    S.box(ax, (.25, .432), .38, .100, '有：先顺路把它清掉\n（局部清除见左图）\n清完回到上一步重判',
          fc=GREEN[0], ec=GREEN[1], fs=8.6)
    S.box(ax, (.69, .432), .38, .100, '没有：走到巡回上的下一个覆盖点\n测完该点所有未定频道（当前频道优先）\n+ 对已发现的源顺带补测',
          fc=ORANGE[0], ec=ORANGE[1], fs=8.4)
    S.box(ax, (.58, .200), .48, .050, '覆盖走完：ALNS 排序，集中清除剩余源', fc=GREEN[0], ec=GREEN[1], fs=9)
    S.box(ax, (.47, .062), .38, .045, '全部清除，结束', fc=GREEN[0], ec=GREEN[1], fs=9.5)

    S.arrow(ax, (.47, .910), (.47, .888))
    S.arrow(ax, (.47, .803), (.47, .780)); lab(ax, .508, .7915, '否')
    S.arrow(ax, (.47, .695), (.47, .670)); lab(ax, .508, .6825, '有')
    S.arrow(ax, (.41, .562), (.29, .504)); lab(ax, .325, .540, '有')
    S.arrow(ax, (.53, .562), (.65, .504)); lab(ax, .625, .540, '没有')
    # 两个分支都回到循环开头重判
    S.arrow(ax, (.25, .362), (.25, .312)); S.arrow(ax, (.70, .362), (.70, .312))
    S.arrow(ax, (.69, .312), (.025, .312)); S.arrow(ax, (.025, .312), (.025, .845))
    S.arrow(ax, (.025, .845), (.095, .845))
    lab(ax, .175, .285, '两个分支都回到循环开头重判')
    # 覆盖走完 → 集中清除
    S.arrow(ax, (.840, .737), (.928, .737)); S.arrow(ax, (.928, .737), (.928, .200))
    S.arrow(ax, (.928, .200), (.845, .200)); lab(ax, .893, .762, '没有')
    S.arrow(ax, (.58, .158), (.50, .108))
    # 清满 16 个 → 结束
    S.arrow(ax, (.840, .845), (.974, .845)); S.arrow(ax, (.974, .845), (.974, .062))
    S.arrow(ax, (.974, .062), (.685, .062)); lab(ax, .912, .870, '是')
    ax.set_title('(b) 主循环（方案四：固定巡回 + 顺路清除 + ALNS 收尾）', pad=10)

    fig.suptitle('图 14a　问题三策略：频道状态机与主循环', fontsize=13.5, color=C['ink'], y=1.0)
    print('已输出：', S.save(fig, '图14a_问题三策略流程与频道状态机'))
