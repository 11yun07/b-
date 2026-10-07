# -*- coding: utf-8 -*-
"""时间趋势与弹幕时间轴。"""
from collections import defaultdict
from datetime import datetime

from backend.analysis import sentiment


def _bucket(ts, granularity):
    try:
        dt = datetime.fromtimestamp(int(ts))
    except (ValueError, TypeError, OSError):
        return None
    if granularity == "hour":
        return dt.strftime("%Y-%m-%d %H:00")
    if granularity == "month":
        return dt.strftime("%Y-%m")
    return dt.strftime("%Y-%m-%d")


def comment_timeline(items, granularity="day", text_key="评论内容"):
    """按小时 / 天聚合评论数量，并计算情感均值随时间变化。"""
    buckets = defaultdict(list)
    for it in items:
        ts = it.get("ctime_ts")
        b = _bucket(ts, granularity)
        if not b:
            continue
        buckets[b].append(it)

    result = []
    for key in sorted(buckets):
        group = buckets[key]
        scores = [sentiment.score_text(it.get(text_key, "")) for it in group]
        result.append({
            "time": key,
            "count": len(group),
            "avg_score": round(sum(scores) / len(scores), 4) if scores else 0,
        })
    return result


def _ms_label(ms):
    s = int(ms) // 1000
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h:02d}:{m:02d}:{sec:02d}"
    return f"{m:02d}:{sec:02d}"


def danmaku_timeline(items, bucket_seconds=10):
    """按视频内进度分桶统计弹幕密度。"""
    buckets = defaultdict(int)
    for it in items:
        try:
            ms = int(it.get("progress_ms", 0))
        except (ValueError, TypeError):
            ms = 0
        buckets[ms // (bucket_seconds * 1000)] += 1

    result = []
    for b in sorted(buckets):
        result.append({
            "time_ms": b * bucket_seconds * 1000,
            "label": _ms_label(b * bucket_seconds * 1000),
            "count": buckets[b],
        })
    return result


def danmaku_heatmap(items, bucket_minutes=1):
    """弹幕热力图：X=视频内时间(分钟)，Y=发送日期，value=条数。"""
    x_buckets = defaultdict(int)
    y_dates = set()
    cells = defaultdict(int)
    for it in items:
        try:
            ms = int(it.get("progress_ms", 0))
            ts = int(it.get("ctime_ts", 0))
        except (ValueError, TypeError):
            continue
        x = ms // (bucket_minutes * 60 * 1000)
        try:
            y = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
        except (ValueError, OSError):
            continue
        x_buckets[x] += 1
        y_dates.add(y)
        cells[(x, y)] += 1

    if not cells:
        return {"x": [], "y": [], "data": []}

    xs = sorted(x_buckets)
    ys = sorted(y_dates)
    x_idx = {v: i for i, v in enumerate(xs)}
    y_idx = {v: i for i, v in enumerate(ys)}
    x_labels = [f"{v * bucket_minutes}-{(v + 1) * bucket_minutes}分" for v in xs]
    data = [[x_idx[x], y_idx[y], cnt] for (x, y), cnt in cells.items()]
    return {"x": x_labels, "y": ys, "data": data}


def danmaku_sentiment_timeline(items, bucket_seconds=30):
    """弹幕密度 × 情感均值叠加（视频内时间轴）。"""
    buckets = defaultdict(list)
    for it in items:
        try:
            ms = int(it.get("progress_ms", 0))
        except (ValueError, TypeError):
            ms = 0
        buckets[ms // (bucket_seconds * 1000)].append(it)

    result = []
    for b in sorted(buckets):
        group = buckets[b]
        scores = [sentiment.score_text(it.get("弹幕内容", "")) for it in group]
        result.append({
            "time_ms": b * bucket_seconds * 1000,
            "label": _ms_label(b * bucket_seconds * 1000),
            "count": len(group),
            "avg_score": round(sum(scores) / len(scores), 4) if scores else 0,
        })
    return result
