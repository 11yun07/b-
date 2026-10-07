# -*- coding: utf-8 -*-
"""SQLite 存储。"""
import json
import logging
import os
import sqlite3

from backend import config

logger = logging.getLogger(__name__)

_COMMENT_COLS = [
    ("rpid", "INTEGER PRIMARY KEY"),
    ("parent_rpid", "INTEGER"),
    ("level", "INTEGER"),
    ("reply_to", "TEXT"),
    ("user_mid", "INTEGER"),
    ("username", "TEXT"),
    ("user_level", "INTEGER"),
    ("vip", "TEXT"),
    ("gender", "TEXT"),
    ("comment_time", "TEXT"),
    ("ctime_ts", "INTEGER"),
    ("region", "TEXT"),
    ("content", "TEXT"),
    ("like_count", "INTEGER"),
    ("reply_count", "INTEGER"),
    ("images", "TEXT"),
]

_DANMAKU_COLS = [
    ("dmid", "INTEGER PRIMARY KEY"),
    ("progress_ms", "INTEGER"),
    ("progress_str", "TEXT"),
    ("mode", "INTEGER"),
    ("fontsize", "INTEGER"),
    ("color", "TEXT"),
    ("mid_hash", "TEXT"),
    ("content", "TEXT"),
    ("send_time", "TEXT"),
    ("ctime_ts", "INTEGER"),
]


def _connect(db_path=None):
    db_path = db_path or config.DB_PATH
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return sqlite3.connect(db_path, timeout=30)


def init_db(db_path=None):
    conn = _connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS comments (%s)"
            % ", ".join(f"{n} {t}" for n, t in _COMMENT_COLS)
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS danmakus (%s)"
            % ", ".join(f"{n} {t}" for n, t in _DANMAKU_COLS)
        )
        conn.commit()
    finally:
        conn.close()


def _comment_values(row):
    return (
        row.get("rpid"), row.get("parent_rpid"), row.get("层级"),
        row.get("回复给"), row.get("user_mid"), row.get("用户名"),
        row.get("等级"), row.get("会员状态"), row.get("性别"),
        row.get("评论时间"), row.get("ctime_ts"), row.get("地区"),
        row.get("评论内容"), row.get("点赞数"), row.get("回复数"),
        json.dumps(row.get("图片") or [], ensure_ascii=False),
    )


def _danmaku_values(row):
    return (
        row.get("dmid"), row.get("progress_ms"), row.get("progress_str"),
        row.get("mode"), row.get("fontsize"), row.get("color"),
        row.get("midHash"), row.get("弹幕内容"), row.get("发送时间"),
        row.get("ctime_ts"),
    )


def save_comments(rows, db_path=None):
    init_db(db_path)
    conn = _connect(db_path)
    try:
        cur = conn.cursor()
        cur.executemany(
            "INSERT OR REPLACE INTO comments VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [_comment_values(r) for r in rows],
        )
        conn.commit()
        return len(rows)
    finally:
        conn.close()


def save_danmakus(rows, db_path=None):
    init_db(db_path)
    conn = _connect(db_path)
    try:
        cur = conn.cursor()
        cur.executemany(
            "INSERT OR REPLACE INTO danmakus VALUES (?,?,?,?,?,?,?,?,?,?)",
            [_danmaku_values(r) for r in rows],
        )
        conn.commit()
        return len(rows)
    finally:
        conn.close()
