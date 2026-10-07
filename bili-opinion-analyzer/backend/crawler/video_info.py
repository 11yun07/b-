# -*- coding: utf-8 -*-
"""通过 view 接口获取视频 cid / aid / 时长（无 Cookie）。"""
import logging
import re

from backend import config
from backend.crawler import session_factory

logger = logging.getLogger(__name__)

_BVID_RE = re.compile(r"BV[0-9A-Za-z]{10}")


def extract_bvid(text):
    """从任意文本中提取首个 BV 号。"""
    m = _BVID_RE.search(text or "")
    return m.group(0) if m else None


def get_video_info(bvid, session=None):
    """获取视频基础信息，返回 {bvid, aid, cid, duration, title}。"""
    if not bvid:
        return None
    session = session or session_factory.make_public_session()
    try:
        resp = session.get(config.VIEW_URL, params={"bvid": bvid}, timeout=15)
        data = resp.json()
        if data.get("code") != 0:
            logger.warning("获取 %s 信息失败：%s", bvid, data.get("message"))
            return None
        d = data.get("data") or {}
        return {
            "bvid": bvid,
            "aid": d.get("aid"),
            "cid": d.get("cid"),
            "duration": d.get("duration"),
            "title": d.get("title"),
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("获取 %s 信息异常：%s", bvid, exc)
        return None
