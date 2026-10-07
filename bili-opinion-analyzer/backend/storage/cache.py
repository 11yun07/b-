# -*- coding: utf-8 -*-
"""内存缓存区：评论 / 弹幕分别存储，按 rpid / dmid 去重。"""
import threading


class BaseCache:
    def __init__(self, key_field):
        self.key_field = key_field
        self._items = []
        self._lock = threading.Lock()

    def add(self, items):
        """批量加入并去重，返回新增条数。"""
        added = 0
        with self._lock:
            existing = {it[self.key_field] for it in self._items}
            for it in items:
                k = it.get(self.key_field)
                if k in existing:
                    continue
                existing.add(k)
                self._items.append(it)
                added += 1
        return added

    def snapshot(self, n=100):
        """返回预览数据：{'total': 总数, 'items': 前 n 条}。"""
        with self._lock:
            return {"total": len(self._items), "items": self._items[:n]}

    def clear(self):
        with self._lock:
            self._items = []

    def count(self):
        with self._lock:
            return len(self._items)

    def all(self):
        """返回完整副本，供导出 / 分析使用。"""
        with self._lock:
            return list(self._items)


class CommentCache(BaseCache):
    def __init__(self):
        super().__init__("rpid")


class DanmakuCache(BaseCache):
    def __init__(self):
        super().__init__("dmid")


# 全局缓存区单例
comment_cache = CommentCache()
danmaku_cache = DanmakuCache()
