# -*- coding: utf-8 -*-
"""Cookie 隔离核心。

- make_search_session(cookie_str)：带 Cookie，仅用于「搜索视频」。
- make_public_session(mobile=False)：无 Cookie，仅用于「评论 / 弹幕」采集。

采集函数（comment.py / danmaku.py）的参数列表中绝不出现 cookie，
从物理上杜绝 Cookie 泄漏到评论、弹幕采集请求中。
"""
import logging

import requests

from backend import config

logger = logging.getLogger(__name__)


def _base_session(mobile=False):
    s = requests.Session()
    ua = config.MOBILE_USER_AGENT if mobile else config.USER_AGENT
    s.headers.update({
        "User-Agent": ua,
        "Referer": config.REFERER,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
    })
    return s


def make_public_session(mobile=False):
    """返回一个显式清空 Cookie 的全新 Session，用于评论 / 弹幕采集。

    评论采集需传 mobile=True，用移动端 UA 才能取到 IP 属地。
    """
    s = _base_session(mobile=mobile)
    s.cookies.clear()
    logger.debug("创建无 Cookie 公共 Session（mobile=%s）", mobile)
    return s


def make_search_session(cookie_str=None):
    """返回携带用户 Cookie 的 Session，仅用于搜索视频。"""
    s = _base_session()
    s.cookies.clear()
    if cookie_str:
        for pair in (cookie_str or "").split(";"):
            pair = pair.strip()
            if not pair or "=" not in pair:
                continue
            k, _, v = pair.partition("=")
            s.cookies.set(k.strip(), v.strip(), domain=".bilibili.com")
    return s
