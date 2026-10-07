# -*- coding: utf-8 -*-
"""Flask 后端入口。

运行：python backend/app.py  （浏览器打开 http://127.0.0.1:5000）
"""
import copy
import logging
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify, request, send_file, send_from_directory

from backend import config
from backend.analysis import cluster as cluster_mod
from backend.analysis import compare as compare_mod
from backend.analysis import highlight as highlight_mod
from backend.analysis import level as level_mod
from backend.analysis import opinion as opinion_mod
from backend.analysis import sentiment as sentiment_mod
from backend.analysis import timeline as timeline_mod
from backend.analysis import wordfreq as wordfreq_mod
from backend.crawler import comment as comment_mod
from backend.crawler import danmaku as danmaku_mod
from backend.crawler import search as search_mod
from backend.crawler import video_info
from backend.storage import cache
from backend.storage import export as export_mod

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("app")

app = Flask(__name__, static_folder=config.FRONTEND_DIR, static_url_path="")


@app.after_request
def _cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return resp


# --------------------------------------------------------------------------- #
# 采集任务管理器
# --------------------------------------------------------------------------- #
class CrawlManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._stop = {"comment": False, "danmaku": False}
        self._status = {
            "comment": self._new_status("评论空闲"),
            "danmaku": self._new_status("弹幕空闲"),
        }
        # 断点续传：{kind: {bvid: 游标}}
        self._checkpoint = {"comment": {}, "danmaku": {}}

    @staticmethod
    def _new_status(message):
        return {"running": False, "done": 0, "total": 0, "count": 0, "message": message}

    def start(self, kind):
        with self._lock:
            self._stop[kind] = False
            st = self._status[kind]
            st["running"] = True
            st["done"] = 0
            st["count"] = 0
            st["message"] = "采集中…"

    def finish(self, kind, message="完成"):
        with self._lock:
            self._status[kind]["running"] = False
            self._status[kind]["message"] = message

    def request_stop(self, kind=None):
        with self._lock:
            if kind in ("comment", "danmaku"):
                self._stop[kind] = True
            else:
                self._stop["comment"] = True
                self._stop["danmaku"] = True

    def set_checkpoint(self, kind, key, value):
        with self._lock:
            if value is None:
                self._checkpoint[kind].pop(key, None)
            else:
                self._checkpoint[kind][key] = value

    def get_checkpoint(self, kind, key, default=None):
        with self._lock:
            return self._checkpoint[kind].get(key, default)

    def is_stopped(self, kind):
        with self._lock:
            return self._stop[kind]

    def is_running(self, kind):
        with self._lock:
            return self._status[kind]["running"]

    def update(self, kind, done=None, total=None, count=None, message=None):
        with self._lock:
            st = self._status[kind]
            if done is not None:
                st["done"] = done
            if total is not None:
                st["total"] = total
            if count is not None:
                st["count"] = count
            if message is not None:
                st["message"] = message

    def get(self):
        with self._lock:
            return copy.deepcopy(self._status)


mgr = CrawlManager()


# --------------------------------------------------------------------------- #
# 采集后台任务
# --------------------------------------------------------------------------- #
def _crawl_comments_job(videos, mode, max_count, delay):
    total_videos = len(videos)
    mgr.start("comment")
    mgr.update("comment", total=total_videos, done=0, count=0)
    for i, v in enumerate(videos):
        if mgr.is_stopped("comment"):
            break
        oid = v.get("aid")
        if not oid and v.get("bvid"):
            info = video_info.get_video_info(v["bvid"])
            oid = (info or {}).get("aid")
        if not oid:
            mgr.update("comment", done=i + 1)
            continue
        title = (v.get("title") or "")[:24]
        mgr.update("comment", message=f"正在采集：{title}")

        def _prog(page, total):
            mgr.update("comment", message=f"正在采集：{title}（{page}/{total}）")
            mgr.update("comment", count=page)

        bvid = v.get("bvid", "")
        start_next = mgr.get_checkpoint("comment", bvid, 0)
        if start_next:
            mgr.update("comment", message=f"断点续传：{title}（第 {start_next} 页起）")

        def _cp(nxt):
            mgr.set_checkpoint("comment", bvid, nxt)

        try:
            rows = comment_mod.fetch_comments(
                oid, mode=mode, max_count=max_count, delay=delay,
                stop_check=lambda: mgr.is_stopped("comment"),
                progress_cb=_prog,
                start_next=start_next,
                checkpoint_cb=_cp,
            )
            # 注入视频归属，供「跨视频 PK 榜」使用
            for r in rows:
                r["视频bvid"] = bvid
                r["视频标题"] = v.get("title", "")
            added = cache.comment_cache.add(rows)
            logger.info("评论采集完成：%s 条（新增 %s）", len(rows), added)
        except Exception as exc:  # noqa: BLE001
            logger.exception("评论采集异常")
            mgr.update("comment", message=f"错误：{exc}")
        mgr.update("comment", done=i + 1, count=cache.comment_cache.count())

    mgr.finish("comment", "已停止" if mgr.is_stopped("comment") else "完成")


def _crawl_danmaku_job(videos, delay):
    total_videos = len(videos)
    mgr.start("danmaku")
    mgr.update("danmaku", total=total_videos, done=0, count=0)
    for i, v in enumerate(videos):
        if mgr.is_stopped("danmaku"):
            break
        bvid = v.get("bvid")
        info = video_info.get_video_info(bvid) if bvid else None
        cid = (info or {}).get("cid") or v.get("cid")
        aid = (info or {}).get("aid") or v.get("aid")
        duration = (info or {}).get("duration") or v.get("duration") or 0
        if not cid:
            mgr.update("danmaku", message=f"跳过（无 cid）：{(v.get('title') or '')[:24]}")
            mgr.update("danmaku", done=i + 1)
            continue
        title = (v.get("title") or "")[:24]

        def _prog(seg, total):
            mgr.update("danmaku", message=f"正在采集：{title}（段 {seg}/{total}）")

        start_segment = mgr.get_checkpoint("danmaku", bvid, 1)
        if start_segment and start_segment > 1:
            mgr.update("danmaku", message=f"断点续传：{title}（第 {start_segment} 段起）")

        def _cp(seg):
            mgr.set_checkpoint("danmaku", bvid, seg)

        try:
            rows = danmaku_mod.fetch_danmakus(
                cid, aid, duration, delay=delay,
                stop_check=lambda: mgr.is_stopped("danmaku"),
                progress_cb=_prog,
                start_segment=start_segment,
                checkpoint_cb=_cp,
            )
            # 注入视频归属，供「跨视频 PK 榜」使用
            for r in rows:
                r["视频bvid"] = bvid
                r["视频标题"] = v.get("title", "")
            added = cache.danmaku_cache.add(rows)
            logger.info("弹幕采集完成：%s 条（新增 %s）", len(rows), added)
        except Exception as exc:  # noqa: BLE001
            logger.exception("弹幕采集异常")
            mgr.update("danmaku", message=f"错误：{exc}")
        mgr.update("danmaku", done=i + 1, count=cache.danmaku_cache.count())

    mgr.finish("danmaku", "已停止" if mgr.is_stopped("danmaku") else "完成")


# --------------------------------------------------------------------------- #
# 页面
# --------------------------------------------------------------------------- #
@app.route("/")
def index():
    return send_from_directory(config.FRONTEND_DIR, "index.html")


# --------------------------------------------------------------------------- #
# 搜索
# --------------------------------------------------------------------------- #
@app.route("/api/search", methods=["POST"])
def api_search():
    data = request.get_json(force=True, silent=True) or {}
    keyword = (data.get("keyword") or "").strip()
    if not keyword:
        return jsonify({"error": "关键词不能为空"}), 400
    order = data.get("order") or "totalrank"
    pages = int(data.get("pages") or config.DEFAULT_PAGES)
    cookie = data.get("cookie") or ""
    try:
        videos = search_mod.search_videos(
            keyword, order=order, pages=pages, cookie=cookie,
        )
        return jsonify({"videos": videos, "total": len(videos)})
    except Exception as exc:  # noqa: BLE001
        logger.exception("搜索异常")
        return jsonify({"error": str(exc)}), 500


# --------------------------------------------------------------------------- #
# 采集控制
# --------------------------------------------------------------------------- #
@app.route("/api/crawl/comments", methods=["POST"])
def api_crawl_comments():
    data = request.get_json(force=True, silent=True) or {}
    videos = data.get("videos") or []
    if not videos:
        return jsonify({"error": "请先选择视频"}), 400
    if mgr.is_running("comment"):
        return jsonify({"error": "评论采集已在进行中"}), 409
    mode = int(data.get("mode") or 3)
    max_count = int(data.get("max_count") or 0)
    delay = float(data.get("delay") or config.DEFAULT_DELAY)
    threading.Thread(
        target=_crawl_comments_job, args=(videos, mode, max_count, delay), daemon=True
    ).start()
    return jsonify({"ok": True})


@app.route("/api/crawl/danmakus", methods=["POST"])
def api_crawl_danmakus():
    data = request.get_json(force=True, silent=True) or {}
    videos = data.get("videos") or []
    if not videos:
        return jsonify({"error": "请先选择视频"}), 400
    if mgr.is_running("danmaku"):
        return jsonify({"error": "弹幕采集已在进行中"}), 409
    delay = float(data.get("delay") or config.DEFAULT_DELAY)
    threading.Thread(target=_crawl_danmaku_job, args=(videos, delay), daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/crawl/status")
def api_crawl_status():
    st = mgr.get()
    return jsonify({
        "comment": st["comment"],
        "danmaku": st["danmaku"],
        "cache": {
            "comment": cache.comment_cache.count(),
            "danmaku": cache.danmaku_cache.count(),
        },
    })


@app.route("/api/crawl/stop", methods=["POST"])
def api_crawl_stop():
    data = request.get_json(force=True, silent=True) or {}
    kind = data.get("type")
    mgr.request_stop(kind if kind in ("comment", "danmaku") else None)
    return jsonify({"ok": True})


# --------------------------------------------------------------------------- #
# 缓存区
# --------------------------------------------------------------------------- #
@app.route("/api/cache/preview")
def api_cache_preview():
    return jsonify({
        "comment": cache.comment_cache.snapshot(100),
        "danmaku": cache.danmaku_cache.snapshot(100),
    })


@app.route("/api/cache/clear", methods=["POST"])
def api_cache_clear():
    data = request.get_json(force=True, silent=True) or {}
    kind = data.get("type")
    if kind == "comment":
        cache.comment_cache.clear()
    elif kind == "danmaku":
        cache.danmaku_cache.clear()
    else:
        cache.comment_cache.clear()
        cache.danmaku_cache.clear()
    return jsonify({"ok": True})


@app.route("/api/export", methods=["POST"])
def api_export():
    data = request.get_json(force=True, silent=True) or {}
    fmt = (data.get("format") or "csv").lower()
    kind = data.get("type") or "comment"
    rows = cache.comment_cache.all() if kind == "comment" else cache.danmaku_cache.all()
    if not rows:
        return jsonify({"error": "没有可导出的数据"}), 400
    db_kind = "comments" if kind == "comment" else "danmakus"
    try:
        if fmt == "csv":
            path = export_mod.to_csv(rows, db_kind)
        elif fmt == "json":
            path = export_mod.to_json(rows, db_kind)
        elif fmt == "sqlite":
            path = export_mod.to_sqlite(rows, db_kind)
        else:
            return jsonify({"error": "不支持的格式"}), 400
        return jsonify({"ok": True, "path": path, "count": len(rows)})
    except Exception as exc:  # noqa: BLE001
        logger.exception("导出失败")
        return jsonify({"error": str(exc)}), 500


# --------------------------------------------------------------------------- #
# 分析接口
# --------------------------------------------------------------------------- #
@app.route("/api/analysis/sentiment")
def api_sentiment():
    comments = cache.comment_cache.all()
    danmakus = cache.danmaku_cache.all()
    c = sentiment_mod.analyze(comments, "评论内容")
    d = sentiment_mod.analyze(danmakus, "弹幕内容")
    distribution = {
        "positive": c["positive"] + d["positive"],
        "negative": c["negative"] + d["negative"],
        "neutral": c["neutral"] + d["neutral"],
        "total": c["total"] + d["total"],
        "comment": c,
        "danmaku": d,
    }
    trend = timeline_mod.comment_timeline(comments, "day", "评论内容")
    return jsonify({"distribution": distribution, "trend": trend})


@app.route("/api/analysis/wordfreq")
def api_wordfreq():
    return jsonify({
        "comment": wordfreq_mod.extract_keywords(cache.comment_cache.all(), "评论内容"),
        "danmaku": wordfreq_mod.extract_keywords(cache.danmaku_cache.all(), "弹幕内容"),
    })


@app.route("/api/analysis/level")
def api_level():
    return jsonify(level_mod.level_distribution(
        cache.comment_cache.all(), cache.danmaku_cache.all()
    ))


@app.route("/api/analysis/timeline")
def api_timeline():
    granularity = request.args.get("granularity", "day")
    return jsonify(timeline_mod.comment_timeline(
        cache.comment_cache.all(), granularity, "评论内容"
    ))


@app.route("/api/analysis/danmaku_timeline")
def api_danmaku_timeline():
    items = cache.danmaku_cache.all()
    return jsonify({
        "buckets": timeline_mod.danmaku_timeline(items, 10),
        "heatmap": timeline_mod.danmaku_heatmap(items, 1),
    })


@app.route("/api/analysis/interaction")
def api_interaction():
    items = cache.comment_cache.all()
    top_level = [it for it in items if it.get("层级") == 1]
    scatter = [
        {
            "like": it.get("点赞数", 0),
            "reply": it.get("回复数", 0),
            "name": (it.get("用户名") or "")[:12],
        }
        for it in top_level
    ]
    top10 = sorted(top_level, key=lambda x: x.get("点赞数", 0), reverse=True)[:10]
    top10_out = [
        {
            "user": it.get("用户名", ""),
            "content": it.get("评论内容", ""),
            "like": it.get("点赞数", 0),
            "reply": it.get("回复数", 0),
            "level": it.get("等级", 0),
            "region": it.get("地区", ""),
            "time": it.get("评论时间", ""),
        }
        for it in top10
    ]
    return jsonify({"scatter": scatter, "top10": top10_out})


# --------------------------------------------------------------------------- #
# 扩展分析接口（名场面 / 夸骂对比 / 叠加曲线 / 高赞情绪 / 聚类 / PK 榜）
# --------------------------------------------------------------------------- #
@app.route("/api/analysis/highlights")
def api_highlights():
    return jsonify({"highlights": highlight_mod.danmaku_highlights(cache.danmaku_cache.all())})


@app.route("/api/analysis/opinion")
def api_opinion():
    return jsonify(opinion_mod.opinion_keywords(
        cache.comment_cache.all(), cache.danmaku_cache.all()
    ))


@app.route("/api/analysis/danmaku_sentiment")
def api_danmaku_sentiment():
    return jsonify({"buckets": timeline_mod.danmaku_sentiment_timeline(
        cache.danmaku_cache.all(), 30
    )})


@app.route("/api/analysis/top_like")
def api_top_like():
    return jsonify(sentiment_mod.top_like_sentiment(cache.comment_cache.all()))


@app.route("/api/analysis/cluster")
def api_cluster():
    k = request.args.get("k", type=int)
    return jsonify(cluster_mod.cluster_opinions(cache.comment_cache.all(), "评论内容", k=k))


@app.route("/api/analysis/compare")
def api_compare():
    return jsonify({"videos": compare_mod.video_compare(cache.comment_cache.all())})


# --------------------------------------------------------------------------- #
# 一键报告
# --------------------------------------------------------------------------- #
def _top10_comments(items):
    top_level = [it for it in items if it.get("层级") == 1]
    ranked = sorted(top_level, key=lambda x: x.get("点赞数", 0), reverse=True)[:10]
    return [
        {
            "user": it.get("用户名", ""),
            "content": it.get("评论内容", ""),
            "like": it.get("点赞数", 0),
            "reply": it.get("回复数", 0),
        }
        for it in ranked
    ]


@app.route("/api/report")
def api_report():
    comments = cache.comment_cache.all()
    danmakus = cache.danmaku_cache.all()
    if not comments and not danmakus:
        return jsonify({"error": "没有可生成报告的数据，请先采集"}), 400

    c = sentiment_mod.analyze(comments, "评论内容")
    d = sentiment_mod.analyze(danmakus, "弹幕内容")
    total = c["total"] + d["total"]
    pos = c["positive"] + d["positive"]
    neg = c["negative"] + d["negative"]
    neu = c["neutral"] + d["neutral"]
    avg_score = (c["avg_score"] * c["total"] + d["avg_score"] * d["total"]) / max(1, total)
    neg_ratio = neg / max(1, total)
    pos_ratio = pos / max(1, total)
    health_score = round(100 * (0.5 * avg_score + 0.5 * (1 - neg_ratio)))
    if neg_ratio < 0.2:
        risk_level, risk_color = "低风险", "#52c41a"
    elif neg_ratio < 0.4:
        risk_level, risk_color = "中风险", "#faad14"
    else:
        risk_level, risk_color = "高风险", "#ff4d4f"

    op = opinion_mod.opinion_keywords(comments, danmakus)
    hl = highlight_mod.danmaku_highlights(danmakus)
    clusters = cluster_mod.cluster_opinions(comments, "评论内容")
    compare_rows = compare_mod.video_compare(comments)
    top_like = sentiment_mod.top_like_sentiment(comments)

    insights = []
    mood = "正面" if pos > neg else ("负面" if neg > pos else "中性")
    insights.append(
        f"共采集评论 {len(comments)} 条、弹幕 {len(danmakus)} 条，"
        f"正面 {pos} 条（{round(pos_ratio * 100)}%）、负面 {neg} 条（{round(neg_ratio * 100)}%），"
        f"整体情绪偏{mood}。"
    )
    pos_words = [w["name"] for w in op["positive"][:5]]
    neg_words = [w["name"] for w in op["negative"][:5]]
    if pos_words:
        insights.append(f"正面情绪主要由「{'、'.join(pos_words)}」等关键词驱动。")
    if neg_words:
        insights.append(f"负面情绪主要由「{'、'.join(neg_words)}」等关键词驱动。")
    if hl:
        insights.append(f"弹幕最密集出现在 {hl[0]['start']}~{hl[0]['end']}，30 秒内达 {hl[0]['count']} 条。")
    if top_like.get("verdict"):
        insights.append(top_like["verdict"])
    if compare_rows:
        top_cont = max(compare_rows, key=lambda x: x["controversy"])
        if top_cont["controversy"] > 0.5:
            insights.append(f"争议度最高的视频是「{top_cont['title']}」，正负观点撕裂明显。")

    data = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "health": {
            "score": health_score,
            "level": risk_level,
            "color": risk_color,
            "avg_score": round(avg_score, 4),
        },
        "insights": insights,
        "stats": {
            "comments": len(comments),
            "danmakus": len(danmakus),
            "videos": len(compare_rows),
            "positive": pos,
            "negative": neg,
            "neutral": neu,
        },
        "distribution": {
            "positive": pos,
            "negative": neg,
            "neutral": neu,
        },
        "trend": timeline_mod.comment_timeline(comments, "day", "评论内容"),
        "highlights": hl,
        "opinion": op,
        "clusters": clusters,
        "compare": compare_rows,
        "top_like": top_like,
        "top10": _top10_comments(comments),
    }
    try:
        path = export_mod.build_report_html(data)
    except Exception as exc:  # noqa: BLE001
        logger.exception("报告生成失败")
        return jsonify({"error": str(exc)}), 500
    return send_file(path, as_attachment=True, download_name=os.path.basename(path))


if __name__ == "__main__":
    logger.info("启动 B 站舆论分析工具：http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
