# -*- coding: utf-8 -*-
"""本地 mock 模拟器 —— 通信协议校验层（严格按 docs/problem/附件2.docx §5）。

本模块只做「请求是否合法」的判断，不涉及测试状态与物理规则。
两类拒绝：
  Reject(http=4xx)                —— HTTP 错误码，响应体仍是含 3 个公共字段的 JSON
  Reject(http=200, accepted=False) —— JSON 结构合法但被业务拒绝
"""

import json
import math
import unicodedata

MAX_BODY = 65536           # 请求体最大字节数（附件2 §5.1）
MAX_DEPTH = 16             # JSON 嵌套层数上限
MAX_COORD = 2_000_000.0    # 坐标绝对值上限（附件2 §1.1）
CHANNEL_MIN, CHANNEL_MAX = 1, 20
ROBOT_ID_MAX = 64          # UTF-8 字节
REQUEST_ID_MAX = 128
ARENA_ID = 'default'

PATHS = ('/enter', '/measure', '/clear', '/exit')
ACTION_PATHS = ('/measure', '/clear')

COMMON_FIELDS = ('arena_id', 'robot_id', 'request_id')
ACTION_FIELDS = COMMON_FIELDS + ('position', 'channel')
POSITION_FIELDS = ('x', 'y')


class Reject(Exception):
    """一次不予执行的请求。

    http         : HTTP 状态码
    accepted     : 业务接受标志（http=200 时才可能出现 accepted=False）
    reason       : 仅供模拟器日志与控制台，不写进响应体（附件2 §5.2：
                   accepted=false 时响应只含 3 个公共字段）
    consumes_id  : 是否占用 request_id 幂等键
    """

    def __init__(self, http, reason, accepted=False, consumes_id=False):
        super().__init__(reason)
        self.http = http
        self.accepted = accepted
        self.reason = reason
        self.consumes_id = consumes_id


# ---------------------------------------------------------------- 头部

def check_headers(headers):
    """Content-Type / Content-Encoding 校验（附件2 §5.1）。不合规抛 415。"""
    ctype = headers.get('Content-Type')
    if ctype is None:
        raise Reject(415, '缺少 Content-Type')
    parts = [p.strip() for p in ctype.split(';')]
    if parts[0].lower() != 'application/json':
        raise Reject(415, 'Content-Type 主类型必须是 application/json')
    for extra in parts[1:]:
        if not extra:
            continue
        k, _, v = extra.partition('=')
        if k.strip().lower() != 'charset' or v.strip().strip('"').lower() != 'utf-8':
            raise Reject(415, 'Content-Type 只允许参数 charset=utf-8')
    enc = headers.get('Content-Encoding')
    if enc is not None and enc.strip().lower() not in ('', 'identity'):
        raise Reject(415, 'Content-Encoding 只允许省略或 identity')


# ---------------------------------------------------------------- 请求体

def _no_dup_pairs(pairs):
    seen = set()
    for k, _ in pairs:
        if k in seen:
            raise ValueError('重复键：%s' % k)
        seen.add(k)
    return dict(pairs)


def _depth(obj, level=1):
    if level > MAX_DEPTH:
        return level
    if isinstance(obj, dict):
        return max([level] + [_depth(v, level + 1) for v in obj.values()])
    if isinstance(obj, list):
        return max([level] + [_depth(v, level + 1) for v in obj])
    return level


def parse_body(raw):
    """原始字节 -> dict。任何结构问题抛 Reject(400)，不占用 request_id。"""
    if len(raw) > MAX_BODY:
        raise Reject(413, '请求体超过 %d 字节' % MAX_BODY)
    if raw[:3] == b'\xef\xbb\xbf':
        raise Reject(400, '请求体带 UTF-8 BOM')
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError:
        raise Reject(400, '请求体不是合法 UTF-8')
    try:
        obj = json.loads(text, object_pairs_hook=_no_dup_pairs)
    except ValueError as e:
        raise Reject(400, 'JSON 解析失败：%s' % e)
    if not isinstance(obj, dict):
        raise Reject(400, '请求体必须是 JSON 对象')
    if _depth(obj) > MAX_DEPTH:
        raise Reject(400, 'JSON 嵌套超过 %d 层' % MAX_DEPTH)
    return obj


# ---------------------------------------------------------------- 字段

def _bad_chars(s):
    """标识符不得含控制字符或不可见格式字符（附件2 §5.1）。"""
    return any(unicodedata.category(c) in ('Cc', 'Cf', 'Cs', 'Zl', 'Zp') for c in s)


def _check_identifier(value, name, max_bytes):
    if not isinstance(value, str):
        raise Reject(400, '%s 必须是字符串' % name)
    b = len(value.encode('utf-8'))
    if b < 1 or b > max_bytes:
        raise Reject(400, '%s 的 UTF-8 长度必须是 1..%d 字节' % (name, max_bytes))
    if _bad_chars(value):
        raise Reject(400, '%s 含控制字符或不可见格式字符' % name)


def _check_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise Reject(400, '%s 必须是 JSON number' % name)
    v = float(value)
    if math.isnan(v) or math.isinf(v):
        raise Reject(400, '%s 必须是有限数值' % name)
    if abs(v) > MAX_COORD:
        raise Reject(400, '%s 绝对值不得超过 %d' % (name, int(MAX_COORD)))
    return v


def _check_channel(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise Reject(400, 'channel 必须是 JSON number')
    v = float(value)
    if math.isnan(v) or math.isinf(v) or v != int(v):
        raise Reject(400, 'channel 必须是整数')          # 1.5 -> 400；1.0 -> 接受
    iv = int(v)
    if not (CHANNEL_MIN <= iv <= CHANNEL_MAX):
        raise Reject(400, 'channel 必须在 %d..%d 范围内' % (CHANNEL_MIN, CHANNEL_MAX))
    return iv


def validate(path, obj, team_id):
    """校验一条请求，返回规范化动作 dict。

    检查顺序：先做会产生 HTTP 400 的结构/类型/范围检查，
    再做返回 200+accepted=false 的未知字段与身份检查。
    以上两类都不占用 request_id（附件2 §5.3）。
    """
    allowed = ACTION_FIELDS if path in ACTION_PATHS else COMMON_FIELDS

    for f in allowed:
        if f not in obj:
            raise Reject(400, '缺少字段 %s' % f)

    if not isinstance(obj['arena_id'], str):
        raise Reject(400, 'arena_id 必须是字符串')
    _check_identifier(obj['robot_id'], 'robot_id', ROBOT_ID_MAX)
    _check_identifier(obj['request_id'], 'request_id', REQUEST_ID_MAX)

    action = {'path': path, 'request_id': obj['request_id']}
    if path in ACTION_PATHS:
        pos = obj['position']
        if not isinstance(pos, dict):
            raise Reject(400, 'position 必须是 JSON 对象')
        for f in POSITION_FIELDS:
            if f not in pos:
                raise Reject(400, '缺少字段 position.%s' % f)
        action['x'] = _check_number(pos['x'], 'position.x')
        action['y'] = _check_number(pos['y'], 'position.y')
        action['channel'] = _check_channel(obj['channel'])
        unknown_pos = [k for k in pos if k not in POSITION_FIELDS]
        if unknown_pos:
            raise Reject(200, 'position 含未声明字段：%s' % ','.join(sorted(unknown_pos)))

    unknown = [k for k in obj if k not in allowed]
    if unknown:
        raise Reject(200, '含未声明字段：%s' % ','.join(sorted(unknown)))

    if obj['arena_id'] != ARENA_ID:
        raise Reject(200, 'arena_id 必须是 "%s"' % ARENA_ID)
    if obj['robot_id'] != team_id:
        raise Reject(200, 'robot_id 与当前登录参赛队号不一致')

    return action


def action_key(action):
    """幂等键对应的动作内容。同 ID 不同内容 -> 409（附件2 §5.3）。"""
    if action['path'] in ACTION_PATHS:
        return (action['path'], repr(action['x']), repr(action['y']), action['channel'])
    return (action['path'],)
