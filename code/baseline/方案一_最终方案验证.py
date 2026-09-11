"""【方案一】交接版（jqx）《最终可执行思路》的核心算法参考与本地验证＝交接材料中的“策略A”。
发现一个频道即去定位清除；问题三 7 点覆盖，问题四 h=900 m 格网 37 点。

Offline mathematical/closed-loop checks; never connects to the official simulator."""
import json
import math
import random
import copy
from pathlib import Path

DELTA = math.radians(1.005)
EPS = 1e-7


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def clip(poly, n, b):
    if not poly:
        return []
    out = []
    for a, c in zip(poly, poly[1:] + poly[:1]):
        fa, fc = dot(n, a) - b, dot(n, c) - b
        ia, ic = fa <= EPS, fc <= EPS
        if ia != ic:
            t = fa / (fa - fc)
            out.append((a[0] + t * (c[0] - a[0]), a[1] + t * (c[1] - a[1])))
        if ic:
            out.append(c)
    return out


def disk_outer(poly, center, r):
    for i in range(64):
        a = 2 * math.pi * i / 64
        n = math.cos(a), math.sin(a)
        poly = clip(poly, n, r + dot(n, center))
    return poly


def update(poly, s, theta):
    poly = wedge(poly, s, theta)
    return disk_outer(poly, s, 1500)


def wedge(poly, s, theta):
    for a, sign in [(theta - DELTA, -1), (theta + DELTA, 1)]:
        n = -sign * math.sin(a), sign * math.cos(a)
        poly = clip(poly, n, dot(n, s))
    return poly


def diameter(poly):
    if not poly:
        return 0., None
    a, b = max(((a, b) for a in poly for b in poly), key=lambda ab: dist(*ab))
    return dist(a, b), (a, b)


def calipers(poly):
    if len(poly) < 3:
        return diameter(poly)[0]
    def cross(a, b, c):
        return abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))
    best, j, n = 0., 1, len(poly)
    for i in range(n):
        nxt = (i+1) % n
        steps = 0
        while cross(poly[i], poly[nxt], poly[(j+1)%n]) > cross(poly[i], poly[nxt], poly[j]) + 1e-9 and steps < n:
            j = (j+1) % n
            steps += 1
        for k in (j, (j+1)%n):
            best = max(best, dist(poly[i],poly[k]),dist(poly[nxt],poly[k]))
    return best


def second_station_example(step=50):
    first = (0., 0.)
    poly = update(initial_poly(), first, 0.)
    sample = []
    for a, b in zip(poly, poly[1:]+poly[:1]):
        count = max(1, math.ceil(dist(a,b)/100))
        sample.extend((a[0]+i/count*(b[0]-a[0]), a[1]+i/count*(b[1]-a[1])) for i in range(count))
    sample.append(centroid(poly))
    best, feasible = None, 0
    for x in range(0,1501,step):
        for y in range(-1000,1001,step):
            s = x,y
            if radius(poly,s)>999:
                continue
            feasible += 1
            worst = 0.
            for g in sample:
                if dist(g,s)<=5:
                    worst = max(worst,10.)
                    continue
                angle = math.atan2(g[1]-y,g[0]-x)
                for e in (-DELTA,0,DELTA):
                    post=wedge(poly,s,angle+e)
                    worst=max(worst,diameter(post)[0])
            cost=worst+.05*dist(first,s)/5
            val=(cost,dist(first,s),x,y,worst)
            if best is None or val<best:
                best=val
    return {'grid_step_m':step,'source_edge_step_m':100,'feasible_candidates':feasible,'point_m':list(best[2:4]),'sampled_worst_diameter_m':round(best[4],6),'cost':round(best[0],6),'certificate_max_distance_to_outer_polygon_m':radius(poly,best[2:4]),'claim':'finite-sample design example, not continuous minimax optimum'}


def initial_poly():
    return disk_outer([(-1810, -1810), (1810, -1810), (1810, 1810), (-1810, 1810)], (0, 0), 1800)


def centroid(poly):
    # Vertex average is inside every nonempty convex polygon, including degeneracy.
    return tuple(sum(p[i] for p in poly) / len(poly) for i in (0, 1))


def contains(poly, p):
    return all((b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0]) >= -EPS*max(1,dist(a,b))
               for a,b in zip(poly,poly[1:]+poly[:1]))


def radius(poly, c):
    return max(dist(p, c) for p in poly)


def omni_points():
    return [(0., 0.)] + [(1200 * math.cos(i * math.pi / 3), 1200 * math.sin(i * math.pi / 3)) for i in range(6)]


def mixed_points():
    pts = []
    for l in range(-4, 5):
        for k in range(-4, 5):
            p = (900 * (k + (l % 2) / 2), 900 * math.sqrt(3) * l / 2)
            if math.hypot(*p) <= 2700 + EPS:
                pts.append(p)
    return sorted(pts, key=lambda p: (dist(p, (0, 0)), p[0], p[1]))


def fallback_cells(poly, anchor, theta):
    u = math.cos(theta), math.sin(theta)
    w = -u[1], u[0]
    cells = []
    for i in range(75):
        for j in (range(3) if i % 2 == 0 else reversed(range(3))):
            x0, y0 = 20 * i, -30 + 20 * j
            cell = [tuple(anchor[t] + x * u[t] + y * w[t] for t in (0, 1))
                    for x, y in [(x0, y0), (x0 + 20, y0), (x0 + 20, y0 + 20), (x0, y0 + 20)]]
            p = poly if poly is not None else cell
            for n, b in [(u, dot(u, anchor) + x0 + 20), ((-u[0], -u[1]), -dot(u, anchor) - x0),
                         (w, dot(w, anchor) + y0 + 20), ((-w[0], -w[1]), -dot(w, anchor) - y0)]:
                p = clip(p, n, b)
            if p:
                c = tuple(anchor[t] + (x0 + 10) * u[t] + (y0 + 10) * w[t] for t in (0, 1))
                cells.append((c, cell))
    return cells


class World:
    def __init__(self, sources, salt=0):
        self.sources = sources
        self.pos = (0., 0.)
        self.channel = 1
        self.time = 0.
        self.moves = self.detect = self.switch = self.cleartime = 0.
        self.actions = 0
        self.salt = salt

    def move(self, p):
        dt = dist(self.pos, p) / 5
        self.time += dt
        self.moves += dt
        self.pos = p

    def measure(self, p, ch):
        self.move(p)
        sw = int(ch != self.channel)
        self.channel = ch
        self.time += 5 + sw
        self.detect += 5
        self.switch += sw
        self.actions += 1
        s = self.sources.get(ch)
        if s is None or s['cleared']:
            return 'no_signal', None
        d = dist(p, s['g'])
        if d > s['r'] or (s['type'] == 'D' and dot((p[0] - s['g'][0], p[1] - s['g'][1]), s['u']) < -1e-10):
            return 'no_signal', None
        if d <= 5:
            return 'near', None
        # Fixed, spatially correlated error. Repeated same point returns same value.
        e = math.sin(.007 * p[0] + .011 * p[1] + ch * 1.7 + self.salt)
        a = math.degrees(math.atan2(s['g'][1] - p[1], s['g'][0] - p[0])) + e
        return 'direction', math.radians(round(a % 360, 2) % 360)

    def clear(self, p, ch):
        self.move(p)
        s = self.sources.get(ch)
        ok = s is not None and not s['cleared'] and dist(p, s['g']) <= 20
        dt = 5 if ok else 3
        self.time += dt
        self.cleartime += dt
        self.actions += 1
        if ok:
            s['cleared'] = True
        return ok


def local(world, ch, first, theta, force_fallback=False):
    poly = update(initial_poly(), first, theta)
    failed, measured = [], [first]
    trials = probes = 0
    if not force_fallback:
        for _ in range(6):
            if not poly:
                break
            c = centroid(poly)
            r = radius(poly, c)
            if trials < 2 and r <= 40:
                trials += 1
                if world.clear(c, ch):
                    return
                assert r > 19.5, 'Certified clear contradicted by response'
                failed.append(c)
            elif probes < 4:
                cand = [c]
                for rr in (60, 150, 300):
                    cand.extend((c[0] + rr * math.cos(j * math.pi / 4), c[1] + rr * math.sin(j * math.pi / 4)) for j in range(8))
                cand = [p for p in cand if math.hypot(*p) <= 3000 and all(dist(p, a) >= 1 for a in measured)]
                if not cand:
                    break
                def score(p):
                    # Local range proxy plus actual movement cost, in seconds.
                    return dist(p, c) * .035 / 5 + dist(p, world.pos) / 5
                p = min(cand, key=lambda p: (score(p), p[0], p[1]))
                probes += 1
                z, a = world.measure(p, ch)
                measured.append(p)
                if z == 'near':
                    assert world.clear(p, ch), 'near must clear'
                    return
                if z == 'direction':
                    new = update(poly, p, a)
                    if not new:
                        break
                    poly = new
            else:
                break
    # Certified rectangle comes from first bearing, independent of later approximations.
    if not poly:
        poly = update(initial_poly(), first, theta)
    attempted = set()
    for c, cell in fallback_cells(poly, first, theta):
        if any(max(dist(v, f) for v in cell) <= 20 - EPS for f in failed):
            continue
        attempted.add(c)
        if world.clear(c, ch):
            return
        failed.append(c)
    for c, _ in fallback_cells(None, first, theta):
        if c not in attempted:
            attempted.add(c)
            if world.clear(c, ch):
                return
    raise AssertionError('Exhausted certified clearing cover')


def solve(world, mixed, force_fallback=False):
    q = mixed_points() if mixed else omni_points()
    unknown = set(range(1, 21))
    cleared_count = 0
    visited = {ch: set() for ch in unknown}
    while unknown:
        if cleared_count == 16:
            break
        remaining = [i for i in range(len(q)) if any(i not in visited[ch] for ch in unknown)]
        if not remaining:
            assert all(len(visited[ch]) == len(q) for ch in unknown)
            unknown.clear()  # All remaining channels have a per-channel coverage exclusion certificate.
            break
        i = min(remaining, key=lambda i: (dist(world.pos, q[i]), i))
        channels = sorted([ch for ch in unknown if i not in visited[ch]], key=lambda ch: (ch != world.channel, ch))
        for ch in channels:
            z, a = world.measure(q[i], ch)
            visited[ch].add(i)
            if z == 'near':
                assert world.clear(q[i], ch)
                cleared_count += 1
                unknown.remove(ch)
                break
            if z == 'direction':
                local(world, ch, q[i], a, force_fallback)
                cleared_count += 1
                unknown.remove(ch)
                break
    assert all(s['cleared'] for s in world.sources.values())
    assert abs(world.time - world.moves - world.detect - world.switch - world.cleartime) < 1e-6
    assert world.time < 360000
    return {'virtual_s': round(world.time, 3), 'actions': world.actions, 'sources': len(world.sources), 'clear_ratio': 1.0}


def source(g, r=1000, kind='O', angle=0):
    return {'g': g, 'r': r, 'type': kind, 'u': (math.cos(angle), math.sin(angle)), 'cleared': False}


def main():
    rng = random.Random(20260911)
    tests = {}
    counter = None
    maxdiff = 0.
    for _ in range(300):
        p=initial_poly()
        obs=[]
        for j in range(3):
            a=rng.random()*2*math.pi
            rr=rng.uniform(100,1500)
            s=(rr*math.cos(a),rr*math.sin(a))
            theta=math.atan2(-s[1],-s[0])+rng.uniform(-math.radians(1),math.radians(1))
            p=wedge(p,s,theta)
            obs.append({'station':s,'bearing_deg':math.degrees(theta)%360})
        assert p
        assert contains(p,(0,0))
        d,pair=diameter(p)
        maxdiff=max(maxdiff,abs(d-calipers(p)))
        mid=((pair[0][0]+pair[1][0])/2,(pair[0][1]+pair[1][1])/2)
        violation=radius(p,mid)-d/2
        if violation>1e-5 and counter is None:
            counter={'observations':obs,'vertices':p,'diameter_m':d,'circle_radius_m':d/2,'max_vertex_distance_m':radius(p,mid)}
    assert maxdiff<1e-7 and counter is not None
    tests['polygon_diameter_checks']={'cases':300,'max_absolute_difference_m':maxdiff,'noncovering_bearing_example':counter}
    tests['second_station_example']=second_station_example()
    # Boundary rays, angle wrap and error quantization: true source remains in polygon.
    for deg in (0, .001, 90, 179.999, 270, 359.999):
        for error in (-1, -.995, 0, .995, 1):
            g = (1499 * math.cos(math.radians(deg)), 1499 * math.sin(math.radians(deg)))
            a = math.radians(round((deg + error) % 360, 2) % 360)
            p = update(initial_poly(), (0, 0), a)
            assert p and contains(p,g) and any(dist(c, g) <= 20 for c, _ in fallback_cells(p, (0, 0), a))
    tests['bearing_and_fallback_boundary_cases'] = 30
    # Full lattice covering checks supplement (not replace) triangle proof.
    q = mixed_points()
    for i in range(360):
        a = 2 * math.pi * i / 360
        for rr in (0, 899, 1799.999, 1800):
            g = rr * math.cos(a), rr * math.sin(a)
            for j in range(36):
                u = math.cos(j * math.pi / 18), math.sin(j * math.pi / 18)
                assert any(dist(p, g) <= 1000 + EPS and dot((p[0]-g[0], p[1]-g[1]), u) >= -EPS for p in q)
    tests['directional_cover_location_direction_pairs'] = 360 * 4 * 36
    w = World({3: source((300, 400))})
    w.measure((0, 0), 1)
    assert w.clear((300, 400), 3)
    w.measure((0, 0), 1)
    assert w.time == 215 and w.switch == 0 and w.channel == 1
    tests['measure_clear_measure_time_s'] = 215
    w = World({1: source((0, 0))})
    surround = [(100,0),(-50,50*math.sqrt(3)),(-50,-50*math.sqrt(3))]
    assert all(w.measure(p,1)[0]=='direction' for p in surround)
    tests['omni_source_in_mixed_model_three_surrounding_signals'] = True
    # All eight cell corners of the three strip rows across near/far columns.
    for x in (0, 20, 1480, 1500):
        for y in (-26.30948931332, 0, 26.30948931332):
            assert min(math.hypot(x-(20*i+10), y-(-20+20*j)) for i in range(75) for j in range(3)) <= math.sqrt(200)+EPS
    runs = []
    for mixed in (False, True):
        for n in (10, 13, 16):
            for rep in range(4):
                sources = {}
                channels = rng.sample(range(1, 21), n)
                for ch in channels:
                    a = rng.random() * 2 * math.pi
                    rr = 1800 * math.sqrt(rng.random())
                    sources[ch] = source((rr*math.cos(a), rr*math.sin(a)), rng.uniform(1000, 1500), 'D' if mixed and rng.random()<.65 else 'O', rng.random()*2*math.pi)
                result = solve(World(sources, rep), mixed)
                result.update(mixed=mixed, seed_case=rep)
                runs.append(result)
    # Boundary outward emitters, near origin, full budget of 16 sources, forced fallback.
    for force in (False, True):
        sources = {i+1: source((1800*math.cos(i*2*math.pi/15), 1800*math.sin(i*2*math.pi/15)), kind='D', angle=i*2*math.pi/15) for i in range(15)}
        sources[20] = source((0, 0))
        result = solve(World(sources, 2), True, force)
        result.update(boundary_outward=True, forced_fallback=force)
        runs.append(result)
    tests['closed_loop_runs'] = runs
    tests['summary'] = {'runs':len(runs), 'all_cleared': True, 'max_virtual_s': max(r['virtual_s'] for r in runs), 'max_actions':max(r['actions'] for r in runs), 'mixed_points':len(q), 'omni_points':7}
    paired_rng=random.Random(9811)
    paired=[]
    for mixed in (False,True):
        for rep in range(6):
            src={}
            for ch in paired_rng.sample(range(1,21),13):
                a=paired_rng.random()*2*math.pi
                r=1800*math.sqrt(paired_rng.random())
                src[ch]=source((r*math.cos(a),r*math.sin(a)),paired_rng.uniform(1000,1500),'D' if mixed and paired_rng.random()<.6 else 'O',paired_rng.random()*2*math.pi)
            fast=solve(World(copy.deepcopy(src),rep),mixed)
            baseline=solve(World(copy.deepcopy(src),rep),mixed,True)
            paired.append({'mixed':mixed,'case':rep,'fast_s':fast['virtual_s'],'fallback_s':baseline['virtual_s']})
    fmean=sum(p['fast_s'] for p in paired)/len(paired)
    bmean=sum(p['fallback_s'] for p in paired)/len(paired)
    tests['paired_ablation']={'cases':paired,'fast_mean_s':fmean,'fallback_mean_s':bmean,'relative_mean_reduction':1-fmean/bmean,'fast_wins':sum(p['fast_s']<p['fallback_s'] for p in paired),'all_cleared':True}
    output = Path(__file__).with_name('方案一_最终方案验证结果.json')
    output.write_text(json.dumps(tests, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(tests['summary'], ensure_ascii=False))


if __name__ == '__main__':
    main()
