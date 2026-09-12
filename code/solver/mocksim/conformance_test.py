# -*- coding: utf-8 -*-
"""本地 mock 模拟器的协议一致性自测。

逐条检查 docs/problem/附件2.docx §1、§2、§4、§5、§7-§10 写明的行为：
状态码、accepted、虚拟时钟、幂等与并发、物理规则、故障注入下的重放。

运行：python conformance_test.py        （全部通过时退出码 0）
"""

import http.client
import json
import math
import os
import socket
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server as SV                                             # noqa: E402
import world as W                                               # noqa: E402

TEAM = 'TEST-TEAM'
CLOSED = ('CLOSED', None)
_results = []


def check(name, ok, detail=''):
    _results.append((name, bool(ok), detail))
    print('%s  %s%s' % ('PASS' if ok else 'FAIL', name, ('  | ' + detail) if detail else ''))


def free_port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    p = s.getsockname()[1]
    s.close()
    return p


def start_sim(sources=None, faults='', **over):
    cfg = SV.build_parser().parse_args([])
    cfg.port = free_port()
    cfg.robot_id = TEAM
    cfg.countdown = 0
    cfg.quiet = True
    cfg.error = 'zero'
    cfg.seed = 2026
    cfg.problem = 3
    cfg.n = 12
    for k, v in over.items():
        setattr(cfg, k, v)
    cfg.faults = SV.parse_faults(faults)
    sim = SV.MockSimulator(cfg)
    if sources is not None:
        sim.session.world = W.World(sources, cfg.error, cfg.salt)
    sim.start()
    return sim


def raw(sim, method, path, body, ctype='application/json',
        extra_headers=None, content_length=None):
    """返回 (status, 解析后的JSON或原始文本)，连接被直接关闭时返回 CLOSED。"""
    if isinstance(body, (dict, list)):
        body = json.dumps(body, ensure_ascii=False)
    if isinstance(body, str):
        body = body.encode('utf-8')
    conn = http.client.HTTPConnection('127.0.0.1', sim.port, timeout=5)
    headers = {}
    if ctype is not None:
        headers['Content-Type'] = ctype
    headers['Content-Length'] = str(content_length if content_length is not None else len(body))
    if extra_headers:
        headers.update(extra_headers)
    try:
        conn.putrequest(method, path, skip_host=False, skip_accept_encoding=True)
        for k, v in headers.items():
            conn.putheader(k, v)
        conn.endheaders()
        if body:
            conn.send(body)
        resp = conn.getresponse()
        text = resp.read().decode('utf-8', 'replace')
        try:
            return resp.status, json.loads(text)
        except ValueError:
            return resp.status, text
    except (http.client.BadStatusLine, http.client.RemoteDisconnected,
            ConnectionResetError, socket.timeout):
        return CLOSED
    finally:
        conn.close()


def base(rid):
    return {'arena_id': 'default', 'robot_id': TEAM, 'request_id': rid}


def act(rid, x, y, ch):
    p = base(rid)
    p['position'] = {'x': x, 'y': y}
    p['channel'] = ch
    return p


def src(ch, x, y, recv=1200.0, kind='O', face=0.0):
    return {'ch': ch, 'x': float(x), 'y': float(y), 'recv': recv,
            'kind': kind, 'face_deg': face, 'cleared': False}


# ================================================================== 用例

def t_paths_and_methods():
    sim = start_sim()
    try:
        for path in ('/measures', '/measure/', '/Measure', '/', '/measure?x=1'):
            st, _ = raw(sim, 'POST', path, base('r'))
            check('路径不精确 %-14s -> 404' % path, st == 404, '实际 %s' % st)
        for m in ('GET', 'PUT', 'DELETE', 'PATCH'):
            st, _ = raw(sim, m, '/measure', b'')
            check('%-6s /measure -> 405' % m, st == 405, '实际 %s' % st)
    finally:
        sim.stop()


def t_headers():
    sim = start_sim()
    try:
        st, _ = raw(sim, 'POST', '/enter', base('h1'), ctype='text/plain')
        check('Content-Type: text/plain -> 415', st == 415, '实际 %s' % st)
        st, _ = raw(sim, 'POST', '/enter', base('h2'), ctype='application/json; boundary=x')
        check('Content-Type 带其他参数 -> 415', st == 415, '实际 %s' % st)
        st, _ = raw(sim, 'POST', '/enter', base('h3'), ctype='application/json; charset=utf-8')
        check('Content-Type 带 charset=utf-8 -> 接受', st == 200, '实际 %s' % st)
        st, _ = raw(sim, 'POST', '/enter', base('h4'), extra_headers={'Content-Encoding': 'gzip'})
        check('Content-Encoding: gzip -> 415', st == 415, '实际 %s' % st)
        big = json.dumps({'arena_id': 'default', 'robot_id': TEAM,
                          'request_id': 'x', 'pad': 'A' * 70000})
        st, _ = raw(sim, 'POST', '/enter', big)
        check('请求体 > 65536 字节 -> 413', st == 413, '实际 %s' % st)
    finally:
        sim.stop()


def t_body_400():
    sim = start_sim()
    try:
        cases = [
            ('非法 JSON', '{not json'),
            ('重复键', '{"arena_id":"default","arena_id":"default","robot_id":"%s","request_id":"a"}' % TEAM),
            ('带 BOM', '﻿' + json.dumps(base('b'))),
            ('顶层不是对象', '[1,2,3]'),
            ('缺 robot_id', json.dumps({'arena_id': 'default', 'request_id': 'c'})),
            ('arena_id 非字符串', json.dumps({'arena_id': 1, 'robot_id': TEAM, 'request_id': 'd'})),
            ('robot_id 为空', json.dumps({'arena_id': 'default', 'robot_id': '', 'request_id': 'e'})),
            ('request_id 含控制字符', json.dumps({'arena_id': 'default', 'robot_id': TEAM, 'request_id': 'a\nb'})),
            ('request_id 超 128 字节', json.dumps({'arena_id': 'default', 'robot_id': TEAM, 'request_id': 'x' * 129})),
        ]
        for name, body in cases:
            st, _ = raw(sim, 'POST', '/enter', body)
            check('%-22s -> 400' % name, st == 400, '实际 %s' % st)

        raw(sim, 'POST', '/enter', base('ok'))
        bad = [
            ('缺 position.y', json.dumps({'arena_id': 'default', 'robot_id': TEAM,
                                          'request_id': 'p1', 'position': {'x': 1}, 'channel': 1})),
            ('position.x = NaN', '{"arena_id":"default","robot_id":"%s","request_id":"p2",'
                                 '"position":{"x":NaN,"y":0},"channel":1}' % TEAM),
            ('position.x 超 2e6', json.dumps(act('p3', 3e6, 0, 1))),
            ('channel = 1.5', json.dumps(act('p4', 0, 0, 1.5))),
            ('channel = 0', json.dumps(act('p5', 0, 0, 0))),
            ('channel = 21', json.dumps(act('p6', 0, 0, 21))),
            ('channel = "1"', json.dumps(act('p7', 0, 0, '1'))),
            ('channel = true', json.dumps(act('p8', 0, 0, True))),
            ('position 非对象', json.dumps({'arena_id': 'default', 'robot_id': TEAM,
                                            'request_id': 'p9', 'position': 5, 'channel': 1})),
        ]
        for name, body in bad:
            st, _ = raw(sim, 'POST', '/measure', body)
            check('%-22s -> 400' % name, st == 400, '实际 %s' % st)

        st, r = raw(sim, 'POST', '/measure', json.dumps(act('p10', 0, 0, 1.0)))
        check('channel = 1.0（整数值）-> 接受', st == 200 and r.get('accepted') is True,
              '实际 %s %s' % (st, r))
    finally:
        sim.stop()


def t_accepted_false():
    sim = start_sim()
    try:
        st, r = raw(sim, 'POST', '/measure', act('n1', 0, 0, 1))
        check('未 /enter 就 /measure -> 200 accepted=false',
              st == 200 and r.get('accepted') is False, '实际 %s %s' % (st, r))
        check('accepted=false 时 virtual_time_s 为 0', r.get('virtual_time_s') == 0, str(r))
        check('accepted=false 时只含 3 个公共字段',
              set(r) == {'accepted', 'real_timestamp_ms', 'virtual_time_s'}, str(r))

        st, r = raw(sim, 'POST', '/exit', base('n2'))
        check('未 /enter 就 /exit -> accepted=false', st == 200 and r['accepted'] is False)

        p = base('n3'); p['arena_id'] = 'other'
        st, r = raw(sim, 'POST', '/enter', p)
        check('arena_id 不是 default -> accepted=false', st == 200 and r['accepted'] is False)

        p = base('n4'); p['robot_id'] = TEAM + 'X'
        st, r = raw(sim, 'POST', '/enter', p)
        check('robot_id 不匹配 -> accepted=false', st == 200 and r['accepted'] is False)

        p = base('n5'); p['debug'] = 1
        st, r = raw(sim, 'POST', '/enter', p)
        check('含未声明字段 -> accepted=false', st == 200 and r['accepted'] is False)

        st, r = raw(sim, 'POST', '/enter', base('n6'))
        check('/enter 成功', st == 200 and r['accepted'] is True)
        check('/enter 返回 remaining_real_duration_s',
              isinstance(r.get('remaining_real_duration_s'), int)
              and 0 <= r['remaining_real_duration_s'] <= 1200, str(r))
        check('/enter 不推进虚拟时钟', r['virtual_time_s'] == 0, str(r))

        st, r = raw(sim, 'POST', '/enter', base('n7'))
        check('重复 /enter -> accepted=false', st == 200 and r['accepted'] is False)

        p = act('n8', 0, 0, 1); p['position']['z'] = 1
        st, r = raw(sim, 'POST', '/measure', p)
        check('position 含未声明字段 -> accepted=false', st == 200 and r['accepted'] is False)

        st, r = raw(sim, 'POST', '/measure', act('n8', 0, 0, 1))
        check('被拒的 request_id 修正后可复用', st == 200 and r['accepted'] is True,
              '实际 %s %s' % (st, r))
    finally:
        sim.stop()


def t_idempotency():
    sim = start_sim()
    try:
        raw(sim, 'POST', '/enter', base('e'))
        st, r1 = raw(sim, 'POST', '/measure', act('m1', 300, 400, 1))
        st, r2 = raw(sim, 'POST', '/measure', act('m1', 300, 400, 1))
        check('同 ID 同内容重放 -> 返回首次完整响应',
              r1['virtual_time_s'] == r2['virtual_time_s']
              and r1['measure_result'] == r2['measure_result'], '%s vs %s' % (r1, r2))
        check('同 ID 重放不重复推进虚拟时钟', r2['virtual_time_s'] == 105.0, str(r2))

        st, r = raw(sim, 'POST', '/measure', act('m1', 300, 401, 1))
        check('同 ID 改位置 -> 409', st == 409, '实际 %s' % st)
        st, r = raw(sim, 'POST', '/measure', act('m1', 300, 400, 2))
        check('同 ID 改频道 -> 409', st == 409, '实际 %s' % st)
        st, r = raw(sim, 'POST', '/clear', act('m1', 300, 400, 1))
        check('同 ID 改路径 -> 409', st == 409, '实际 %s' % st)
    finally:
        sim.stop()

    sim2 = start_sim(idem_limit=3)
    try:
        raw(sim2, 'POST', '/enter', base('a'))
        raw(sim2, 'POST', '/measure', act('b', 0, 0, 1))
        raw(sim2, 'POST', '/measure', act('c', 0, 0, 1))
        st, r = raw(sim2, 'POST', '/measure', act('d', 0, 0, 1))
        check('幂等记录达上限 -> 429', st == 429, '实际 %s' % st)
    finally:
        sim2.stop()


def t_timing():
    sim = start_sim()
    try:
        raw(sim, 'POST', '/enter', base('e'))
        seq = [('/measure', act('a', 300, 400, 1), 105.0),
               ('/measure', act('b', 300, 400, 2), 111.0),
               ('/clear', act('c', 300, 0, 3), 194.0),
               ('/measure', act('d', 300, 0, 2), 199.0)]
        ok = True
        for path, p, want in seq:
            st, r = raw(sim, 'POST', path, p)
            if r.get('virtual_time_s') != want:
                ok = False
                check('附件2 §10 %s 步虚拟时刻应为 %s' % (path, want), False, str(r))
        check('附件2 §10 计时示例逐步复现（105/111/194/199）', ok)
    finally:
        sim.stop()

    sources = [src(1, 1700, 0), src(3, 300, 400)]
    sim = start_sim(sources=sources)
    try:
        raw(sim, 'POST', '/enter', base('e'))
        st, r1 = raw(sim, 'POST', '/measure', act('a', 0, 0, 1))
        st, r2 = raw(sim, 'POST', '/clear', act('b', 300, 400, 3))
        st, r3 = raw(sim, 'POST', '/measure', act('c', 0, 0, 1))
        check('思路 §2.3 校验例 measure→clear→measure = 215 s',
              r3['virtual_time_s'] == 215.0,
              '%s / %s / %s' % (r1['virtual_time_s'], r2['virtual_time_s'], r3['virtual_time_s']))
        check('该例中 clear 成功（清除动作 5 s）', r2['clear_result'] == 'success', str(r2))
        check('clear 后再测同频道无切换耗时',
              r3['virtual_time_s'] - r2['virtual_time_s'] == 105.0)
    finally:
        sim.stop()

    sim = start_sim(sources=[src(1, 1000, 0), src(5, 0, 0)])
    try:
        raw(sim, 'POST', '/enter', base('e'))
        raw(sim, 'POST', '/measure', act('a', 0, 0, 1))
        raw(sim, 'POST', '/clear', act('b', 0, 0, 5))
        st, r = raw(sim, 'POST', '/measure', act('c', 0, 0, 1))
        check('/clear 的 channel 不改变测向机频道（5+5+5=15）',
              r['virtual_time_s'] == 15.0, str(r))
    finally:
        sim.stop()


def t_physics():
    s_omni = src(2, 500, 0, recv=1000.0)
    s_dir = src(4, -500, 0, recv=1000.0, kind='D', face=0.0)
    sim = start_sim(sources=[s_omni, s_dir])
    try:
        raw(sim, 'POST', '/enter', base('e'))
        st, r = raw(sim, 'POST', '/measure', act('ph_a', 0, 0, 2))
        check('全向源在接收半径内 -> direction', r['measure_result'] == 'direction', str(r))
        check('示向度以正东为 0°、逆时针为正', abs(r['svd_deg'] - 0.0) < 1e-9, str(r))

        st, r = raw(sim, 'POST', '/measure', act('ph_b', 1600, 0, 2))
        check('超出有效接收半径 -> no_signal', r['measure_result'] == 'no_signal', str(r))

        st, r = raw(sim, 'POST', '/measure', act('ph_c', 497, 0, 2))
        check('距离 3 m（≤5）-> near，且不返回 svd_deg',
              r['measure_result'] == 'near' and 'svd_deg' not in r, str(r))

        st, r = raw(sim, 'POST', '/measure', act('ph_d', 0, 0, 4))
        check('定向源朝向一侧 -> direction', r['measure_result'] == 'direction', str(r))
        st, r = raw(sim, 'POST', '/measure', act('ph_e', -900, 0, 4))
        check('定向源背面 -> no_signal', r['measure_result'] == 'no_signal', str(r))
        st, r = raw(sim, 'POST', '/measure', act('ph_f', -500, 300, 4))
        check('定向源覆盖边界（夹角 90°，含边界）-> direction',
              r['measure_result'] == 'direction', str(r))
        st, r = raw(sim, 'POST', '/measure', act('ph_g', 0, 0, 7))
        check('该频道无干扰源 -> no_signal', r['measure_result'] == 'no_signal', str(r))

        st, r = raw(sim, 'POST', '/clear', act('ph_h', 480, 0, 2))
        check('距离恰为 20 m（含边界）-> 清除成功', r['clear_result'] == 'success', str(r))
        st, r = raw(sim, 'POST', '/clear', act('ph_i', 480, 0, 2))
        check('重复清除同一源 -> no_target_in_range',
              r['clear_result'] == 'no_target_in_range', str(r))
        st, r = raw(sim, 'POST', '/measure', act('ph_j', 490, 0, 2))
        check('已清除的频道 -> no_signal', r['measure_result'] == 'no_signal', str(r))
        st, r = raw(sim, 'POST', '/clear', act('ph_k', -481, 0, 4))
        check('定向源背面也能清除（清除与朝向无关）',
              r['clear_result'] == 'success', str(r))
    finally:
        sim.stop()

    sim = start_sim(sources=[src(2, 500, 0)], error='orig_sin')
    try:
        raw(sim, 'POST', '/enter', base('e'))
        st, r1 = raw(sim, 'POST', '/measure', act('ph_a', 100, 100, 2))
        st, r2 = raw(sim, 'POST', '/measure', act('ph_b', 100, 100, 2))
        check('同一点重复测量，示向度完全相同（不能靠原地重测降噪）',
              r1['svd_deg'] == r2['svd_deg'], '%s vs %s' % (r1, r2))
        true_deg = math.degrees(math.atan2(-100, 400)) % 360
        d = abs((r1['svd_deg'] - true_deg + 180) % 360 - 180)
        check('示向度误差不超过 1°', d <= 1.0 + 1e-9, '偏差 %.4f°' % d)
        check('示向度保留两位小数', round(r1['svd_deg'], 2) == r1['svd_deg'], str(r1))
    finally:
        sim.stop()


def t_exit_and_close():
    sim = start_sim()
    try:
        raw(sim, 'POST', '/enter', base('e'))
        st, r = raw(sim, 'POST', '/exit', base('x'))
        check('/exit 返回 user_exit', r.get('exit_reason') == 'user_exit', str(r))
        check('/exit 不推进虚拟时钟', r['virtual_time_s'] == 0, str(r))
        time.sleep(.1)
        out = raw(sim, 'POST', '/measure', act('y', 0, 0, 1))
        check('测试结束后连接直接关闭，没有 JSON 体', out == CLOSED, str(out))
    finally:
        sim.stop()

    sim = start_sim(countdown=0)
    sim.session.state = 'preparing'
    try:
        out = raw(sim, 'POST', '/enter', base('e'))
        check('接口未开放时连接直接关闭', out == CLOSED, str(out))
    finally:
        sim.stop()

    sim = start_sim(window=0.6, enter_limit=0.6)
    try:
        raw(sim, 'POST', '/enter', base('e'))
        time.sleep(1.2)
        out = raw(sim, 'POST', '/measure', act('a', 0, 0, 1))
        check('现实时间截止后连接关闭', out == CLOSED, str(out))
    finally:
        sim.stop()


def t_faults():
    sim = start_sim(sources=[src(2, 500, 0)], faults='3:drop')
    try:
        raw(sim, 'POST', '/enter', base('e'))
        raw(sim, 'POST', '/measure', act('a', 300, 400, 2))
        out = raw(sim, 'POST', '/measure', act('b', 300, 0, 2))
        check('故障注入 drop：无响应，连接关闭', out == CLOSED, str(out))
        st, r = raw(sim, 'POST', '/measure', act('b', 300, 0, 2))
        check('丢响应后同 ID 重放拿到已执行的结果',
              st == 200 and r.get('accepted') is True, '%s %s' % (st, r))
        # 100(移动) + 1(频道1->2) + 5(检测) = 106；再 80(移动) + 5(检测) = 191
        check('丢响应后重放不重复计时（106+80+5=191）',
              r['virtual_time_s'] == 191.0, str(r))
        st, r = raw(sim, 'POST', '/measure', act('b', 300, 1, 2))
        check('丢响应后同 ID 改内容 -> 409', st == 409, '实际 %s' % st)
    finally:
        sim.stop()

    sim = start_sim(faults='2:badjson,3:close,4:http500,5:http429')
    try:
        raw(sim, 'POST', '/enter', base('e'))
        st, r = raw(sim, 'POST', '/measure', act('a', 0, 0, 1))
        check('故障注入 badjson：返回非 JSON 体', st == 200 and isinstance(r, str), str(r))
        out = raw(sim, 'POST', '/measure', act('b', 0, 0, 1))
        check('故障注入 close：执行前关闭连接', out == CLOSED, str(out))
        st, _ = raw(sim, 'POST', '/measure', act('c', 0, 0, 1))
        check('故障注入 http500', st == 500, '实际 %s' % st)
        st, _ = raw(sim, 'POST', '/measure', act('d', 0, 0, 1))
        check('故障注入 http429', st == 429, '实际 %s' % st)
    finally:
        sim.stop()


def t_concurrency():
    sim = start_sim(faults='2:delay=800')
    try:
        raw(sim, 'POST', '/enter', base('e'))
        got = []

        def go(rid, y):
            got.append(raw(sim, 'POST', '/measure', act(rid, 0, y, 1))[0])

        ts = [threading.Thread(target=go, args=('c1', 0)),
              threading.Thread(target=go, args=('c2', 100))]
        ts[0].start()
        time.sleep(.25)
        ts[1].start()
        for t in ts:
            t.join()
        check('未决动作期间发送不同动作 -> 409', 409 in got, '状态码 %s' % got)
    finally:
        sim.stop()


def t_virtual_limit():
    sim = start_sim(sources=[src(1, 0, 0)])
    try:
        raw(sim, 'POST', '/enter', base('e'))
        st, r = raw(sim, 'POST', '/measure', act('a', 1_900_000, 0, 1))
        check('单次动作可推进到虚拟上限并被接受', st == 200 and r['accepted'] is True, str(r))
        time.sleep(.1)
        out = raw(sim, 'POST', '/measure', act('b', 0, 0, 1))
        check('虚拟时间超限后测试结束、连接关闭', out == CLOSED, str(out))
    finally:
        sim.stop()


def main():
    for fn in (t_paths_and_methods, t_headers, t_body_400, t_accepted_false,
               t_idempotency, t_timing, t_physics, t_exit_and_close,
               t_faults, t_concurrency, t_virtual_limit):
        print('\n---- %s ----' % fn.__name__)
        fn()
    bad = [n for n, ok, _ in _results if not ok]
    print('\n共 %d 项，失败 %d 项' % (len(_results), len(bad)))
    for n in bad:
        print('  FAIL %s' % n)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
