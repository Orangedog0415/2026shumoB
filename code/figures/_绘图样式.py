"""论文插图的统一样式：配色、字体、坐标轴与常用图元。所有 图xx_*.py 都从这里取样式。

配色只用三个分类色（蓝/橙/红），其余一律走中性灰阶——分类色少而固定，读者一眼就能把
“覆盖点 / 巡回路线 / 超限警示”对应上，而且这三个色在色觉障碍模拟下两两可分。
字体用 Noto Sans CJK SC（容器与多数 Linux 自带）；Windows 下自动退回微软雅黑/黑体。
输出同时给 PDF（矢量，插进 LaTeX/Word 用这个）与 PNG（预览用）。
"""
import math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

# ---------- 配色 ----------
C = dict(
    blue   = '#2a78d6',   # 分类 1：覆盖点 / 主对象
    orange = '#eb6834',   # 分类 2：巡回路线 / 对比项
    red    = '#e34948',   # 分类 3：超限、警示、反例
    ink    = '#1a1a19',   # 正文字色
    ink2   = '#52514e',   # 次级字色
    grid   = '#dedcd6',   # 网格
    edge   = '#c9c8c3',   # 三角剖分等结构线
    fill   = '#f2f1ee',   # 目标圆盘等大面积底色
    white  = '#ffffff',
)

def _pick_font():
    have = {f.name for f in font_manager.fontManager.ttflist}
    for n in ('Noto Sans CJK SC','Source Han Sans SC','Microsoft YaHei','SimHei','WenQuanYi Zen Hei'):
        if n in have: return n
    return 'DejaVu Sans'

def use_style():
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': [_pick_font(), 'Noto Sans CJK JP', 'DejaVu Sans'],
        'axes.unicode_minus': False,
        'figure.facecolor': C['white'], 'axes.facecolor': C['white'],
        'axes.edgecolor': C['edge'], 'axes.linewidth': .8,
        'axes.labelcolor': C['ink2'], 'axes.titlecolor': C['ink'],
        'xtick.color': C['ink2'], 'ytick.color': C['ink2'],
        'xtick.labelsize': 9, 'ytick.labelsize': 9,
        'axes.labelsize': 10, 'axes.titlesize': 11.5, 'legend.fontsize': 9,
        'grid.color': C['grid'], 'grid.linewidth': .6,
        'legend.frameon': False, 'savefig.bbox': 'tight', 'savefig.pad_inches': .12,
        'pdf.fonttype': 42, 'ps.fonttype': 42,
    })

def field_axes(ax, R=1800., pad=800., ticks=(-1800,-900,0,900,1800), disk=True):
    """统一的“目标区域”坐标系：等比例、浅网格、可选画出半径 R 的目标圆盘。"""
    if disk:
        ax.add_patch(plt.Circle((0,0), R, facecolor=C['fill'], edgecolor='none', zorder=0))
        ax.add_patch(plt.Circle((0,0), R, facecolor='none', edgecolor='#9a9a95',
                                lw=1.0, ls=(0,(5,4)), zorder=6))
    ax.set_aspect('equal')
    ax.set_xlim(-R-pad, R+pad); ax.set_ylim(-R-pad, R+pad)
    ax.set_xticks(ticks); ax.set_yticks(ticks)
    ax.grid(True, zorder=1)
    for s in ('top','right'): ax.spines[s].set_visible(False)

def tour(ax, pts, start=(0.,0.), color=None, lw=1.6, label=None, z=4):
    """把一条开放巡回画成折线，并在起点画一个空心方块标记出发位置。"""
    color = color or C['orange']
    xs = [start[0]]+[p[0] for p in pts]; ys = [start[1]]+[p[1] for p in pts]
    ax.plot(xs, ys, '-', color=color, lw=lw, solid_capstyle='round', zorder=z, label=label)
    ax.plot([start[0]],[start[1]], marker='s', ms=7, mfc=C['white'], mec=color, mew=1.6, zorder=z+1)
    return sum(math.dist((xs[i],ys[i]),(xs[i+1],ys[i+1])) for i in range(len(xs)-1))

def note(ax, s, loc='lower left', dy=0.):
    """图内说明文字：垫一层半透明白底，压在路线之上也读得清。"""
    P = {'lower left':(.025,.025,'left','bottom'), 'lower right':(.975,.025,'right','bottom'),
         'upper left':(.025,.975,'left','top'),     'upper right':(.975,.975,'right','top')}
    x, y, ha, va = P[loc]; y += dy
    ax.text(x, y, s, transform=ax.transAxes, ha=ha, va=va, fontsize=9, color=C['ink2'],
            linespacing=1.55, zorder=9,
            bbox=dict(boxstyle='round,pad=0.35', fc=C['white'], ec='none', alpha=.82))

def tag(ax, xy, s, color=None, dx=0., dy=-18.):
    """指向图元的小标签，同样垫白底，避免压住线条。"""
    ax.annotate(s, xy=xy, xytext=(dx,dy), textcoords='offset points', ha='center', va='center',
                fontsize=8.5, color=color or C['red'], zorder=9,
                bbox=dict(boxstyle='round,pad=0.25', fc=C['white'], ec='none', alpha=.85))

def save(fig, name, outdir=None):
    out = Path(outdir) if outdir else Path(__file__).resolve().parents[2]/'figures'
    out.mkdir(parents=True, exist_ok=True)
    for ext in ('pdf','png'):
        fig.savefig(out/f'{name}.{ext}', dpi=200)
    plt.close(fig)
    return out/f'{name}.png'


# ---------- 流程图图元 ----------
def box(ax, xy, w, h, text, fc=None, ec=None, fs=9.5, tc=None, style='round,pad=0.02', lw=1.3, z=5):
    """圆角文本框，xy 为中心。返回中心坐标，便于接箭头。"""
    from matplotlib.patches import FancyBboxPatch
    fc = fc or C['white']; ec = ec or C['edge']; tc = tc or C['ink']
    ax.add_patch(FancyBboxPatch((xy[0]-w/2, xy[1]-h/2), w, h, boxstyle=style,
                                facecolor=fc, edgecolor=ec, linewidth=lw, zorder=z))
    ax.text(xy[0], xy[1], text, ha='center', va='center', fontsize=fs, color=tc,
            zorder=z+1, linespacing=1.45)
    return xy

def arrow(ax, a, b, text=None, color=None, rad=0., fs=8.5, z=4, dx=0., dy=0.):
    """两点之间的箭头，rad 不为 0 时画成弧线；text 标在中点。"""
    color = color or C['ink2']
    ax.annotate('', xy=b, xytext=a, zorder=z,
                arrowprops=dict(arrowstyle='-|>', color=color, lw=1.2,
                                connectionstyle='arc3,rad=%.3f' % rad, shrinkA=2, shrinkB=4))
    if text:
        ax.text((a[0]+b[0])/2+dx, (a[1]+b[1])/2+dy, text, ha='center', va='center',
                fontsize=fs, color=color, zorder=z+1,
                bbox=dict(boxstyle='round,pad=0.2', fc=C['white'], ec='none', alpha=.9))

def blank_axes(ax, xlim=(0,1), ylim=(0,1), equal=False):
    ax.set_xlim(*xlim); ax.set_ylim(*ylim)
    if equal: ax.set_aspect('equal')
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values(): sp.set_visible(False)
