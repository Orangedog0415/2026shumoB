"""图 14b：问题四（方案七）的频道状态机与主循环。

(a) 频道状态机：结构与问题三（图 14a）完全相同，只是判空的两条依据换成 25 点覆盖网的覆盖证书
    与计数提前停（已清除 + 已发现 = 16 ⇒ 其余频道必空）。
(b) 主循环：不用固定巡回与绕行阈值 x，改为每一步把「还有未定频道的覆盖点」和「可以去清的源」
    放在一起重排路线（源用服务簇表示），只执行排在最前的那个节点，然后重排。
运行：python 图14b_问题四策略流程与频道状态机.py
输出：figures/图14b_问题四策略流程与频道状态机.pdf / .png
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
                  '① 覆盖证书：25 个覆盖点上该频道全无信号\n② 计数提前停：已清除 + 已发现 = 16',
                  '(a) 频道状态机（20 个频道各自独立）')

    # ---- (b) 主循环：联合重规划 + 服务簇 + 计数提前停 ----
    ax = axes[1]; S.blank_axes(ax)
    S.box(ax, (.47, .960), .50, .045, '从原点出发，测向机频道 1', fc=BLUE[0], ec=BLUE[1], fs=9.5)
    S.box(ax, (.47, .850), .70, .045, '已清除满 16 个 ？', fc=GREY[0], ec=GREY[1], fs=9.5)
    S.box(ax, (.47, .750), .80, .045, '还有未定频道的覆盖点，且「已清除 + 已发现」< 16 ？', fc=GREY[0], ec=GREY[1], fs=9.2)
    S.box(ax, (.25, .620), .40, .075, '候选节点 = 未测完的覆盖点\n＋ 区域半径 ≤130 m 的已发现源',
          fc=BLUE[0], ec=BLUE[1], fs=8.5)
    S.box(ax, (.70, .620), .36, .075, '候选节点 = 全部待清的源\n（计数提前停 / 覆盖已走完）',
          fc=BLUE[0], ec=BLUE[1], fs=8.5)
    S.box(ax, (.47, .465), .82, .105,
          '联合重规划：从当前位置把候选节点排成一条最近邻 + 2-opt 开放路线\n'
          '（每个源用服务簇表示：≤6 个 20 m 清除圆中心，取离当前位置最近的那个）\n'
          '→ 只执行排在最前的那个节点，然后回到开头重排', fc=ORANGE[0], ec=ORANGE[1], fs=8.2)
    S.box(ax, (.25, .305), .40, .095, '节点是覆盖点：测完该点所有未定频道\n（当前频道优先）+ 对已发现的源顺带补测',
          fc=ORANGE[0], ec=ORANGE[1], fs=8.4)
    S.box(ax, (.70, .305), .36, .095, '节点是源：局部清除\n（见左图的四档阶梯）',
          fc=GREEN[0], ec=GREEN[1], fs=8.6)
    S.box(ax, (.47, .075), .38, .045, '全部清除，结束', fc=GREEN[0], ec=GREEN[1], fs=9.5)

    S.arrow(ax, (.47, .918), (.47, .893))
    S.arrow(ax, (.47, .808), (.47, .793)); lab(ax, .508, .8005, '否')
    S.arrow(ax, (.41, .728), (.29, .680)); lab(ax, .318, .708, '是')
    S.arrow(ax, (.53, .728), (.66, .680)); lab(ax, .638, .708, '否')
    S.arrow(ax, (.25, .563), (.33, .540)); S.arrow(ax, (.70, .563), (.60, .540))
    S.arrow(ax, (.41, .393), (.29, .372)); S.arrow(ax, (.53, .393), (.65, .372))
    # 两个分支都回到循环开头重排
    S.arrow(ax, (.25, .238), (.25, .190)); S.arrow(ax, (.70, .238), (.70, .190))
    S.arrow(ax, (.70, .190), (.025, .190)); S.arrow(ax, (.025, .190), (.025, .850))
    S.arrow(ax, (.025, .850), (.095, .850))
    lab(ax, .175, .163, '每执行一个节点就回到开头重排')
    # 候选为空（覆盖走完且没有待清源）→ 结束
    S.arrow(ax, (.893, .465), (.945, .465)); S.arrow(ax, (.945, .465), (.945, .075))
    S.arrow(ax, (.945, .075), (.665, .075)); lab(ax, .905, .430, '候选为空', fs=8.2)
    # 清满 16 个 → 结束
    S.arrow(ax, (.840, .850), (.980, .850)); S.arrow(ax, (.980, .850), (.980, .098))
    S.arrow(ax, (.980, .098), (.665, .098)); lab(ax, .918, .875, '是')
    ax.set_title('(b) 主循环（方案七：联合重规划 + 服务簇 + 计数提前停）', pad=10)

    fig.suptitle('图 14b　问题四策略：频道状态机与主循环', fontsize=13.5, color=C['ink'], y=1.0)
    print('已输出：', S.save(fig, '图14b_问题四策略流程与频道状态机'))
