# -*- coding: utf-8 -*-
"""跨视频 PK 榜：口碑 / 热度 / 争议度。"""
from collections import defaultdict

from backend.analysis import sentiment


def video_compare(comments):
    """按视频分组（依赖采集时注入的「视频bvid / 视频标题」字段）。"""
    groups = defaultdict(list)
    for it in comments:
        bvid = it.get("视频bvid") or "未知"
        title = it.get("视频标题") or "未知视频"
        groups[(bvid, title)].append(it)

    rows = []
    for (bvid, title), items in groups.items():
        scores = [sentiment.score_text(it.get("评论内容", "")) for it in items]
        likes = [int(it.get("点赞数", 0) or 0) for it in items]
        pos = sum(1 for s in scores if s >= 0.6)
        neg = sum(1 for s in scores if s <= 0.4)
        n = len(items) or 1
        pos_ratio = pos / n
        neg_ratio = neg / n
        # 争议度：正负情绪占比越接近、且总量越大，越「撕裂」
        controversy = round((1 - abs(pos_ratio - neg_ratio)) * (pos_ratio + neg_ratio), 4)
        rows.append({
            "bvid": bvid,
            "title": title,
            "comment_count": len(items),
            "avg_score": round(sum(scores) / n, 4),
            "positive_ratio": round(pos_ratio, 4),
            "negative_ratio": round(neg_ratio, 4),
            "avg_like": round(sum(likes) / n, 1),
            "controversy": controversy,
        })

    rows.sort(key=lambda x: x["comment_count"], reverse=True)
    return rows
