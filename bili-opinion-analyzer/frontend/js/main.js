/* 前端主控制器 */
let videoResults = [];
let selectedBvids = new Set();
let statusTimer = null;
let prevRunning = { comment: false, danmaku: false };
let cacheTab = 'comment';
let cookie = localStorage.getItem('bili_cookie') || '';

const panels = {};

function $(id) { return document.getElementById(id); }

function escapeHtml(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
}

function showMsg(msg, ok = true) {
  const el = $('toast');
  el.textContent = msg;
  el.className = 'toast show ' + (ok ? 'ok' : 'err');
  setTimeout(() => { el.className = 'toast'; }, 3000);
}

function fmtNum(n) { return (n == null ? 0 : n).toLocaleString(); }

function fmtDur(sec) {
  if (!sec) return '0:00';
  const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = sec % 60;
  return h ? `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}` : `${m}:${String(s).padStart(2, '0')}`;
}

function fmtDate(ts) {
  if (!ts) return '';
  const d = new Date(ts * 1000);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

/* ---------------- 设置弹窗 ---------------- */
function openSettings() { $('settings-modal').classList.add('show'); $('cookie-input').value = cookie; }
function closeSettings() { $('settings-modal').classList.remove('show'); }
function saveSettings() {
  cookie = $('cookie-input').value.trim();
  localStorage.setItem('bili_cookie', cookie);
  closeSettings();
  showMsg('Cookie 已保存（仅用于搜索）');
}

/* ---------------- 搜索 ---------------- */
async function doSearch() {
  const keyword = $('search-keyword').value.trim();
  if (!keyword) { showMsg('请输入关键词', false); return; }
  const order = $('search-order').value;
  const pages = parseInt($('search-pages').value || '3', 10);
  const btn = $('search-btn');
  btn.disabled = true; btn.textContent = '搜索中…';
  try {
    const res = await API.post('/api/search', { keyword, order, pages, cookie });
    if (res.error) { showMsg(res.error, false); return; }
    videoResults = res.videos || [];
    selectedBvids = new Set(videoResults.map(v => v.bvid));
    renderVideoTable();
    showMsg(`搜索完成，共 ${videoResults.length} 个视频`);
  } catch (e) {
    showMsg('搜索失败：' + e.message, false);
  } finally {
    btn.disabled = false; btn.textContent = '搜索';
  }
}

function renderVideoTable() {
  const tbody = $('video-tbody');
  tbody.innerHTML = videoResults.map(v => `
    <tr>
      <td><input type="checkbox" class="video-check" data-bvid="${v.bvid}" ${selectedBvids.has(v.bvid) ? 'checked' : ''}></td>
      <td class="title">${escapeHtml(v.title)}</td>
      <td>${escapeHtml(v.author)}</td>
      <td>${escapeHtml(v.bvid)}</td>
      <td>${fmtNum(v.play)}</td>
      <td>${fmtNum(v.video_review)}</td>
      <td>${fmtNum(v.review)}</td>
      <td>${fmtDur(v.duration)}</td>
      <td>${fmtDate(v.pubdate)}</td>
    </tr>`).join('');
  tbody.querySelectorAll('.video-check').forEach(cb => {
    cb.addEventListener('change', () => {
      if (cb.checked) selectedBvids.add(cb.dataset.bvid);
      else selectedBvids.delete(cb.dataset.bvid);
      updateSelectedCount();
    });
  });
  updateSelectedCount();
}

function updateSelectedCount() {
  $('selected-count').textContent = `已选 ${selectedBvids.size} 个`;
}

function selectAll(v) {
  selectedBvids = v ? new Set(videoResults.map(x => x.bvid)) : new Set();
  renderVideoTable();
}
function invertSelect() {
  const nv = new Set();
  videoResults.forEach(v => { if (!selectedBvids.has(v.bvid)) nv.add(v.bvid); });
  selectedBvids = nv;
  renderVideoTable();
}

function selectedVideos() { return videoResults.filter(v => selectedBvids.has(v.bvid)); }

/* ---------------- 采集控制 ---------------- */
async function crawlComments() {
  const vids = selectedVideos();
  if (!vids.length) { showMsg('请先勾选视频', false); return; }
  const res = await API.post('/api/crawl/comments', {
    videos: vids,
    mode: parseInt($('comment-mode').value || '3', 10),
    max_count: parseInt($('max-count').value || '0', 10),
    delay: parseFloat($('delay-input').value || '1'),
  });
  if (res.error) { showMsg(res.error, false); return; }
  showMsg('评论采集已启动');
  startStatusPoll();
}

async function crawlDanmaku() {
  const vids = selectedVideos();
  if (!vids.length) { showMsg('请先勾选视频', false); return; }
  const res = await API.post('/api/crawl/danmakus', {
    videos: vids,
    delay: parseFloat($('delay-input').value || '1'),
  });
  if (res.error) { showMsg(res.error, false); return; }
  showMsg('弹幕采集已启动');
  startStatusPoll();
}

async function stopComment() {
  await API.post('/api/crawl/stop', { type: 'comment' });
  showMsg('已发送评论停止信号');
}

async function stopDanmaku() {
  await API.post('/api/crawl/stop', { type: 'danmaku' });
  showMsg('已发送弹幕停止信号');
}

function startStatusPoll() {
  if (statusTimer) return;
  pollStatus();
  statusTimer = setInterval(pollStatus, 1500);
}

async function pollStatus() {
  let res;
  try { res = await API.get('/api/crawl/status'); }
  catch (e) { return; }

  renderProgress('comment', res.comment);
  renderProgress('danmaku', res.danmaku);

  const running = res.comment.running || res.danmaku.running;
  const wasRunning = prevRunning.comment || prevRunning.danmaku;
  prevRunning = { comment: res.comment.running, danmaku: res.danmaku.running };

  if (!running && wasRunning) {
    clearInterval(statusTimer); statusTimer = null;
    renderCachePreview();
    refreshCharts();
    showMsg('采集完成，图表已刷新');
  }
}

function renderProgress(kind, st) {
  const pct = st.total ? Math.round(st.done / st.total * 100) : 0;
  $(`${kind}-bar`).style.width = pct + '%';
  $(`${kind}-pct`).textContent = pct + '%';
  $(`${kind}-msg`).textContent = `${st.message}（已缓存 ${st.count} 条）`;
}

/* ---------------- 缓存区 ---------------- */
function switchCacheTab(t) {
  cacheTab = t;
  document.querySelectorAll('.cache-tab').forEach(b => b.classList.toggle('active', b.dataset.tab === t));
  renderCachePreview();
}

async function renderCachePreview() {
  let res;
  try { res = await API.get('/api/cache/preview'); }
  catch (e) { return; }
  const snap = cacheTab === 'comment' ? res.comment : res.danmaku;
  renderPreviewTable(cacheTab, snap);
}

function renderPreviewTable(kind, snap) {
  const items = (snap && snap.items) || [];
  const total = (snap && snap.total) || 0;
  const thead = $('cache-thead');
  const tbody = $('cache-tbody');

  let cols;
  if (kind === 'comment') {
    cols = ['视频标题', '用户名', '等级', '地区', '评论内容', '点赞数', '回复数'];
  } else {
    cols = ['视频标题', 'progress_str', '弹幕内容', '发送时间'];
  }

  thead.innerHTML = `<tr>${cols.map(c => `<th>${c}</th>`).join('')}<th>（共 ${total} 条）</th></tr>`;
  if (!items.length) {
    tbody.innerHTML = `<tr><td colspan="${cols.length + 1}" class="empty">暂无数据</td></tr>`;
    return;
  }
  tbody.innerHTML = items.map(it => `<tr>${cols.map(c => `<td>${escapeHtml(String(it[c] == null ? '' : it[c]))}</td>`).join('')}<td></td></tr>`).join('');
}

async function doExport(format) {
  const label = cacheTab === 'comment' ? '评论' : '弹幕';
  if (!confirm(`确定导出当前「${label}」为 ${format.toUpperCase()}？`)) return;
  const res = await API.post('/api/export', { format, type: cacheTab });
  if (res.error) { showMsg(res.error, false); return; }
  showMsg(`已导出 ${res.count} 条到：${res.path}`);
}

async function clearCache() {
  if (!confirm('确定清空缓存区？')) return;
  await API.post('/api/cache/clear', {});
  renderCachePreview();
  refreshCharts();
  showMsg('缓存已清空');
}

/* ---------------- 一键报告 ---------------- */
async function downloadReport() {
  try {
    const r = await fetch('/api/report');
    const ct = r.headers.get('Content-Type') || '';
    if (ct.includes('application/json')) {
      const j = await r.json();
      showMsg(j.error || '报告生成失败', false);
      return;
    }
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = '舆情报告.html';
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    showMsg('报告已开始下载');
  } catch (e) {
    showMsg('下载失败：' + e.message, false);
  }
}

/* ---------------- 图表 ---------------- */
async function refreshCharts() {
  try {
    const [sent, lvl, wc, hm, sc, ov, op, hl, cl, cp, tl] = await Promise.all([
      API.get('/api/analysis/sentiment'),
      API.get('/api/analysis/level'),
      API.get('/api/analysis/wordfreq'),
      API.get('/api/analysis/danmaku_timeline'),
      API.get('/api/analysis/interaction'),
      API.get('/api/analysis/danmaku_sentiment'),
      API.get('/api/analysis/opinion'),
      API.get('/api/analysis/highlights'),
      API.get('/api/analysis/cluster'),
      API.get('/api/analysis/compare'),
      API.get('/api/analysis/top_like'),
    ]);
    panels.sentiment.render(sent);
    panels.level.render(lvl);
    panels.wordcloud.render(wc);
    panels.heatmap.render(hm);
    panels.overlay.render(ov);
    panels.opinion.render(op);
    panels.highlight.render(hl);
    panels.cluster.render(cl);
    panels.compare.render(cp);
    panels.scatter.render({ scatter: sc.scatter, topLike: tl });
  } catch (e) {
    showMsg('图表刷新失败：' + e.message, false);
  }
}

function resizeAll() { Object.values(panels).forEach(p => p.resize()); }

/* ---------------- 初始化 ---------------- */
document.addEventListener('DOMContentLoaded', () => {
  panels.sentiment = initSentimentChart('chart-sentiment-pie', 'chart-sentiment-line');
  panels.level = initLevelChart('chart-level');
  panels.wordcloud = initWordcloudChart('chart-wordcloud-comment', 'chart-wordcloud-danmaku');
  panels.heatmap = initHeatmapChart('chart-heatmap');
  panels.overlay = initOverlayChart('chart-overlay');
  panels.opinion = initOpinionChart('chart-opinion-pos', 'chart-opinion-neg');
  panels.highlight = initHighlightPanel('highlight-list');
  panels.cluster = initClusterPanel('cluster-list');
  panels.compare = initComparePanel('compare-body');
  panels.scatter = initScatterChart('chart-scatter', 'top-like-verdict', 'top10-list');

  $('search-keyword').addEventListener('keydown', e => { if (e.key === 'Enter') doSearch(); });
  $('settings-modal').addEventListener('click', e => {
    if (e.target === $('settings-modal')) closeSettings();
  });

  window.addEventListener('resize', resizeAll);
  renderCachePreview();
  refreshCharts();
});
