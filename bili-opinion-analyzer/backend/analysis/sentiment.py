# -*- coding: utf-8 -*-
"""SnowNLP 情感分析。"""
import threading

from snownlp import SnowNLP

_score_cache = {}
_lock = threading.Lock()


def score_text(text):
    """返回 0~1 的情感分，越接近 1 越正面。带简单缓存。"""
    text = (text or "").strip()
    if not text:
        return 0.5
    key = text[:60]
    with _lock:
        if key in _score_cache:
            return _score_cache[key]
    try:
        s = SnowNLP(text).sentiments
    except Exception:  # noqa: BLE001
        s = 0.5
    with _lock:
        _score_cache[key] = s
    return s


def classify(score):
    if score >= 0.6:
        return "positive"
    if score <= 0.4:
        return "negative"
    return "neutral"


def analyze(items, text_key="评论内容"):
    """对一批文本打分并分类，返回汇总统计。"""
    pos = neg = neu = 0
    scores = []
    for it in items:
        s = score_text(it.get(text_key, ""))
        scores.append(s)
        c = classify(s)
        if c == "positive":
            pos += 1
        elif c == "negative":
            neg += 1
        else:
            neu += 1
    total = len(items) or 1
    return {
        "positive": pos,
        "negative": neg,
        "neutral": neu,
        "positive_ratio": round(pos / total, 4),
        "negative_ratio": round(neg / total, 4),
        "neutral_ratio": round(neu / total, 4),
        "avg_score": round(sum(scores) / total, 4) if scores else 0,
        "total": len(items),
    }


def top_like_sentiment(items, topn=30):
    """高赞评论的情绪倾向：判断「高赞=认同」还是「群嘲」。"""
    top_level = [it for it in items if it.get("层级") == 1]
    ranked = sorted(top_level, key=lambda x: x.get("点赞数", 0), reverse=True)[:topn]
    if not ranked:
        return {"total": 0, "positive": 0, "negative": 0, "neutral": 0,
                "verdict": "暂无数据", "items": []}

    pos = neg = neu = 0
    out = []
    labels = {"positive": "正面", "negative": "负面", "neutral": "中性"}
    for it in ranked:
        s = score_text(it.get("评论内容", ""))
        c = classify(s)
        if c == "positive":
            pos += 1
        elif c == "negative":
            neg += 1
        else:
            neu += 1
        out.append({
            "user": it.get("用户名", ""),
            "content": it.get("评论内容", ""),
            "like": it.get("点赞数", 0),
            "score": round(s, 4),
            "label": labels[c],
        })

    total = len(ranked)
    if neg / total >= 0.5:
        verdict = "高赞评论以负面为主，疑似「群嘲 / 口碑翻车」"
    elif pos / total >= 0.6:
        verdict = "高赞评论以正面为主，属于「真香 / 广泛认同」"
    else:
        verdict = "高赞评论情绪混合，观点存在分歧"

    return {
        "total": total, "positive": pos, "negative": neg, "neutral": neu,
        "verdict": verdict, "items": out,
    }
