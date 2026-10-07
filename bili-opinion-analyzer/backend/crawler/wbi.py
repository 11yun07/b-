# -*- coding: utf-8 -*-
"""WBI 签名工具。

get_mixin_key() 与 sign() 可直接复用自用户已有代码。
"""
import hashlib
import logging
import time
from urllib.parse import urlencode

from backend import config
from backend.crawler import session_factory

logger = logging.getLogger(__name__)

# B 站 WBI 混排密钥表
MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52,
]


def get_mixin_key(orig):
    """按混排表重排字符串并取前 32 位作为 mixin key。"""
    return "".join(orig[i] for i in MIXIN_KEY_ENC_TAB)[:32]


def _key_from_url(url):
    return (url or "").rsplit("/", 1)[-1].split(".")[0]


class _WbiKeys:
    """wbi_img 密钥缓存，避免每次请求都调 nav 接口。"""

    def __init__(self):
        self.img_key = None
        self.sub_key = None
        self.expire_at = 0.0

    def get(self, session=None):
        if self.img_key and self.sub_key and time.time() < self.expire_at:
            return self.img_key, self.sub_key
        session = session or session_factory.make_public_session()
        resp = session.get(config.NAV_URL, timeout=10)
        data = resp.json()
        wbi_img = (data.get("data") or {}).get("wbi_img") or {}
        self.img_key = _key_from_url(wbi_img.get("img_url", ""))
        self.sub_key = _key_from_url(wbi_img.get("sub_url", ""))
        self.expire_at = time.time() + 6 * 3600
        return self.img_key, self.sub_key


_wbi_keys = _WbiKeys()


def sign(params, session=None):
    """为参数字典追加 wts 与 w_rid 并返回新字典（不修改入参）。"""
    img_key, sub_key = _wbi_keys.get(session)
    mixin_key = get_mixin_key(img_key + sub_key)
    p = dict(params)
    p["wts"] = int(time.time())
    p = dict(sorted(p.items()))
    # B 站规则：编码后去除 !'()* 五个字符再拼接 mixin_key 计算 md5
    query = urlencode(p)
    query = "".join(ch for ch in query if ch not in "!'()*")
    p["w_rid"] = hashlib.md5((query + mixin_key).encode("utf-8")).hexdigest()
    return p


def get_signed(session, url, params, cooldown=None, max_retries=None, timeout=15):
    """签名 + GET，遇到 412 自动冷却重试，返回 Response。"""
    cooldown = config.COOLDOWN_412 if cooldown is None else cooldown
    max_retries = config.MAX_RETRIES if max_retries is None else max_retries
    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            signed = sign(params, session)
            resp = session.get(url, params=signed, timeout=timeout)
            if resp.status_code == 412:
                last_exc = RuntimeError("HTTP 412 触发风控")
                logger.warning("412 触发，冷却 %ss 后重试（%s/%s）", cooldown, attempt + 1, max_retries)
                time.sleep(cooldown)
                continue
            return resp
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt < max_retries:
                time.sleep(1.0 + attempt)
                continue
    raise last_exc
