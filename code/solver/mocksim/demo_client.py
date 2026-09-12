# -*- coding: utf-8 -*-
"""附件2 §11 的官方示例客户端，改成可指定地址与队号，用来确认联调通了。

  python demo_client.py --base http://127.0.0.1:2026 --robot-id 你的参赛队号

对本地 mock 模拟器和官方模拟器都可以用。只演示 4 类请求的收发，不含查找策略。
"""

import argparse
import json
from urllib.request import Request, urlopen


def make_post(base_url):
    def post(path, payload):
        request = Request(
            base_url + path,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        with urlopen(request, timeout=5) as http_response:
            response = json.loads(http_response.read().decode('utf-8'))
        print(path, response)
        return response
    return post


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default='http://127.0.0.1:2026')
    ap.add_argument('--robot-id', dest='robot_id', default='TEST-TEAM')
    cfg = ap.parse_args()
    post = make_post(cfg.base)

    def base(request_id):
        return {'arena_id': 'default', 'robot_id': cfg.robot_id, 'request_id': request_id}

    def action(request_id, x, y, channel):
        payload = base(request_id)
        payload['position'] = {'x': x, 'y': y}
        payload['channel'] = channel
        return payload

    enter_response = post('/enter', base('enter-1'))
    if enter_response.get('accepted') is not True:
        print('进入失败')
        return
    print('本局可用现实时间：', enter_response['remaining_real_duration_s'], '秒')

    actions = [
        ('/measure', action('measure-1', 300, 400, 1)),
        ('/measure', action('measure-2', 300, 400, 2)),
        ('/clear', action('clear-1', 300, 0, 3)),
        ('/measure', action('measure-3', 300, 0, 2)),
    ]
    for path, payload in actions:
        # 如果因网络故障重试本动作，必须复用这个 payload 及其中的 request_id。
        response = post(path, payload)
        if response.get('accepted') is not True:
            print('请求未执行')
            return
        if path == '/measure':
            if response['measure_result'] == 'direction':
                print('示向度：', response['svd_deg'], '度')
            elif response['measure_result'] == 'near':
                print('距离过近，没有示向度')
            else:
                print('未测得信号')
        else:
            print('清除成功' if response['clear_result'] == 'success' else '清除位置附近没有目标')

    exit_response = post('/exit', base('exit-1'))
    if exit_response.get('accepted') is True:
        print('退出原因：', exit_response['exit_reason'])
    print('虚拟时间应为 199 s，实际 %s s' % exit_response['virtual_time_s'])


if __name__ == '__main__':
    main()
