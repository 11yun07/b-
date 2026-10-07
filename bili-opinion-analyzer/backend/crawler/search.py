# -*- coding: utf-8 -*-
"""搜索模块（带 Cookie）。"""
import logging
import re
import time

from backend import config
from backend.crawler import session_factory, video_info, wbi

logger = logging.getLogger(__name__)

_TAG_RE = re.compile(r"<[^>]+>")


def _clean_title(title):
    return _TAG_RE.sub("", title or "").strip()


def _parse_duration(raw):
    """把 'mm:ss' / 'hh:mm:ss' 转成秒；异常返回 0。"""
    try:
        if isinstance(raw, (int, float)):
            return int(raw)
        parts = [int(x) for x in str(raw).split(":")]
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        return 0
    except (ValueError, TypeError):
        return 0


def search_videos(keyword, order="totalrank", pages=None, page_size=None,
                  cookie=None, delay=None, stop_check=None, progress_cb=None,
                  enrich_cid=True):
    """搜索视频。使用带 Cookie 的 Session；可选通过 view 接口补全 cid。

    返回 list[dict]，字段：bvid/aid/cid/title/author/play/video_review/review/
    pubdate/duration/pic。
    """
    pages = pages or config.DEFAULT_PAGES
    page_size = page_size or config.DEFAULT_PAGE_SIZE
    delay = config.DEFAULT_DELAY if delay is None else delay

    session = session_factory.make_search_session(cookie)
    results = []

    for page in range(1, int(pages) + 1):
        if stop_check and stop_check():
            break
        params = {
            "keyword": keyword,
            "search_type": "video",
            "order": order,
            "page": page,
            "page_size": page_size,
        }
        resp = wbi.get_signed(session, config.SEARCH_URL, params)
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"搜索失败（code={data.get('code')}）：{data.get('message')}")
        result_list = ((data.get("data") or {}).get("result")) or []
        for item in result_list:
            results.append({
                "bvid": item.get("bvid", ""),
                "aid": item.get("aid", 0),
                "cid": 0,
                "title": _clean_title(item.get("title", "")),
                "author": item.get("author", ""),
                "play": item.get("play", 0),
                "video_review": item.get("video_review", 0),
                "review": item.get("review", 0),
                "pubdate": item.get("pubdate", 0),
                "duration": _parse_duration(item.get("duration", "")),
                "pic": item.get("pic", ""),
            })
        if progress_cb:
            progress_cb(page, pages)
        time.sleep(delay)

    # 搜索结果不含 cid，用无 Cookie 的 view 接口补全
    if enrich_cid and results:
        public = session_factory.make_public_session()
        for v in results:
            if stop_check and stop_check():
                break
            try:
                info = video_info.get_video_info(v["bvid"], public)
                if info:
                    v["cid"] = info.get("cid") or v["cid"]
                    v["aid"] = info.get("aid") or v["aid"]
                    v["duration"] = info.get("duration") or v["duration"]
            except Exception as exc:  # noqa: BLE001
                logger.warning("补全 %s 的 cid 失败：%s", v["bvid"], exc)
            time.sleep(0.3)

    return results
