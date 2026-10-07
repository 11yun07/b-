# -*- coding: utf-8 -*-
"""全局配置。"""
import os

# 项目根目录（backend/ 的上一级）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(BASE_DIR, "data")
CACHE_DIR = os.path.join(DATA_DIR, "cache")
EXPORT_DIR = os.path.join(DATA_DIR, "exports")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

for _d in (DATA_DIR, CACHE_DIR, EXPORT_DIR):
    os.makedirs(_d, exist_ok=True)

# 请求头
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
# 移动端 UA：B 站网页版评论接口在 PC UA 下不返回 IP 属地，
# 改用移动端 UA 请求后可取到 member.ip_location / reply_control.location
MOBILE_USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)
REFERER = "https://www.bilibili.com/"

# B 站接口
NAV_URL = "https://api.bilibili.com/x/web-interface/nav"
SEARCH_URL = "https://api.bilibili.com/x/web-interface/wbi/search/type"
VIEW_URL = "https://api.bilibili.com/x/web-interface/view"
# 评论接口：移动端 main 可取 IP 属地；网页版 wbi/main 无 IP 但更稳（作回退）
COMMENT_URL_MOBILE = "https://api.bilibili.com/x/v2/reply/main"
COMMENT_URL_WEB = "https://api.bilibili.com/x/v2/reply/wbi/main"
DANMAKU_URL = "https://api.bilibili.com/x/v2/dm/wbi/web/seg.so"

# 采集参数
DEFAULT_DELAY = 1.0          # 请求间隔（秒）
COOLDOWN_412 = 10.0          # 触发 412 风控后的冷却时间（秒）
MAX_RETRIES = 3              # 最大重试次数
DEFAULT_PAGES = 3            # 默认搜索页数
DEFAULT_PAGE_SIZE = 20       # 每页条数
DEFAULT_MAX_COUNT = 0        # 0 表示不限制采集数量

# 弹幕分段时长（秒），B 站每段 6 分钟
DANMAKU_SEG_SECONDS = 360

# 数据库文件
DB_PATH = os.path.join(DATA_DIR, "bili_opinion.db")

# 支持的排序方式
SEARCH_ORDERS = {
    "totalrank": "综合",
    "click": "最多播放",
    "pubdate": "最新发布",
    "dm": "最多弹幕",
    "stow": "最多收藏",
}
