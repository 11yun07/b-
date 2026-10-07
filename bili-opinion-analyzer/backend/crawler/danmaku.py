# -*- coding: utf-8 -*-
"""弹幕采集模块（无 Cookie）。"""
import logging
import math
import time
from datetime import datetime

from backend import config
from backend.crawler import session_factory, wbi
from backend.proto import dm_seg_pb2

logger = logging.getLogger(__name__)


def _fmt(ts):
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError, OSError):
        return ""


def _ms_to_str(ms):
    try:
        s = int(ms) // 1000
        h, rem = divmod(s, 3600)
        m, sec = divmod(rem, 60)
        if h:
            return f"{h:02d}:{m:02d}:{sec:02d}"
        return f"{m:02d}:{sec:02d}"
    except (ValueError, TypeError):
        return "00:00"


def _color_hex(c):
    return f"#{int(c) & 0xFFFFFF:06X}"


def fetch_danmakus(cid, aid, duration=0, delay=None, stop_check=None, progress_cb=None,
                   start_segment=1, checkpoint_cb=None):
    """采集弹幕。返回 list[dict]，由调用方写入缓存区。

    start_segment / checkpoint_cb 用于断点续传。
    注意：本函数只使用无 Cookie 的公共 Session，参数中不出现 cookie。
    """
    delay = config.DEFAULT_DELAY if delay is None else delay
    session = session_factory.make_public_session()
    session.cookies.clear()

    seg_len = config.DANMAKU_SEG_SECONDS
    if duration and int(duration) > 0:
        num_segments = max(1, math.ceil(int(duration) / seg_len))
    else:
        num_segments = 1

    all_rows = []
    seen = set()

    for seg in range(int(start_segment or 1), num_segments + 1):
        if stop_check and stop_check():
            logger.info("弹幕采集收到停止信号")
            break

        params = {
            "type": 1,
            "oid": cid,
            "pid": aid,
            "segment_index": seg,
            "web_location": 1315875,
        }
        resp = wbi.get_signed(session, config.DANMAKU_URL, params)
        raw = resp.content
        if raw:
            try:
                reply = dm_seg_pb2.DmSegMobileReply()
                reply.ParseFromString(raw)
                for e in reply.elems:
                    if e.id in seen:
                        continue
                    seen.add(e.id)
                    all_rows.append({
                        "dmid": e.id,
                        "progress_ms": e.progress,
                        "progress_str": _ms_to_str(e.progress),
                        "mode": e.mode,
                        "fontsize": e.fontsize,
                        "color": _color_hex(e.color),
                        "midHash": e.midHash,
                        "弹幕内容": e.content,
                        "发送时间": _fmt(e.ctime),
                        "ctime_ts": e.ctime,
                    })
            except Exception as exc:  # noqa: BLE001
                logger.warning("解析弹幕段 %s 失败（可能为空或风控）：%s", seg, exc)

        if progress_cb:
            progress_cb(seg, num_segments)
        # 记录断点：下一段；最后一段记 None 表示完成
        if checkpoint_cb:
            checkpoint_cb(seg + 1 if seg < num_segments else None)
        time.sleep(delay)

    return all_rows
