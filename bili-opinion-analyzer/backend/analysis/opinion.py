# -*- coding: utf-8 -*-
"""「夸什么 vs 骂什么」正负面高频词对比。"""
from backend.analysis import sentiment, wordfreq


def opinion_keywords(comments, danmakus=None, topk=30):
    """按情感把文本分成正/负两类，分别提取高频词。"""
    pos_items = []
    neg_items = []
    for it in comments:
        s = sentiment.score_text(it.get("评论内容", ""))
        if s >= 0.6:
            pos_items.append(it)
        elif s <= 0.4:
            neg_items.append(it)
    for it in (danmakus or []):
        s = sentiment.score_text(it.get("弹幕内容", ""))
        if s >= 0.6:
            pos_items.append({"评论内容": it.get("弹幕内容", "")})
        elif s <= 0.4:
            neg_items.append({"评论内容": it.get("弹幕内容", "")})

    return {
        "positive": wordfreq.extract_keywords(pos_items, "评论内容", topk),
        "negative": wordfreq.extract_keywords(neg_items, "评论内容", topk),
        "pos_count": len(pos_items),
        "neg_count": len(neg_items),
    }
