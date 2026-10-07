/* 观点聚类列表（纯 DOM） */
function _escCl(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
}

function initClusterPanel(listId) {
  function render(data) {
    const el = document.getElementById(listId);
    const cls = data.clusters || [];
    el.innerHTML = cls.length
      ? cls.map(c => `
        <li>
          <b>观点${c.id}</b>（${Math.round(c.ratio * 100)}% · ${c.size} 条）
          <div class="cl-keywords">${c.keywords.map(k => `<span class="tag">${_escCl(k)}</span>`).join('')}</div>
          <div class="cl-samples">${c.samples.map(s => `<div>· ${_escCl(s)}</div>`).join('')}</div>
        </li>`).join('')
      : '<li class="empty">暂无评论数据</li>';
  }
  return { render, resize() {} };
}
