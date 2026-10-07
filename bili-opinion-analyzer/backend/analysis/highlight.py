# -*- coding: utf-8 -*-
"""弹幕「名场面 / 高能时刻」定位。"""
from collections import Counter, defaultdict


def _ms_label(ms):
    s = int(ms) // 1000
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h:02d}:{m:02d}:{sec:02d}"
    return f"{m:02d}:{sec:02d}"


def danmaku_highlights(items, window_seconds=30, topn=8):
    """按时间窗统计弹幕密度，返回峰值片段列表。"""
    if not items:
        return []
    buckets = defaultdict(list)
    for it in items:
        try:
            ms = int(it.get("progress_ms", 0))
        except (ValueError, TypeError):
            ms = 0
        buckets[ms // (window_seconds * 1000)].append(it)

    ranked = sorted(buckets.items(), key=lambda kv: len(kv[1]), reverse=True)[:topn]
    result = []
    for b, group in ranked:
        counter = Counter(it.get("弹幕内容", "") for it in group if it.get("弹幕内容"))
        samples = [c for c, _ in counter.most_common(3)]
        result.append({
            "start_ms": b * window_seconds * 1000,
            "end_ms": (b + 1) * window_seconds * 1000,
            "start": _ms_label(b * window_seconds * 1000),
            "end": _ms_label((b + 1) * window_seconds * 1000),
            "count": len(group),
            "samples": samples,
        })
    return result
