# -*- coding: utf-8 -*-
"""用户等级分布。"""
from collections import Counter


def level_distribution(comment_items, danmaku_items):
    """评论按 0-6 级统计；弹幕匿名无等级，归入「未知」。"""
    c = Counter()
    for it in comment_items:
        try:
            lv = int(it.get("等级", 0))
        except (ValueError, TypeError):
            lv = 0
        c[max(0, min(6, lv))] += 1

    categories = ["0", "1", "2", "3", "4", "5", "6", "未知"]
    comments = [c[i] for i in range(7)] + [0]
    danmakus = [0] * 7 + [len(danmaku_items)]
    return {"categories": categories, "comments": comments, "danmakus": danmakus}
