"""图 4：半平面求交的退化分支——空集、点、线段、无界与数值不确定。

Sutherland–Hodgman 逐条裁剪之后，结果不一定是"正常的多边形"。实现必须把下面几种情形分开处理，
否则直径、外接圆、清除点这些下游计算都会出错：
  空集      两条楔形没有公共部分 → 观测互相矛盾，转异常分支（现场表现为误差超界或频道串扰）
  单点 / 线段  退化成零面积集合，直径仍然良定义（线段长度），但"顶点枚举求直径"必须允许 1~2 个顶点
  无界      只有一次观测时楔形本身无界，所以实现里一律先与"目标圆盘 + 到检测点 ≤1500 m"求交再往下走
  数值不确定  顶点间距离小于容差时，判据落在边界上；统一用 EPS=1e-7 的一侧闭包，并让下游用保守半径
运行：python 图04_退化分支判定.py   输出：figures/图04_退化分支判定.pdf / .png
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
BLUE, ORANGE, GREEN, GREY, RED = ('#eaf2fc', C['blue']), ('#fdece5', C['orange']), ('#e9f3ea', '#3f8a50'), (S.C['fill'], C['ink2']), ('#fdeaea', C['red'])

if __name__ == '__main__':
    S.use_style()
    fig, ax = plt.subplots(figsize=(11.6, 6.8)); S.blank_axes(ax)
    S.box(ax, (.5, .94), .46, .07, '逐条半平面裁剪后的结果 $P$', fc=BLUE[0], ec=BLUE[1], fs=10)
    S.box(ax, (.5, .80), .30, .06, '顶点数 = 0 ？', fc=GREY[0], ec=GREY[1], fs=9.5)
    S.box(ax, (.5, .64), .30, .06, '顶点数 ≤ 2 ？', fc=GREY[0], ec=GREY[1], fs=9.5)
    S.box(ax, (.5, .48), .34, .06, '外接半径 < 数值容差 ？', fc=GREY[0], ec=GREY[1], fs=9.5)
    S.box(ax, (.5, .26), .40, .09, '正常多边形\n顶点枚举 + 旋转卡壳求直径', fc=GREEN[0], ec=GREEN[1], fs=9.5)

    S.box(ax, (.87, .80), .24, .10, '空集：观测矛盾\n转异常分支', fc=RED[0], ec=RED[1], fs=9)
    S.box(ax, (.87, .64), .24, .10, '点 / 线段\n直径 = 两点距离', fc=ORANGE[0], ec=ORANGE[1], fs=9)
    S.box(ax, (.87, .48), .24, .11, '数值不确定\n按保守半径处理\n（直接进入清除流程）', fc=ORANGE[0], ec=ORANGE[1], fs=9)
    S.box(ax, (.13, .64), .24, .13, '无界情形\n只有一次观测时楔形本身无界\n实现里先与目标圆盘和\n"到检测点 ≤1500 m"求交', fc=BLUE[0], ec=BLUE[1], fs=8.6)

    S.arrow(ax, (.5, .905), (.5, .832))
    for y0, y1 in ((.80, .672), (.64, .512), (.48, .308)):
        S.arrow(ax, (.5, y0-.032), (.5, y1)); ax.text(.525, y1+.038, '否', fontsize=9, color=C['ink2'])
    for y in (.80, .64, .48):
        S.arrow(ax, (.66, y), (.75, y)); ax.text(.70, y+.022, '是', fontsize=9, color=C['ink2'])
    S.arrow(ax, (.35, .935), (.25, .71), color=C['ink2'])
    ax.set_title('图 4　定位区域求交的退化分支与处理方式', fontsize=13.5, pad=14)
    ax.text(.5, .055, '这些分支不是"防御性代码"：题目允许示向度取整到 0.01°，'
                      '两次观测几乎共线时定位区域会退化成线段，\n'
                      '而误差超界或频道串扰时会直接出现空集——实现必须给出确定的动作，不能靠异常抛出。',
            ha='center', fontsize=9.2, color=C['ink2'], linespacing=1.7)
    print('已输出：', S.save(fig, '图04_退化分支判定'))
