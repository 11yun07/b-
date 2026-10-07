# -*- coding: utf-8 -*-
"""观点聚类：jieba 分词 + TF-IDF + 纯 Python KMeans（无重依赖）。"""
import math
import random
from collections import Counter

import jieba

from backend.analysis import wordfreq


def _tokenize(text):
    words = []
    for w in jieba.cut(text or ""):
        w = w.strip()
        if len(w) >= 2 and w not in wordfreq._STOPWORDS:
            words.append(w)
    return words


def cluster_opinions(items, text_key="评论内容", k=None, max_docs=1500, max_vocab=300):
    """对文本做 TF-IDF + KMeans 聚类，返回观点簇。"""
    docs = [str(it.get(text_key, "")).strip() for it in items
            if str(it.get(text_key, "")).strip()]
    if not docs:
        return {"k": 0, "clusters": []}

    if len(docs) > max_docs:
        random.seed(42)
        docs = random.sample(docs, max_docs)

    # 词表：按文档频率取 top 词
    df = Counter()
    tokenized = []
    for d in docs:
        toks = set(_tokenize(d))
        tokenized.append(toks)
        for t in toks:
            df[t] += 1
    vocab = [w for w, _ in df.most_common(max_vocab)]
    vocab_idx = {w: i for i, w in enumerate(vocab)}

    n = len(docs)
    idf = {w: math.log((1 + n) / (1 + df[w])) + 1.0 for w in vocab}
    vectors = []
    for toks in tokenized:
        tf = Counter(toks)
        vec = {}
        norm = 0.0
        for w in toks:
            if w in vocab_idx:
                weight = (1 + math.log(tf[w])) * idf[w]
                vec[vocab_idx[w]] = weight
                norm += weight * weight
        norm = math.sqrt(norm) or 1.0
        vectors.append({i: w / norm for i, w in vec.items()})

    if k is None:
        k = min(6, max(3, int(math.sqrt(n / 2))))
    k = max(1, min(k, n))

    random.seed(42)
    centroid_ids = random.sample(range(n), k)
    centroids = [dict(vectors[i]) for i in centroid_ids]

    assign = [0] * n
    for _ in range(20):
        changed = False
        for i, v in enumerate(vectors):
            best, best_sim = 0, -1.0
            for c in range(k):
                sim = sum(w * centroids[c].get(j, 0.0) for j, w in v.items())
                if sim > best_sim:
                    best_sim, best = sim, c
            if assign[i] != best:
                assign[i] = best
                changed = True
        if not changed:
            break
        sums = [{} for _ in range(k)]
        counts = [0] * k
        for i, v in enumerate(vectors):
            c = assign[i]
            counts[c] += 1
            for j, w in v.items():
                sums[c][j] = sums[c].get(j, 0.0) + w
        for c in range(k):
            cnt = counts[c] or 1
            norm = math.sqrt(sum(w * w for w in sums[c].values())) or 1.0
            centroids[c] = {j: w / norm for j, w in sums[c].items()}

    clusters = []
    for c in range(k):
        member_idx = [i for i in range(n) if assign[i] == c]
        if not member_idx:
            continue
        size = len(member_idx)
        top_words = sorted(centroids[c].items(), key=lambda x: -x[1])[:8]
        keywords = [vocab[j] for j, _ in top_words]
        dists = []
        for i in member_idx:
            sim = sum(w * centroids[c].get(j, 0.0) for j, w in vectors[i].items())
            dists.append((sim, i))
        dists.sort(reverse=True)
        samples = [docs[i] for _, i in dists[:3]]
        clusters.append({
            "id": c + 1,
            "size": size,
            "ratio": round(size / n, 4),
            "keywords": keywords,
            "samples": samples,
        })
    clusters.sort(key=lambda x: -x["size"])
    return {"k": len(clusters), "clusters": clusters}
