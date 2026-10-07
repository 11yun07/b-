# -*- coding: utf-8 -*-
"""jieba 分词 + 停用词过滤 + TF-IDF 词频统计。"""
import logging

import jieba.analyse

logger = logging.getLogger(__name__)

_STOPWORDS = set(
    """
    的 了 和 是 就 都 而 及 与 着 或 一个 没有 我们 你们 他们 她们 它们 这个 那个 这些 那些
    自己 什么 怎么 为什么 因为 所以 但是 如果 然后 就是 不是 也是 还是 可以 可能 已经 现在
    知道 觉得 感觉 真的 有点 一下 这种 那种 时候 大家 评论 弹幕 视频 一个 一直 一起 一样
    没有 不要 不能 不会 东西 事情 问题 地方 方面 这样 那样 还是 就是 但是 而且 或者 还有
    以及 等等 哈哈哈 哈哈 呜呜 卧槽 牛逼 牛批 绝了 真的 假的 真的假的 好家伙 离谱 确实
    up主 up 主 bilibili 哔哩哔哩 B站 b站
    """.split()
)

# jieba 默认词典内置的常用停用词也一起过滤
try:
    from jieba.analyse import default_tfidf
    if hasattr(default_tfidf, "stop_words"):
        _STOPWORDS.update(default_tfidf.stop_words)
except Exception:  # noqa: BLE001
    pass


def extract_keywords(items, text_key="评论内容", topk=100):
    """返回 Top 词及权重：[{'name': str, 'value': float}, ...]。"""
    text = "\n".join(str(it.get(text_key, "")) for it in items if it.get(text_key))
    if not text.strip():
        return []
    try:
        tags = jieba.analyse.extract_tags(text, topK=topk, withWeight=True)
    except Exception as exc:  # noqa: BLE001
        logger.warning("jieba 分词失败：%s", exc)
        return []
    result = []
    for word, weight in tags:
        if word in _STOPWORDS or len(word) < 2:
            continue
        result.append({"name": word, "value": round(float(weight), 6)})
        if len(result) >= topk:
            break
    return result
