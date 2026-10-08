# B站舆论分析工具（bili-opinion-analyzer）

一个 Web 端的 B 站舆论分析工具：使用 Cookie 搜索视频，然后在**无 Cookie** 状态下爬取评论与弹幕，并进行情感分析、词频统计与可视化。

> ⚠️ 合规提示：本工具仅供个人学习研究使用。请控制请求频率，勿用于商业用途，勿存储、传播敏感个人信息，遵守 B 站服务条款与相关法律法规。

---

## 一、核心设计：Cookie 隔离

- **搜索视频**：使用携带用户 Cookie 的 `requests.Session`（`make_search_session`）。
- **采集评论 / 弹幕**：使用**全新、显式清空 Cookie** 的 `Session`（`make_public_session`）。
- 采集函数（`fetch_comments` / `fetch_danmakus`）参数列表中**不出现 cookie**，从物理上杜绝 Cookie 泄漏。
- 本工具只采集文本数据，**不下载视频**。

相关代码位于 `backend/crawler/session_factory.py`。

---

## 二、目录结构

```
bili-opinion-analyzer/
├── backend/
│   ├── app.py                 # Flask 入口，全部 API
│   ├── config.py              # 全局配置
│   ├── crawler/
│   │   ├── session_factory.py # Cookie 隔离核心
│   │   ├── wbi.py             # WBI 签名 + 412 重试
│   │   ├── search.py          # 搜索（带 Cookie）
│   │   ├── video_info.py      # view 接口获取 cid
│   │   ├── comment.py         # 评论采集（无 Cookie）
│   │   └── danmaku.py         # 弹幕采集（无 Cookie）
│   ├── analysis/
│   │   ├── sentiment.py       # SnowNLP 情感分析
│   │   ├── wordfreq.py        # jieba + TF-IDF
│   │   ├── level.py           # 等级分布
│   │   └── timeline.py        # 时间趋势 / 弹幕时间轴
│   ├── storage/
│   │   ├── cache.py           # 内存缓存区
│   │   ├── db.py              # SQLite
│   │   └── export.py          # CSV/JSON/SQLite 导出
│   └── proto/
│       ├── dm_seg.proto       # 弹幕 protobuf 定义
│       └── dm_seg_pb2.py      # Python 消息类（运行时构建）
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   ├── js/
│   │   ├── api.js
│   │   ├── main.js
│   │   └── charts/            # 6 个 ECharts 图表模块
│   └── assets/china.json      # 中国地图 GeoJSON（可选，缺失时自动回退 CDN）
├── data/                      # 运行时生成：cache/ exports/ *.db
├── requirements.txt
└── README.md
```

---

## 三、安装与运行

### 1. 安装依赖

```bash
cd bili-opinion-analyzer
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. 启动后端

```bash
python backend/app.py
```

浏览器打开 <http://127.0.0.1:5000>。

### 3. 配置 Cookie（仅用于搜索）

1. 浏览器打开 B 站并登录。
2. 按 F12 → 网络（Network）→ 刷新页面 → 找到任意 `api.bilibili.com` 请求 → 复制请求头中的 `Cookie`。
3. 点击页面右上角「⚙️ 设置」，粘贴 Cookie 并保存。

> Cookie 仅用于「搜索视频」，评论与弹幕采集始终使用无 Cookie 会话。

---

## 四、使用流程

1. **搜索**：输入关键词，选择排序与页数，点击「搜索」。
2. **选择视频**：勾选要分析的视频（支持全选 / 反选）。
3. **采集**：点击「采集评论」或「采集弹幕」，可分别「停止」；停止后再点采集会**断点续传**。
4. **缓存区**：查看预览，选择「保存为 CSV / JSON / 存入数据库 / 清空」。
5. **图表**：采集完成后自动刷新（情感、词云、名场面、观点聚类、PK 榜等面板）。
6. **报告**：点右上角「📄 下载报告」，一键下载自包含的 HTML 舆情报告。

---

## 五、API 一览

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/search` | POST | 搜索视频 |
| `/api/crawl/comments` | POST | 启动评论采集 |
| `/api/crawl/danmakus` | POST | 启动弹幕采集 |
| `/api/crawl/status` | GET | 采集进度 |
| `/api/crawl/stop` | POST | 停止采集 |
| `/api/cache/preview` | GET | 缓存区预览 |
| `/api/cache/clear` | POST | 清空缓存 |
| `/api/export` | POST | 导出 CSV/JSON/SQLite |
| `/api/analysis/sentiment` | GET | 情感分布 + 趋势 |
| `/api/analysis/wordfreq` | GET | 词频 |
| `/api/analysis/level` | GET | 等级分布 |
| `/api/analysis/timeline` | GET | 评论时间趋势 |
| `/api/analysis/danmaku_timeline` | GET | 弹幕时间轴 / 热力图 |
| `/api/analysis/interaction` | GET | 互动散点 |
| `/api/analysis/highlights` | GET | 弹幕名场面 / 高能时刻 |
| `/api/analysis/opinion` | GET | 夸什么 vs 骂什么 |
| `/api/analysis/danmaku_sentiment` | GET | 弹幕密度 × 情感叠加 |
| `/api/analysis/top_like` | GET | 高赞评论情绪判断 |
| `/api/analysis/cluster` | GET | 观点聚类 |
| `/api/analysis/compare` | GET | 跨视频 PK 榜 |
| `/api/report` | GET | 下载 HTML 舆情报告 |

---

## 六、说明与注意事项

- **WBI 签名**：`backend/crawler/wbi.py` 中的 `get_mixin_key()` / `sign()` 可复用用户已有代码；签名密钥通过 `nav` 接口自动获取并缓存。
- **弹幕 protobuf**：`backend/proto/dm_seg_pb2.py` 使用 `descriptor_pool` 在运行时构建消息类，无需安装 protoc。若装有 protoc，可执行 `protoc --python_out=. dm_seg.proto` 覆盖。
- **412 风控**：采集遇到 412 会冷却 10 秒并重试最多 3 次。
- **请求间隔**：默认 1 秒，可在页面调整；请勿调得过低。
- **断点续传**：停止后再次点击采集，会从上次进度继续（评论按游标、弹幕按分段），且缓存按 rpid/dmid 去重，不会重复。
- **停止按钮**：评论与弹幕的「停止」已拆分为两个按钮，可单独停止其一。
- **停用词**：词频统计内置了一份中文停用词表，可自行扩展 `backend/analysis/wordfreq.py` 中的 `_STOPWORDS`。
- **观点聚类**：纯 Python 实现（jieba + TF-IDF + KMeans），无额外依赖；采样上限 1500 条以保证速度。
- **PK 榜**：依赖采集时注入的「视频bvid / 视频标题」字段；旧缓存数据（无此字段）会归入「未知视频」，重新采集即可。
