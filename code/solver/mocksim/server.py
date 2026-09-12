# -*- coding: utf-8 -*-
"""本地 mock 模拟器 —— HTTP 服务（严格按 docs/problem/附件2.docx）。

用途：在没有官方模拟器、或不想消耗演练时段的情况下，把官方客户端与问题三/四的
策略完整跑通，并注入通信故障检验客户端的幂等与重试。

只用 Python 标准库。命令行示例见本目录 README.md。

与官方模拟器的已知差异见 README.md「差异与限制」一节。
"""

import argparse
import hashlib
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import protocol as P                                            # noqa: E402
import world as W                                               # noqa: E402

_VT = '@@VIRTUAL_TIME@@'


def _fmt_virtual(us):
    """虚拟时钟：微秒累计，最多保留 6 位小数并去掉无意义的末尾零（附件2 §4.1）。"""
    s = '%.6f' % (us / 1_000_000)
    if '.' in s:
        s = s.rstrip('0').rstrip('.')
    return s or '0'


def _now_ms():
    return int(time.time() * 1000)


# ====================================================================== 会话

class Session:
    """一局测试的状态机。

    preparing -> open -> running -> ended
    preparing / ended 期间机器狗接口未开放，连接直接关闭（附件2 §1.5、§4.5）。
    """

    def __init__(self, cfg):
        self.cfg = cfg
        self.sources = W.generate_sources(
            n=cfg.n, problem=cfg.problem, seed=cfg.seed,
            layout=cfg.layout, radius=cfg.radius, p_directional=cfg.pd)
        self.world = W.World(self.sources, cfg.error, cfg.salt)
        self.case_id = 'MOCK-' + hashlib.md5(
            repr((cfg.problem, cfg.n, cfg.seed, cfg.layout, cfg.radius,
                  cfg.error, cfg.salt, cfg.pd)).encode()).hexdigest()[:8].upper()

        self.state = 'preparing'
        self.entered = False
        self.exit_reason = None
        self.end_reason = None
        self.window_deadline = None      # monotonic
        self.real_deadline = None        # monotonic
        self.enter_mono = None

        self.idem = {}                   # request_id -> {'key','http','body'}
        self.inflight = {}               # thread id -> action key
        self.lock = threading.Lock()     # 保护 inflight / idem
        self.exec_lock = threading.Lock()
        self.seq = 0                     # 到达执行阶段的请求计数，用于故障注入
        self.log_fp = open(cfg.log, 'a', encoding='utf-8') if cfg.log else None

    # ------------------------------------------------ 生命周期
    def open_interface(self):
        self.state = 'open'
        self.window_deadline = time.monotonic() + self.cfg.window
        self.real_deadline = self.window_deadline

    def end(self, reason):
        if self.state != 'ended':
            self.state = 'ended'
            self.end_reason = reason

    def expired(self):
        if self.real_deadline is not None and time.monotonic() >= self.real_deadline:
            return 'real_timeout_window' if not self.entered else 'real_timeout_run'
        if self.world.us >= W.MAX_VIRTUAL_S * 1_000_000:
            return 'virtual_timeout'
        return None

    # ------------------------------------------------ 日志
    def log(self, record):
        if self.log_fp:
            self.log_fp.write(json.dumps(record, ensure_ascii=False) + '\n')
            self.log_fp.flush()

    def close_log(self):
        if self.log_fp:
            self.log_fp.close()
            self.log_fp = None


# ====================================================================== 处理器

class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    server_version = 'CUMCM2026B-MockSim/1.0'

    # ---------------------------------------------- 基础工具
    @property
    def S(self):
        return self.server.session

    def log_message(self, fmt, *args):       # 关掉 BaseHTTPRequestHandler 的 stderr 行
        pass

    def _console(self, text):
        if not self.S.cfg.quiet:
            print(text, flush=True)

    def _write(self, http, body, ctype='application/json; charset=utf-8'):
        data = body.encode('utf-8')
        self.send_response(http)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _render(self, accepted, extra=None):
        """按附件2 §5.2 组装响应体。accepted=false 时只含 3 个公共字段，
        且 virtual_time_s 固定为 0（不是当前虚拟时刻）。"""
        body = {'accepted': bool(accepted),
                'real_timestamp_ms': _now_ms(),
                'virtual_time_s': _VT}
        if accepted and extra:
            body.update(extra)
        raw = json.dumps(body, ensure_ascii=False)
        vt = _fmt_virtual(self.S.world.us if accepted else 0)
        return raw.replace('"%s"' % _VT, vt)

    def _respond(self, http, accepted, extra=None, reason=''):
        raw = self._render(accepted, extra)
        self._write(http, raw)
        self._console('    <- HTTP %d %s%s'
                      % (http, raw, ('  （%s）' % reason) if reason else ''))
        return http, raw

    def _close_silently(self, why):
        self.close_connection = True
        self._console('    <- 连接关闭，无响应（%s）' % why)

    # ---------------------------------------------- 方法分发
    def do_POST(self):
        self._handle('POST')

    def _method_not_allowed(self):
        self._handle(self.command)

    do_GET = do_PUT = do_DELETE = do_PATCH = do_OPTIONS = do_HEAD = _method_not_allowed

    # ---------------------------------------------- 主流程
    def _handle(self, method):
        S = self.S

        # 1) 接口未开放 / 测试已结束：连接直接关闭，没有 JSON 体
        if S.state in ('preparing', 'ended'):
            self._close_silently('接口未开放或测试已结束')
            return

        # 2) 现实/虚拟时间截止
        why = S.expired()
        if why:
            S.end(why)
            self._close_silently('测试已结束：%s' % why)
            return

        # 3) 路径必须精确
        path = self.path
        if '?' in path or path not in P.PATHS:
            self._respond(404, False, reason='路径未知或不精确：%s' % path)
            return
        if method != 'POST':
            self._respond(405, False, reason='%s 方法不被支持' % method)
            return

        self._console('-> %s %s' % (method, path))

        try:
            P.check_headers(self.headers)

            if self.headers.get('Transfer-Encoding'):
                raise P.Reject(400, '不支持 Transfer-Encoding')
            try:
                length = int(self.headers.get('Content-Length') or 0)
            except ValueError:
                raise P.Reject(400, 'Content-Length 非法')
            if length > P.MAX_BODY:
                self.close_connection = True
                raise P.Reject(413, '请求体超过 %d 字节' % P.MAX_BODY)
            raw = self.rfile.read(length) if length else b''
            self._console('   %s' % raw.decode('utf-8', 'replace')[:400])

            obj = P.parse_body(raw)
            action = P.validate(path, obj, S.cfg.robot_id)
        except P.Reject as r:
            self._log_req(method, path, None, r.http, '', r.reason)
            self._respond(r.http, r.accepted, reason=r.reason)
            return

        self._execute(path, action, raw)

    # ---------------------------------------------- 幂等 + 执行
    def _execute(self, path, action, raw):
        S = self.S
        key = P.action_key(action)
        rid = action['request_id']
        tid = threading.get_ident()

        with S.lock:
            rec = S.idem.get(rid)
            if rec is not None:
                if rec['key'] != key:
                    self._respond(409, False, reason='同一 request_id 对应了不同动作')
                    return
                self._console('    <- HTTP %d %s  （幂等重放，不重复执行）'
                              % (rec['http'], rec['body']))
                self._write(rec['http'], rec['body'])
                self._log_req('POST', path, action, rec['http'], rec['body'], '幂等重放')
                return
            if len(S.idem) >= S.cfg.idem_limit:
                self._respond(429, False, reason='本局幂等记录达到上限')
                return
            for other_tid, other_key in S.inflight.items():
                if other_tid != tid and other_key != key:
                    self._respond(409, False, reason='并发发送了不同动作')
                    return
            S.inflight[tid] = key
            S.seq += 1
            seq = S.seq

        try:
            fault = S.cfg.faults.get(seq)
            if fault:
                kind, _, arg = fault.partition('=')
                if kind == 'close':
                    self._close_silently('故障注入：执行前关闭连接（第 %d 个请求）' % seq)
                    return
                if kind == 'http429':
                    self._respond(429, False, reason='故障注入：429')
                    return
                if kind == 'http500':
                    self._respond(500, False, reason='故障注入：500')
                    return

            with S.exec_lock:
                http, accepted, extra, reason = self._business(path, action)
            # 执行完成即注销 inflight：否则串行客户端在收到响应后立刻发下一个动作时，
            # 上一条请求的线程可能还没走到 finally，会被误判成“并发发送了不同动作”而回 409。
            with S.lock:
                S.inflight.pop(tid, None)

            if fault:
                kind, _, arg = fault.partition('=')
                if kind == 'delay':
                    time.sleep(float(arg or 1000) / 1000.0)
                elif kind == 'drop':
                    # 服务端已执行，但响应丢失：客户端必须用同 ID、同内容重发
                    self._log_req('POST', path, action, 0, '', '故障注入：响应丢失（已执行）')
                    if accepted:
                        self._remember(rid, key, http, self._render(accepted, extra))
                    self._close_silently('故障注入：已执行但丢弃响应（第 %d 个请求）' % seq)
                    return
                elif kind == 'badjson':
                    body = 'NOT-A-JSON-BODY'
                    self._write(200, body, 'text/plain; charset=utf-8')
                    if accepted:
                        self._remember(rid, key, http, self._render(accepted, extra))
                    self._console('    <- HTTP 200 %s  （故障注入：非 JSON）' % body)
                    return

            http_out, raw_out = self._respond(http, accepted, extra, reason)
            if accepted:
                self._remember(rid, key, http_out, raw_out)
            self._log_req('POST', path, action, http_out, raw_out, reason)

            if S.exit_reason is not None:
                S.end('user_exit')
            why = S.expired()
            if why:
                S.end(why)
        finally:
            with S.lock:
                S.inflight.pop(tid, None)

    def _remember(self, rid, key, http, body):
        with self.S.lock:
            self.S.idem[rid] = {'key': key, 'http': http, 'body': body}

    # ---------------------------------------------- 业务
    def _business(self, path, action):
        """返回 (http, accepted, extra, reason)。此处只处理测试状态与物理规则。"""
        S = self.S
        w = S.world

        if path == '/enter':
            if S.entered:
                return 200, False, None, '重复调用 /enter'
            if S.state != 'open':
                return 200, False, None, '当前测试状态不接受 /enter'
            S.entered = True
            S.state = 'running'
            S.enter_mono = time.monotonic()
            S.real_deadline = min(S.window_deadline, S.enter_mono + S.cfg.enter_limit)
            remaining = int(max(0, min(1200, S.real_deadline - S.enter_mono)))
            return 200, True, {
                'max_virtual_duration_s': int(W.MAX_VIRTUAL_S),
                'max_real_duration_s': int(S.cfg.enter_limit),
                'remaining_real_duration_s': remaining,
            }, ''

        if not S.entered:
            return 200, False, None, '尚未成功调用 /enter'
        if S.state != 'running':
            return 200, False, None, '机器狗已经退出或测试已结束'

        if path == '/exit':
            S.exit_reason = 'user_exit'
            return 200, True, {'exit_reason': 'user_exit'}, ''

        p = (action['x'], action['y'])
        ch = action['channel']
        if path == '/measure':
            out, timing = w.measure(p, ch)
        else:
            out, timing = w.clear(p, ch)
        self._last_timing = timing
        return 200, True, out, ''

    # ---------------------------------------------- 日志
    def _log_req(self, method, path, action, http, body, reason):
        S = self.S
        rec = {
            'wall_ms': _now_ms(),
            'method': method,
            'path': path,
            'request': action,
            'http_status': http,
            'response': body,
            'note': reason,
            'virtual_time_s': S.world.us / 1_000_000,
            'robot_position': list(S.world.pos),
            'robot_channel': S.world.channel,
        }
        t = getattr(self, '_last_timing', None)
        if t:
            rec['timing'] = {(k[:-3] + '_s' if k.endswith('_us') else k):
                             (v / 1_000_000 if k.endswith('_us') else v)
                             for k, v in t.items()}
            self._last_timing = None
        S.log(rec)


# ====================================================================== 启动

class MockSimulator:
    def __init__(self, cfg):
        self.cfg = cfg
        self.session = Session(cfg)
        self.httpd = ThreadingHTTPServer((cfg.host, cfg.port), Handler)
        self.httpd.session = self.session
        self.httpd.daemon_threads = True
        self.port = self.httpd.server_address[1]
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self._thread.start()
        if self.cfg.countdown > 0:
            for i in range(int(self.cfg.countdown), 0, -1):
                if not self.cfg.quiet:
                    print('倒计时 %d ...' % i, flush=True)
                time.sleep(1)
        self.session.open_interface()
        if not self.cfg.quiet:
            print('机器狗接口已就绪：http://%s:%d  测试案例编码 %s'
                  % (self.cfg.host, self.port, self.session.case_id), flush=True)
        return self.port

    def wait(self):
        S = self.session
        while S.state != 'ended':
            time.sleep(0.05)
            why = S.expired()
            if why:
                S.end(why)
        return S.end_reason

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.session.close_log()


def parse_faults(spec):
    faults = {}
    for item in (spec or '').split(','):
        item = item.strip()
        if not item:
            continue
        n, _, kind = item.partition(':')
        faults[int(n)] = kind
    return faults


def build_parser():
    ap = argparse.ArgumentParser(
        description='2026 国赛 B 题 本地 mock 模拟器（按附件2实现，不是官方模拟器）')
    g = ap.add_argument_group('案例')
    g.add_argument('--problem', type=int, choices=(3, 4), default=3,
                   help='3=全部全向源；4=混合（含定向源）')
    g.add_argument('--n', type=int, default=None, help='干扰源数量 10..16，默认随机')
    g.add_argument('--seed', type=int, default=None, help='案例随机种子')
    g.add_argument('--layout', choices=('uniform', 'boundary', 'outward'), default='uniform',
                   help='源分布：均匀 / 贴边界 / 贴边界且定向源朝外（最难）')
    g.add_argument('--radius', choices=('rand', 'min'), default='rand',
                   help='有效接收半径：U(1000,1500) 或全取下限 1000')
    g.add_argument('--pd', type=float, default=0.65, help='问题四中定向源比例')
    g.add_argument('--error', choices=sorted(W.ERROR_MODELS), default='orig_sin',
                   help='示向度误差模型')
    g.add_argument('--salt', type=int, default=0, help='误差场偏移，换误差实现而不换源布局')

    g = ap.add_argument_group('服务')
    g.add_argument('--host', default='127.0.0.1')
    g.add_argument('--port', type=int, default=2026)
    g.add_argument('--robot-id', default='TEST-TEAM', dest='robot_id',
                   help='模拟“当前登录参赛队号”，请求里的 robot_id 必须逐字节相同')
    g.add_argument('--countdown', type=float, default=5, help='开放接口前的倒计时秒数')
    g.add_argument('--window', type=float, default=1500, help='测试窗口秒数，默认 25 分钟')
    g.add_argument('--enter-limit', type=float, default=1200, dest='enter_limit',
                   help='/enter 成功后的程序运行秒数，默认 20 分钟')
    g.add_argument('--idem-limit', type=int, default=20000, dest='idem_limit',
                   help='本局幂等记录上限，超出返回 429')

    g = ap.add_argument_group('输出与故障注入')
    g.add_argument('--log', default=None, help='JSONL 行为日志路径')
    g.add_argument('--truth-out', default=None, dest='truth_out',
                   help='测试结束后把本局真值写到该 JSON 文件')
    g.add_argument('--mode', choices=('drill', 'formal'), default='drill',
                   help='drill 结束时显示源数量统计，formal 不显示')
    g.add_argument('--reveal', action='store_true', help='开局就在控制台打印真值（仅调试）')
    g.add_argument('--quiet', action='store_true', help='不打印每条请求与反馈')
    g.add_argument('--fault', default='', dest='fault_spec',
                   help='故障注入，如 "3:drop,5:badjson,7:close,9:delay=2000,11:http500"，'
                        '序号按到达执行阶段的请求计数')
    return ap


def main(argv=None):
    cfg = build_parser().parse_args(argv)
    cfg.faults = parse_faults(cfg.fault_spec)
    sim = MockSimulator(cfg)

    if not cfg.quiet:
        print('本地 mock 模拟器（非官方）。问题%d，误差模型 %s，布局 %s，接收半径 %s。'
              % (cfg.problem, cfg.error, cfg.layout, cfg.radius))
        print('数据准备完成。')
    if cfg.reveal:
        print(json.dumps(sim.session.world.truth(), ensure_ascii=False, indent=1))

    sim.start()
    try:
        reason = sim.wait()
    except KeyboardInterrupt:
        sim.session.end('manual_abort')
        reason = 'manual_abort'

    s = sim.session.world.summary()
    print('\n==== 测试结束：%s ====' % reason)
    print('测试案例编码：%s' % sim.session.case_id)
    print('虚拟时间 %.6f s（移动 %.1f / 检测 %.1f / 切换 %.1f / 清除 %.1f）'
          % (s['virtual_time_s'], s['move_s'], s['measure_s'], s['switch_s'], s['clear_s']))
    print('检测 %d 次，清除 %d 次' % (s['measure_count'], s['clear_count']))
    if cfg.mode == 'drill':
        print('干扰源总数 %d（全向 %d，定向 %d），已清除 %d，剩余 %d'
              % (s['source_total'], s['source_omni'], s['source_directional'],
                 s['cleared'], s['remaining']))
    else:
        print('正式模式不显示案例真值。')
    if cfg.truth_out:
        with open(cfg.truth_out, 'w', encoding='utf-8') as f:
            json.dump({'case_id': sim.session.case_id, 'summary': s,
                       'truth': sim.session.world.truth()}, f, ensure_ascii=False, indent=1)
        print('真值已写入 %s' % cfg.truth_out)
    sim.stop()
    return 0 if s['remaining'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
