# -*- coding: utf-8 -*-
"""评论采集模块（无 Cookie）。"""
import logging
import time
from datetime import datetime

from backend import config
from backend.crawler import session_factory, wbi

logger = logging.getLogger(__name__)


def _fmt(ts):
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError, OSError):
        return ""


def _sex(s):
    return {"男": "男", "女": "女", "保密": "保密"}.get(s, "未知")


def _vip_status(member):
    vip = member.get("vip") or {}
    if vip.get("status") == 1:
        return (vip.get("label") or {}).get("text") or "大会员"
    return "普通用户"


def _flatten_rich(reply, parent_rpid=0, level=1, reply_to=""):
    """递归展开评论与楼中楼，返回 list[dict]。"""
    rows = []
    member = reply.get("member") or {}
    content = reply.get("content") or {}

    level_info = member.get("level_info") or {}
    try:
        current_level = int(level_info.get("current_level", member.get("level", 0)))
    except (ValueError, TypeError):
        current_level = 0

    # IP 属地：优先 member.ip_location，其次 reply_control.location
    region = member.get("ip_location") or ""
    if not region:
        region = (reply.get("reply_control") or {}).get("location") or ""
    # 去掉可能的 "IP属地：" 前缀
    if region:
        region = (region.replace("IP属地：", "").replace("IP属地:", "")
                      .replace("IP:", "").strip())

    rows.append({
        "rpid": reply.get("rpid", 0),
        "parent_rpid": parent_rpid,
        "层级": level,
        "回复给": reply_to,
        "user_mid": member.get("mid", 0),
        "用户名": member.get("uname", ""),
        "等级": current_level,
        "会员状态": _vip_status(member),
        "性别": _sex(member.get("sex", "")),
        "评论时间": _fmt(reply.get("ctime", 0)),
        "ctime_ts": reply.get("ctime", 0),
        "地区": region,
        "评论内容": content.get("message", ""),
        "点赞数": reply.get("like", 0),
        "回复数": reply.get("rcount", 0),
        "图片": [p.get("img_src", "") for p in (content.get("pictures") or [])],
    })

    for sub in (reply.get("replies") or []):
        rows.extend(_flatten_rich(
            sub,
            parent_rpid=rows[-1]["rpid"],
            level=level + 1,
            reply_to=rows[-1]["用户名"],
        ))
    return rows


def _fetch_via_mobile(oid, mode, max_count, delay, stop_check, progress_cb,
                      start_next=0, checkpoint_cb=None):
    """移动端接口：可取 IP 属地。start_next / checkpoint_cb 用于断点续传。"""
    session = session_factory.make_public_session(mobile=True)
    session.cookies.clear()
    all_rows = []
    next_page = int(start_next or 0)
    while True:
        if stop_check and stop_check():
            logger.info("评论采集收到停止信号")
            break
        params = {"type": 1, "oid": oid, "mode": mode, "plat": 1, "next": next_page, "ps": 20}
        resp = wbi.get_signed(session, config.COMMENT_URL_MOBILE, params)
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"移动端评论采集失败（code={data.get('code')}）：{data.get('message')}")
        payload = data.get("data") or {}
        replies = payload.get("replies") or []
        for r in replies:
            all_rows.extend(_flatten_rich(r))
            if max_count and len(all_rows) >= max_count:
                if checkpoint_cb:
                    checkpoint_cb(None)
                return all_rows[:max_count]
        cursor = payload.get("cursor") or {}
        if progress_cb:
            progress_cb(len(all_rows), cursor.get("all_count") or len(all_rows))
        if cursor.get("is_end"):
            if checkpoint_cb:
                checkpoint_cb(None)
            break
        nxt = cursor.get("next")
        if not nxt:
            if checkpoint_cb:
                checkpoint_cb(None)
            break
        next_page = int(nxt)
        if checkpoint_cb:
            checkpoint_cb(next_page)
        time.sleep(delay)
    return all_rows[:max_count] if max_count else all_rows


def _fetch_via_web(oid, mode, max_count, delay, stop_check, progress_cb):
    """网页版接口：无 IP 属地，但更稳（回退用）。"""
    session = session_factory.make_public_session(mobile=False)
    session.cookies.clear()
    all_rows = []
    pagination_str = ""
    while True:
        if stop_check and stop_check():
            logger.info("评论采集收到停止信号")
            break
        params = {"type": 1, "oid": oid, "mode": mode, "plat": 1, "web_location": 1315875}
        if pagination_str:
            params["pagination_str"] = pagination_str
        resp = wbi.get_signed(session, config.COMMENT_URL_WEB, params)
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"网页版评论采集失败（code={data.get('code')}）：{data.get('message')}")
        payload = data.get("data") or {}
        replies = payload.get("replies") or []
        for r in replies:
            all_rows.extend(_flatten_rich(r))
            if max_count and len(all_rows) >= max_count:
                return all_rows[:max_count]
        cursor = payload.get("cursor") or {}
        if progress_cb:
            progress_cb(len(all_rows), cursor.get("all_count") or len(all_rows))
        if cursor.get("is_end"):
            break
        next_offset = (cursor.get("pagination_reply") or {}).get("next_offset", "")
        if not next_offset and cursor.get("next"):
            next_offset = str(cursor.get("next"))
        if not next_offset:
            break
        pagination_str = next_offset
        time.sleep(delay)
    return all_rows[:max_count] if max_count else all_rows


def fetch_comments(oid, mode=3, max_count=0, delay=None, stop_check=None, progress_cb=None,
                   start_next=0, checkpoint_cb=None):
    """采集视频评论（oid=aid）。优先移动端接口（可取 IP 属地），失败自动回退网页版。

    start_next / checkpoint_cb 用于断点续传（仅移动端主路径）。
    注意：本函数只使用无 Cookie 的公共 Session，参数中不出现 cookie。
    """
    delay = config.DEFAULT_DELAY if delay is None else delay
    try:
        return _fetch_via_mobile(oid, mode, max_count, delay, stop_check, progress_cb,
                                 start_next, checkpoint_cb)
    except Exception as exc:  # noqa: BLE001
        logger.warning("移动端评论接口失败（%s），回退网页版接口", exc)
        return _fetch_via_web(oid, mode, max_count, delay, stop_check, progress_cb)
