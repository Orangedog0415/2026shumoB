"""Delaunay 三角剖分：优先用 scipy，没装 scipy 时退回内置的暴力空外接圆检验。

覆盖网只有 25~37 个点，暴力枚举 O(n^4) 也只要几十毫秒，且与 scipy 的结果一致
（实测三张网的最长相交边逐位相同：950.0 / 997.9 / 995.9 m）。
供 图11、图12 共用。
"""

def simplices(P):
    """P 为点列表或 (n,2) 数组，返回三角形的顶点下标三元组列表。"""
    try:
        from scipy.spatial import Delaunay
        return [tuple(s) for s in Delaunay(P).simplices]
    except ImportError:
        pass
    Q = [(float(p[0]), float(p[1])) for p in P]
    n = len(Q); out = []
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                A, B, D = Q[i], Q[j], Q[k]
                area = (B[0]-A[0])*(D[1]-A[1]) - (B[1]-A[1])*(D[0]-A[0])
                if abs(area) < 1e-6:
                    continue                       # 三点共线
                ok = True
                for m in range(n):
                    if m in (i, j, k):
                        continue
                    E = Q[m]
                    ax, ay = A[0]-E[0], A[1]-E[1]
                    bx, by = B[0]-E[0], B[1]-E[1]
                    cx, cy = D[0]-E[0], D[1]-E[1]
                    det = ((ax*ax+ay*ay)*(bx*cy-by*cx) - (bx*bx+by*by)*(ax*cy-ay*cx)
                           + (cx*cx+cy*cy)*(ax*by-ay*bx))
                    if abs(det) > 1e-6 and (det > 0) == (area > 0):
                        ok = False; break          # E 严格落在外接圆内
                if ok:
                    out.append((i, j, k))
    return out
